// Shared protection for public Netlify functions (Sep 2026).
// - Origin: browsers always send Origin or Referer on these calls; a present but
//   foreign one is refused. The iPhone app sends neither, so absent is allowed.
// - CORS: echo our own origins only (was '*'), so other sites cannot read responses.
// - Rate limit: best effort, per function instance and client IP. It stops a single
//   script hammering an endpoint; spend alerts in Google Cloud and Anthropic are
//   the backstop (see SECURITY-AND-LEGAL.md).
const OURS = ['concertocity.com', 'www.concertocity.com', 'localhost', '127.0.0.1'];
function hostOk(h) { h = String(h || '').toLowerCase(); return OURS.includes(h) || h.endsWith('.concertocity.com') || h.endsWith('.netlify.app'); }
function originOf(event) {
  const hd = event.headers || {};
  const raw = hd.origin || hd.Origin || hd.referer || hd.Referer || '';
  if (!raw) return { present: false, ok: true, origin: '' };
  try { const u = new URL(raw); return { present: true, ok: hostOk(u.hostname), origin: u.origin }; }
  catch (e) { return { present: true, ok: false, origin: '' }; }
}
function corsHeaders(event, methods) {
  const o = originOf(event);
  return { 'Access-Control-Allow-Origin': o.present && o.ok ? o.origin : 'https://concertocity.com', 'Vary': 'Origin',
           'Access-Control-Allow-Headers': 'Content-Type, Authorization', 'Access-Control-Allow-Methods': methods || 'GET, OPTIONS' };
}
const hits = new Map();
function clientIp(event) { const h = event.headers || {}; return h['x-nf-client-connection-ip'] || h['client-ip'] || String(h['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown'; }
function limited(event, max, windowMs) {
  const key = clientIp(event), now = Date.now(), w = windowMs || 60000;
  const r = hits.get(key) || { n: 0, t: now };
  if (now - r.t > w) { r.n = 0; r.t = now; }
  r.n += 1; hits.set(key, r);
  if (hits.size > 5000) hits.clear();
  return r.n > max;
}
function refuse(event, status, msg, methods) {
  return { statusCode: status, headers: { ...corsHeaders(event, methods), 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }, body: JSON.stringify({ error: msg }) };
}
module.exports = { originOf, corsHeaders, limited, refuse };
