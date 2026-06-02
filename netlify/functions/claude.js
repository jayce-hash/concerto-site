// netlify/functions/claude.js
// Shared proxy for all Concerto premium features
// Handles: Claude AI, Ticketmaster, Google Places, Geocode, Bag Check
//
// HARDENED:
//   - Requires a valid Supabase JWT on every request (Authorization: Bearer <token>)
//   - Premium (is_premium) required for the Anthropic-backed branches (claude, bag_check)
//   - 'claude' branch clamps model to an allowlist and caps max_tokens (no longer an open Anthropic proxy)
//   - CORS locked to known origins instead of '*'
// Note: CORS only constrains browsers; the JWT + premium check is the real lock.

const { createClient } = require('@supabase/supabase-js');

const ALLOWED_ORIGINS = [
  'https://concertocity.com',
  'https://www.concertocity.com',
];

// Only these models may be requested through the proxy, with a hard token ceiling.
const ALLOWED_MODELS = new Set([
  'claude-haiku-4-5-20251001',
]);
const DEFAULT_MODEL = 'claude-haiku-4-5-20251001';
const MAX_TOKENS_CAP = 4096;

// Branches that cost real money on Anthropic — gated behind premium.
const PREMIUM_SERVICES = new Set(['claude', 'bag_check']);

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

  // ── Auth: verify Supabase JWT ───────────────────
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

  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON' }) };
  }
  const { service } = body;

  // ── Premium gate for expensive branches ─────────
  if (PREMIUM_SERVICES.has(service)) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('is_premium')
      .eq('id', user.id)
      .single();
    if (!profile?.is_premium) {
      return { statusCode: 403, headers, body: JSON.stringify({ error: 'Premium required' }) };
    }
  }

  try {
    // ── Claude (AI itinerary, chat) ─────────────────
    if (service === 'claude') {
      const model = ALLOWED_MODELS.has(body.model) ? body.model : DEFAULT_MODEL;
      const max_tokens = Math.min(Number(body.max_tokens) || 1024, MAX_TOKENS_CAP);
      const payload = { model, max_tokens };
      if (typeof body.system === 'string') payload.system = body.system;
      if (Array.isArray(body.messages)) payload.messages = body.messages;

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type':      'application/json',
          'x-api-key':         process.env.ANTHROPIC_API_KEY,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    // ── Bag Check (image analysis) ──────────────────
    if (service === 'bag_check') {
      const { imageB64, venue } = body;
      if (!imageB64 || !venue) {
        return { statusCode: 400, headers, body: JSON.stringify({ error: 'Missing image or venue' }) };
      }
      const policy = `Venue: ${venue.n} (${venue.loc})
Policy: ${venue.policy_text || ''}
Allowed: ${(venue.allows || []).join('; ')}
Prohibited: ${(venue.denies || []).join('; ')}`;

      const prompt = `You are Concerto's Bag Check AI. Analyze the bag in this photo for entry to ${venue.n}.

${policy}

Respond ONLY with valid JSON, no markdown:
{"verdict":"pass"|"warn"|"fail","bag_type":"e.g. Small Leather Clutch","dims":"e.g. Est. 6\\" × 4\\" · Leather · Metal clasp","confidence":<60-98>,"label":"2-4 word headline","findings":[{"s":"pass"|"warn"|"fail","rule":"Short rule","detail":"1-2 sentence explanation"}]}

Include 3-5 findings citing specific policy rules.`;

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type':      'application/json',
          'x-api-key':         process.env.ANTHROPIC_API_KEY,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 1000,
          messages: [{
            role: 'user',
            content: [
              { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: imageB64 } },
              { type: 'text', text: prompt }
            ]
          }]
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

    // ── Ticketmaster ────────────────────────────────
    if (service === 'ticketmaster') {
      const { keyword, size = 10 } = body;
      const url = `https://app.ticketmaster.com/discovery/v2/events.json`
        + `?apikey=${process.env.TICKETMASTER_API_KEY}`
        + `&keyword=${encodeURIComponent(keyword || '')}`
        + `&size=${Math.min(Number(size) || 10, 50)}&sort=date,asc&classificationName=music`;
      const response = await fetch(url);
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    // ── Google Places nearby ────────────────────────
    if (service === 'places_nearby') {
      const { lat, lng, type, keyword, radius = 2000 } = body;
      const url = `https://maps.googleapis.com/maps/api/place/nearbysearch/json`
        + `?location=${encodeURIComponent(lat)},${encodeURIComponent(lng)}`
        + `&radius=${Math.min(Number(radius) || 2000, 50000)}`
        + `&type=${encodeURIComponent(type || '')}`
        + `&keyword=${encodeURIComponent(keyword || '')}`
        + `&key=${process.env.GOOGLE_MAPS_API_KEY}`;
      const response = await fetch(url);
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    // ── Google Geocode ──────────────────────────────
    if (service === 'geocode') {
      const { address } = body;
      const url = `https://maps.googleapis.com/maps/api/geocode/json`
        + `?address=${encodeURIComponent(address || '')}`
        + `&key=${process.env.GOOGLE_MAPS_API_KEY}`;
      const response = await fetch(url);
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Unknown service' }) };

  } catch (err) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: err.message }) };
  }
};
