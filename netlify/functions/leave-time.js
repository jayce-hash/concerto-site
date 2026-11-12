// Leave Time (Concerto+): how long the trip is right now, from where the fan is to where their
// night starts (dinner, or the venue). The app turns that into "Leave by 5:05 PM".
//
// Travel times come from Apple's Maps Server API. Nothing is stored: the two coordinates are
// used for this one answer and are not logged.
//
// Needs three environment variables from the Apple Developer account:
//   APPLE_MAPS_TEAM_ID       the 10-character Team ID
//   APPLE_MAPS_KEY_ID        the 10-character Key ID of a key with the Maps service enabled
//   APPLE_MAPS_PRIVATE_KEY   the contents of that key's .p8 file (BEGIN and END lines included)
// Without them the function answers 503 and the app simply doesn't show Leave Time.
//
// Access: a signed-in fan with Concerto+ or an active Show Pass, the same rule as the other
// Concerto+ tools.

const crypto = require('crypto');
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
const MAPS = 'https://maps-api.apple.com/v1';
const MODES = { rideshare: '', drive: '', transit: 'Transit', walk: 'Walking' }; // '' is Apple's default: by car

const b64url = (x) => Buffer.from(x).toString('base64').replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');

// The signed token Apple asks for: ES256, the key id in the header, the team as issuer, and
// the server_api scope. Short-lived; it is only used to fetch an access token.
function authToken(now = Math.floor(Date.now() / 1000)) {
  const key = String(process.env.APPLE_MAPS_PRIVATE_KEY || '').replace(/\\n/g, '\n').trim();
  const head = b64url(JSON.stringify({ alg: 'ES256', kid: process.env.APPLE_MAPS_KEY_ID, typ: 'JWT' }));
  const body = b64url(JSON.stringify({ iss: process.env.APPLE_MAPS_TEAM_ID, iat: now, exp: now + 600, scope: 'server_api' }));
  const sig = crypto.sign('sha256', Buffer.from(`${head}.${body}`), { key, dsaEncoding: 'ieee-p1363' });
  return `${head}.${body}.${b64url(sig)}`;
}

// Apple's access token lasts 30 minutes. One is kept for as long as this function stays warm.
let access = { token: '', until: 0 };
async function accessToken() {
  if (access.token && Date.now() < access.until) return access.token;
  const res = await fetch(`${MAPS}/token`, { headers: { Authorization: `Bearer ${authToken()}` } });
  if (!res.ok) throw new Error(`maps token ${res.status}`);
  const data = await res.json();
  if (!data.accessToken) throw new Error('maps token empty');
  access = { token: data.accessToken, until: Date.now() + Math.max(60, (Number(data.expiresInSeconds) || 1800) - 120) * 1000 };
  return access.token;
}

async function allowed(userId) {
  const { data: profile } = await supabase.from('profiles').select('is_premium').eq('id', userId).single();
  if (profile?.is_premium === true) return true;
  const { data: passes } = await supabase.from('show_passes').select('until').eq('user_id', userId).gt('until', new Date().toISOString()).limit(1);
  return Boolean(passes && passes.length);
}

const coord = (p) => {
  const lat = Number(p && p.lat), lng = Number(p && p.lng);
  return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180 && !(lat === 0 && lng === 0) ? { lat, lng } : null;
};
function miles(a, b) {
  const r = 3958.8, rad = (d) => (d * Math.PI) / 180;
  const h = Math.sin(rad(b.lat - a.lat) / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(rad(b.lng - a.lng) / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(h));
}

exports.handler = async (event) => {
  const headers = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers, body: JSON.stringify({ error: 'Method not allowed' }) };
  if (!process.env.APPLE_MAPS_TEAM_ID || !process.env.APPLE_MAPS_KEY_ID || !process.env.APPLE_MAPS_PRIVATE_KEY) {
    return { statusCode: 503, headers, body: JSON.stringify({ error: 'not_configured' }) };
  }
  try {
    const bearer = (event.headers.authorization || event.headers.Authorization || '').replace(/^Bearer\s+/i, '');
    if (!bearer) return { statusCode: 401, headers, body: JSON.stringify({ error: 'Sign in required' }) };
    const { data: auth, error: authErr } = await supabase.auth.getUser(bearer);
    if (authErr || !auth?.user) return { statusCode: 401, headers, body: JSON.stringify({ error: 'Sign in required' }) };
    if (!(await allowed(auth.user.id))) return { statusCode: 403, headers, body: JSON.stringify({ error: 'Concerto+ required' }) };

    let body = {};
    try { body = JSON.parse(event.body || '{}'); } catch (_) {}
    const from = coord(body.from), to = coord(body.to);
    const mode = Object.prototype.hasOwnProperty.call(MODES, body.mode) ? body.mode : 'drive';
    if (!from || !to) return { statusCode: 400, headers, body: JSON.stringify({ error: 'Two places are required' }) };
    // Leave Time is for the trip to tonight's show. A fan who is still far away gets no answer.
    if (miles(from, to) > 250) return { statusCode: 200, headers, body: JSON.stringify({ far: true }) };

    const params = new URLSearchParams({ origin: `${from.lat},${from.lng}`, destinations: `${to.lat},${to.lng}` });
    if (MODES[mode]) params.set('transportType', MODES[mode]);
    let res = await fetch(`${MAPS}/etas?${params}`, { headers: { Authorization: `Bearer ${await accessToken()}` } });
    if (res.status === 401) { // the kept access token expired early: fetch a new one, once
      access = { token: '', until: 0 };
      res = await fetch(`${MAPS}/etas?${params}`, { headers: { Authorization: `Bearer ${await accessToken()}` } });
    }
    if (res.status === 429) return { statusCode: 503, headers, body: JSON.stringify({ error: 'busy' }) };
    if (!res.ok) return { statusCode: 502, headers, body: JSON.stringify({ error: 'No travel time' }) };
    const eta = ((await res.json()).etas || [])[0];
    const seconds = Number(eta && eta.expectedTravelTimeSeconds);
    if (!Number.isFinite(seconds) || seconds <= 0) return { statusCode: 502, headers, body: JSON.stringify({ error: 'No travel time' }) };
    return { statusCode: 200, headers, body: JSON.stringify({
      seconds: Math.round(seconds),
      usualSeconds: Number.isFinite(Number(eta.staticTravelTimeSeconds)) ? Math.round(Number(eta.staticTravelTimeSeconds)) : null,
      meters: Number.isFinite(Number(eta.distanceMeters)) ? Math.round(Number(eta.distanceMeters)) : null,
      mode,
    }) };
  } catch (err) {
    console.error('leave-time:', String(err && err.message || err).slice(0, 200));
    return { statusCode: 502, headers, body: JSON.stringify({ error: 'No travel time' }) };
  }
};

exports._test = { authToken };
