// netlify/functions/venue-photo.js
//
// COMPLIANT Google Places photo lookup, updated Aug 17 with a
// shared cache. Verified directly against Google's current policy
// pages: place_id can be cached indefinitely (the only unconditional
// exception), coordinates up to 30 days, and there's a general
// "temporary caching" allowance covering other content -- capped at
// UNDER 30 consecutive days, meant for smoothing latency, not
// permanent storage. Photos were never exempt from that cap.
//
// Before this, every single view triggered a fresh Google call, no
// matter how many different people were looking at the exact same
// restaurant. That was fine at low volume, but the new Home rows put
// these lookups on the single most-viewed screen in the app, which
// meaningfully raised how often this runs. The fix: cache resolved
// photos in Supabase, keyed by place_id, for 25 days -- safely under
// Google's 30-day ceiling, not pushing right up against it. The
// first person who views a given place triggers the one real Google
// call; everyone else within that window, on any device, reads the
// cached row instead. Past 25 days, the entry is treated as expired
// and the next request does a fresh live lookup, same as before.
//
// This only applies when a place_id is available (every nearby-place
// item has one; venues.json entries don't) -- without one there's no
// stable cache key, so that path is untouched: live lookup every
// time, exactly as it always was.
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
const { createClient } = require('@supabase/supabase-js');

// 25 days, not 30 -- real margin under Google's ceiling rather than
// an implementation that only works if every clock and cron involved
// is perfectly on time.
const CACHE_DAYS = 25;

exports.handler = async function (event) {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: CORS, body: '' };
  }
  const key = process.env.GOOGLE_PLACES_SERVER_KEY;
  if (!key) {
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: 'GOOGLE_PLACES_SERVER_KEY not configured' }) };
  }
  const { name, city, lat, lng, place_id: placeId } = event.queryStringParameters || {};
  if (!name || lat === undefined || lng === undefined) {
    return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: 'name, lat, lng required' }) };
  }
  const vLat = parseFloat(lat);
  const vLng = parseFloat(lng);

  // Supabase is optional here on purpose: if the env vars aren't
  // set for some reason, this falls through to the pre-cache
  // behavior (live lookup every time) rather than hard-erroring the
  // whole photo feature over a caching layer specifically.
  const supabase =
    process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY
      ? createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY)
      : null;

  if (placeId && supabase) {
    try {
      const { data: cached } = await supabase
        .from('place_photos')
        .select('src, credit, cached_at')
        .eq('place_id', placeId)
        .single();
      if (cached) {
        const ageMs = Date.now() - new Date(cached.cached_at).getTime();
        if (ageMs < CACHE_DAYS * 86400000) {
          return {
            statusCode: 200,
            headers: { ...CORS, 'Content-Type': 'application/json', 'Cache-Control': 'private, max-age=900' },
            body: JSON.stringify({ src: cached.src, credit: cached.credit }),
          };
        }
      }
    } catch {
      // No cached row, or the lookup itself failed -- either way,
      // fall through to a live search rather than error the request.
    }
  }

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
    const result = {
      src: media.photoUri,
      credit: credit ? `Photo: ${credit}, via Google` : 'Photo via Google',
    };

    // Write-through: only when we actually have a place_id to key on
    // (the exempt, indefinitely-storable identifier), and only the
    // photo URL and credit -- nothing else from this response gets
    // persisted. Upsert, not insert, since a stale row past 25 days
    // needs replacing, not a duplicate-key error.
    if (placeId && supabase) {
      try {
        await supabase.from('place_photos').upsert({
          place_id: placeId, src: result.src, credit: result.credit, cached_at: new Date().toISOString(),
        });
      } catch {
        // A failed cache write should never fail the actual request
        // the user is waiting on -- the photo still made it back to
        // them, it just won't be cached this one time.
      }
    }

    return {
      statusCode: 200,
      headers: { ...CORS, 'Content-Type': 'application/json', 'Cache-Control': 'private, max-age=900' },
      body: JSON.stringify(result),
    };
  } catch (err) {
    console.error('venue-photo error:', err);
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: 'lookup failed' }) };
  }
};
