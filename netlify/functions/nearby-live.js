// nearby-live.js — live "search more" via Mapbox Search Box category endpoint.
// Proxies the call server-side so the token stays hidden, and enforces a simple
// in-memory rate cap so a bot or traffic spike can't run up a Mapbox bill
// (Mapbox has no hard spend cap, so WE add one here).
//
// Mapbox category search free tier: ~100k requests/month. This function is only
// hit when a user taps "Search more", not on page load, so real usage stays low.

const MAPBOX_CATEGORY = 'https://api.mapbox.com/search/searchbox/v1/category';

// crude in-memory rate limiter (per warm lambda instance). Not bulletproof, but
// stops runaway loops. Tune MAX_PER_MIN as needed.
let _hits = [];
const MAX_PER_MIN = 120;

// allowed categories map friendly tab -> mapbox category codes
const CATEGORIES = {
  restaurants: ['restaurant', 'bar', 'coffee', 'fast_food'],
  hotels: ['hotel'],
  more: ['tourist_attraction', 'museum', 'park'],
};

exports.handler = async (event) => {
  const headers = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' };
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers, body: JSON.stringify({ error: 'POST only' }) };
  }

  // rate cap
  const now = Date.now();
  _hits = _hits.filter((t) => now - t < 60000);
  if (_hits.length >= MAX_PER_MIN) {
    return { statusCode: 429, headers, body: JSON.stringify({ error: 'Rate limited, try again shortly.' }) };
  }
  _hits.push(now);

  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, headers, body: JSON.stringify({ error: 'Bad JSON' }) }; }

  const { lat, lng, tab = 'restaurants', category } = body;
  if (typeof lat !== 'number' || typeof lng !== 'number') {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'lat/lng required' }) };
  }

  const token = process.env.MAPBOX_TOKEN || process.env.MAPBOX_ACCESS_TOKEN;
  if (!token) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'Mapbox token not configured' }) };
  }

  // pick categories: a specific one if requested + allowed, else the tab's set
  const allowed = CATEGORIES[tab] || CATEGORIES.restaurants;
  const cats = category && allowed.includes(category) ? [category] : allowed;

  try {
    // query each category, merge + dedupe by name
    const seen = new Set();
    const results = [];
    for (const cat of cats) {
      const url = `${MAPBOX_CATEGORY}/${encodeURIComponent(cat)}`
        + `?access_token=${token}`
        + `&proximity=${lng},${lat}`
        + `&limit=10&language=en`;
      const r = await fetch(url);
      if (!r.ok) continue;
      const data = await r.json();
      for (const f of (data.features || [])) {
        const name = f.properties?.name;
        if (!name || seen.has(name)) continue;
        seen.add(name);
        const coord = f.geometry?.coordinates || [];
        results.push({
          name,
          address: f.properties?.full_address || f.properties?.address || '',
          category: cat,
          lat: coord[1], lng: coord[0],
          maki: f.properties?.maki || null,
        });
      }
    }
    return { statusCode: 200, headers, body: JSON.stringify({ results }) };
  } catch (e) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'Mapbox request failed' }) };
  }
};
