// netlify/functions/venue-photo.js
//
// COMPLIANT Google Places photo lookup: LIVE, per-request, NOTHING
// STORED. Google's Maps Platform Terms (Sec. 3.2.3, "No Caching")
// prohibit pre-fetching, caching, or storing Places content beyond
// place_id (indefinite) and lat/lng (30 days). Photos are NOT
// exempt. So this function never writes an image to disk and never
// persists a photo URL past the response: every call is a fresh
// Google lookup, exactly how Google's own docs say Photos (New)
// must be used ("the photo name can expire; always get it from a
// live search response").
//
// SETUP (do this once):
//   1. Google Cloud Console -> Credentials -> Create a NEW API key.
//      Do NOT reuse the browser key from maps-key.js.
//   2. Restrict it: "API restrictions" -> Places API (New) only.
//      Leave "Application restrictions" as None -- this key lives
//      only in your server environment and is never sent to a
//      browser or app, so IP/referrer restriction isn't applicable
//      the way it is for the client-side key.
//   3. Add it to Netlify: Site settings -> Environment variables ->
//      GOOGLE_PLACES_SERVER_KEY. Never commit it to the repo.
//
// The app calls this per-venue, only for venues actually on screen
// (same pattern as its existing Ticketmaster image lookup), not in
// bulk, so it stays cheap: a handful of calls per session, not 346.

const R_EARTH_M = 6371000;
function metersBetween(lat1, lng1, lat2, lng2) {
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * R_EARTH_M * Math.asin(Math.sqrt(a));
}

// This function has never exposed a secret to the browser -- it's a
// read-only lookup that only ever returns public place data. Adding
// CORS support (Aug 13) doesn't create a new risk, it just lets
// callers other than concertocity.com itself use it, e.g. a design
// prototype that wants real venue photos without ever holding its
// own Google Places key.
const CORS = { 'Access-Control-Allow-Origin': '*' };

exports.handler = async function (event) {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: CORS, body: '' };
  }
  const key = process.env.GOOGLE_PLACES_SERVER_KEY;
  if (!key) {
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: 'GOOGLE_PLACES_SERVER_KEY not configured' }) };
  }
  const { name, city, lat, lng } = event.queryStringParameters || {};
  if (!name || lat === undefined || lng === undefined) {
    return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'name, lat, lng required' }) };
  }
  const vLat = parseFloat(lat);
  const vLng = parseFloat(lng);

  try {
    // 1. Live text search. Never stored: this response is used once,
    //    for this one request, then discarded.
    const searchRes = await fetch('https://places.googleapis.com/v1/places:searchText', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': key,
        'X-Goog-FieldMask': 'places.location,places.photos,places.displayName',
      },
      body: JSON.stringify({ textQuery: `${name} ${city || ''}`.trim(), maxResultCount: 3 }),
    });
    if (!searchRes.ok) {
      return { statusCode: 404, headers: CORS, body: JSON.stringify({ error: 'search failed' }) };
    }
    const searchData = await searchRes.json();
    const places = searchData.places || [];

    // 2. Coordinate match, not "just take the first result": reject
    //    anything more than 800m from the venue's own known lat/lng,
    //    the same wrong-venue guard the Wikimedia version used.
    const match = places.find((p) => {
      if (!p.location || !p.photos?.length) return false;
      const d = metersBetween(vLat, vLng, p.location.latitude, p.location.longitude);
      return d <= 800;
    });
    if (!match) {
      return { statusCode: 404, headers: CORS, body: JSON.stringify({ error: 'no coordinate-verified match' }) };
    }

    const photo = match.photos[0];
    const credit = (photo.authorAttributions || [])
      .map((a) => a.displayName)
      .filter(Boolean)
      .join(', ');

    // 3. Live photo media lookup. skipHttpRedirect=true returns a
    //    JSON pointer to Google's own hosted image URL -- we relay
    //    that URL to the client; we never download or touch the
    //    image bytes ourselves, and nothing is written to disk.
    const mediaRes = await fetch(
      `https://places.googleapis.com/v1/${photo.name}/media?maxWidthPx=1200&skipHttpRedirect=true&key=${key}`,
    );
    if (!mediaRes.ok) {
      return { statusCode: 404, headers: CORS, body: JSON.stringify({ error: 'photo media failed' }) };
    }
    const media = await mediaRes.json();

    return {
      statusCode: 200,
      headers: {
        ...CORS,
        'Content-Type': 'application/json',
        // Short client cache only, purely to smooth repeat views in
        // the same session; well under any interpretation of "no
        // caching beyond allowed exceptions" as this is HTTP
        // freshness handling, not developer-side storage/rehosting.
        'Cache-Control': 'private, max-age=900',
      },
      body: JSON.stringify({
        src: media.photoUri,
        credit: credit ? `Photo: ${credit}, via Google` : 'Photo via Google',
      }),
    };
  } catch (err) {
    console.error('venue-photo error:', err);
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: 'lookup failed' }) };
  }
};
