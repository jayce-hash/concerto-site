// netlify/functions/claude.js
// Shared proxy for all Concerto features
// Handles: Claude AI, Ticketmaster, Google Places, Geocode, Bag Check
//
// AUTH MODEL:
//   - PUBLIC (no login):  tm_venue_events  → powers the public venue pages' "Upcoming Events"
//   - LOGGED IN required: ticketmaster, geocode, places_nearby
//   - PREMIUM required:   claude, bag_check
//
// HARDENING:
//   - Anthropic/Google/Ticketmaster keys live only in env vars (never in the client)
//   - 'claude' branch clamps model to an allowlist and caps max_tokens
//   - CORS locked to known origins; public branch additionally rejects disallowed browser origins
// Note: CORS/Origin only constrains browsers, not curl. For the public branch the only exposed
// capability is "list a venue's upcoming music events" — read-only public data, no key exposed.

const { createClient } = require('@supabase/supabase-js');
const venueInfo = require('../../data/venue_info.json');

const ALLOWED_ORIGINS = [
  'https://concertocity.com',
  'https://www.concertocity.com',
];

const ALLOWED_MODELS = new Set(['claude-haiku-4-5-20251001']);
const DEFAULT_MODEL = 'claude-haiku-4-5-20251001';
const MAX_TOKENS_CAP = 4096;

const PUBLIC_SERVICES  = new Set(['tm_venue_events']);
const PREMIUM_SERVICES = new Set(['claude', 'bag_check']);
const TM = 'https://app.ticketmaster.com/discovery/v2';

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allow,
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Vary': 'Origin',
  };
}

exports.handler = async function (event) {
  const origin = event.headers.origin || event.headers.Origin || '';
  const headers = { 'Content-Type': 'application/json', ...corsHeaders(origin) };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: corsHeaders(origin), body: '' };
  }
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers, body: JSON.stringify({ error: 'Method Not Allowed' }) };
  }

  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON' }) };
  }
  const { service } = body;

  // ─────────────────────────────────────────────
  // PUBLIC LANE (no auth) — runs before the auth gate
  // ─────────────────────────────────────────────
  if (PUBLIC_SERVICES.has(service)) {
    // Soft origin check: block other sites' browsers, allow same-origin and non-browser (no Origin).
    if (origin && !ALLOWED_ORIGINS.includes(origin)) {
      return { statusCode: 403, headers, body: JSON.stringify({ error: 'Origin not allowed' }) };
    }
    try {
      if (service === 'tm_venue_events') {
        const venueName = (body.venueName || '').toString().trim().slice(0, 120);
        const size = Math.min(Number(body.size) || 6, 12);
        if (!venueName) {
          return { statusCode: 400, headers, body: JSON.stringify({ error: 'Missing venueName' }) };
        }
        // Step 1 — resolve the Ticketmaster venue id from the name
        const vRes = await fetch(`${TM}/venues.json?apikey=${process.env.TICKETMASTER_API_KEY}`
          + `&keyword=${encodeURIComponent(venueName)}&size=1`);
        const vData = await vRes.json();
        const tmVenue = vData?._embedded?.venues?.[0];
        if (!tmVenue?.id) {
          // Return an empty-but-valid shape so the page shows its normal "no events" state
          return { statusCode: 200, headers, body: JSON.stringify({ _embedded: { events: [] } }) };
        }
        // Step 2 — upcoming events at that venue
        const eRes = await fetch(`${TM}/events.json?apikey=${process.env.TICKETMASTER_API_KEY}`
          + `&venueId=${encodeURIComponent(tmVenue.id)}&size=${size}&sort=date,asc`);
        const eData = await eRes.json();
        return { statusCode: eRes.status, headers, body: JSON.stringify(eData) };
      }
    } catch (err) {
      return { statusCode: 500, headers, body: JSON.stringify({ error: err.message }) };
    }
  }

  // ─────────────────────────────────────────────
  // AUTH GATE — everything below requires a valid Supabase JWT
  // ─────────────────────────────────────────────
  const authHeader = event.headers.authorization || event.headers.Authorization || '';
  const token = authHeader.replace(/^Bearer\s+/i, '').trim();
  if (!token) {
    return { statusCode: 401, headers, body: JSON.stringify({ error: 'Authentication required' }) };
  }

  let user, supabase;
  try {
    supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const { data: { user: u }, error } = await supabase.auth.getUser(token);
    if (error || !u) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'Invalid session' }) };
    }
    user = u;
  } catch (err) {
    console.error('claude proxy auth error:', err);
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'Auth check failed' }) };
  }

  // Premium gate for expensive branches
  if (PREMIUM_SERVICES.has(service)) {
    const { data: profile } = await supabase
      .from('profiles').select('is_premium').eq('id', user.id).single();
    if (!profile?.is_premium) {
      return { statusCode: 403, headers, body: JSON.stringify({ error: 'Premium required' }) };
    }
  }

  try {
    // ── Claude (AI itinerary, chat) ──
    if (service === 'claude') {
      const model = ALLOWED_MODELS.has(body.model) ? body.model : DEFAULT_MODEL;
      const max_tokens = Math.min(Number(body.max_tokens) || 1024, MAX_TOKENS_CAP);
      const payload = { model, max_tokens };
      if (typeof body.system === 'string') payload.system = body.system;
      if (Array.isArray(body.messages)) payload.messages = body.messages;
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': process.env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    // ── Bag Check (image analysis) ──
    if (service === 'bag_check') {
      const { imageB64, venueSlug, venue: clientVenue } = body;
      if (!imageB64 || (!venueSlug && !clientVenue)) {
        return { statusCode: 400, headers, body: JSON.stringify({ error: 'Missing image or venue' }) };
      }

      // Verified venue policy is server-owned. A modified client must not be
      // able to tell Bag Check what an arena's official rules supposedly are.
      // Keep the legacy payload only as a compatibility fallback for an older
      // app binary while 2.4.1 rolls out.
      const detail = venueSlug ? venueInfo[String(venueSlug)] : null;
      const venue = detail ? {
        n: detail.name,
        loc: `${detail.city}${detail.state ? `, ${detail.state}` : ''}`,
        policy_text: detail.bagPolicy?.summary || '',
        allows: detail.bagPolicy?.allowed || [],
        denies: detail.bagPolicy?.prohibited || [],
        park_note: detail.parking?.note || 'unknown',
        ride_note: detail.rideshare?.note || 'unknown',
      } : clientVenue;
      if (!venue) {
        return { statusCode: 404, headers, body: JSON.stringify({ error: 'Venue not found' }) };
      }
      const policy = `Venue: ${venue.n} (${venue.loc})
Policy: ${venue.policy_text || ''}
Allowed: ${(venue.allows || []).join('; ')}
Prohibited: ${(venue.denies || []).join('; ')}
Parking context: ${venue.park_note || 'unknown'}
Rideshare context: ${venue.ride_note || 'unknown'}`;
      const prompt = `You are Concerto's Bag Check AI. Analyze the bag in this photo for entry to ${venue.n}.

${policy}

Respond ONLY with valid JSON, no markdown:
{"verdict":"pass"|"warn"|"fail","bag_type":"e.g. Small Leather Clutch","dims":"e.g. Est. 6\\" × 4\\" · Leather · Metal clasp","confidence":<60-98>,"label":"2-4 word headline","findings":[{"s":"pass"|"warn"|"fail","rule":"Short rule","detail":"1-2 sentence explanation"}],"next_steps":[{"title":"Short action","detail":"1-2 sentences"}]}

Include 3-5 findings citing specific policy rules. Include next_steps ONLY when verdict is warn or fail: 1-3 concrete, venue-specific alternatives (use the parking/rideshare context if it mentions lockers, storage, lots, or leave-in-car options; otherwise suggest practical options like returning the bag to a car, using a nearby bag storage service, or swapping to an allowed clear bag). Never leave a fail without a path forward. Omit next_steps entirely on pass.`;
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': process.env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
        body: JSON.stringify({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 1000,
          messages: [{ role: 'user', content: [
            { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: imageB64 } },
            { type: 'text', text: prompt }
          ] }]
        }),
      });
      const data = await response.json();
      const text = (data?.content?.[0]?.text || '').trim().replace(/```json|```/g, '').trim();
      try {
        return { statusCode: 200, headers, body: JSON.stringify(JSON.parse(text)) };
      } catch {
        return { statusCode: 500, headers, body: JSON.stringify({ error: 'Parse failed', raw: text.slice(0, 200) }) };
      }
    }

    // ── Ticketmaster (authenticated keyword search — used by Concerto+) ──
    if (service === 'ticketmaster') {
      const tmKey = process.env.TICKETMASTER_API_KEY || process.env.TM_API_KEY;
      if (!tmKey) return { statusCode: 500, headers, body: JSON.stringify({ error: 'TM key not configured' }) };
      const { keyword, size = 10 } = body;
      const url = `${TM}/events.json?apikey=${tmKey}`
        + `&keyword=${encodeURIComponent(keyword || '')}`
        + `&size=${Math.min(Number(size) || 10, 50)}&sort=date,asc&classificationName=music`;
      const response = await fetch(url);
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    // ── Google Places nearby ──
    if (service === 'places_nearby') {
      const { lat, lng, type, keyword, radius = 2000 } = body;
      const url = `https://maps.googleapis.com/maps/api/place/nearbysearch/json`
        + `?location=${encodeURIComponent(lat)},${encodeURIComponent(lng)}`
        + `&radius=${Math.min(Number(radius) || 2000, 50000)}`
        + `&type=${encodeURIComponent(type || '')}&keyword=${encodeURIComponent(keyword || '')}`
        + `&key=${process.env.GOOGLE_MAPS_API_KEY}`;
      const response = await fetch(url);
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    // ── Google Geocode ──
    if (service === 'geocode') {
      const { address } = body;
      const url = `https://maps.googleapis.com/maps/api/geocode/json`
        + `?address=${encodeURIComponent(address || '')}&key=${process.env.GOOGLE_MAPS_API_KEY}`;
      const response = await fetch(url);
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Unknown service' }) };
  } catch (err) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: err.message }) };
  }
};
