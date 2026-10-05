// Self-serve signup, step 2: find the business on Google near the chosen venue.
// GET ?venue=<slug>&kind=restaurant|hotel&q=<name>. Returns up to 6 matches within 5 miles.
const guard = require('./lib/guard');
const { venueBySlug, miles, kindFits } = require('./lib/partner-self-serve');

exports.handler = async (event) => {
  const H = { ...guard.corsHeaders(event, 'GET, OPTIONS'), 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: H, body: '' };
  if (event.httpMethod !== 'GET') return guard.refuse(event, 405, 'method not allowed', 'GET, OPTIONS');
  if (guard.limited(event, 30, 60000)) return guard.refuse(event, 429, 'Too many searches. Try again in a minute.', 'GET, OPTIONS');
  const q = event.queryStringParameters || {};
  const venue = venueBySlug(String(q.venue || ''));
  const text = String(q.q || '').trim().slice(0, 80);
  const kind = q.kind === 'hotel' ? 'hotel' : 'restaurant';
  if (!venue || text.length < 2) return guard.refuse(event, 400, 'Choose a venue and type your business name.', 'GET, OPTIONS');
  const key = process.env.GOOGLE_PLACES_SERVER_KEY;
  if (!key) return guard.refuse(event, 503, 'Search is unavailable right now.', 'GET, OPTIONS');
  try {
    const r = await fetch('https://places.googleapis.com/v1/places:searchText', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': key,
        'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location,places.types' },
      body: JSON.stringify({ textQuery: text, maxResultCount: 8,
        locationBias: { circle: { center: { latitude: venue.lat, longitude: venue.lng }, radius: 8000 } } }),
    });
    if (!r.ok) return guard.refuse(event, 502, 'Search failed. Try again.', 'GET, OPTIONS');
    const j = await r.json();
    const out = (j.places || []).map((p) => {
      const loc = { lat: p.location?.latitude, lng: p.location?.longitude };
      return { id: p.id, name: p.displayName?.text || '', address: p.formattedAddress || '', lat: loc.lat, lng: loc.lng,
        miles: loc.lat != null ? Math.round(miles(venue, loc) * 10) / 10 : null, fits: kindFits(kind, p.types) };
    }).filter((p) => p.miles != null && p.miles <= 5).slice(0, 6);
    return { statusCode: 200, headers: H, body: JSON.stringify({ results: out }) };
  } catch (e) {
    return guard.refuse(event, 502, 'Search failed. Try again.', 'GET, OPTIONS');
  }
};
