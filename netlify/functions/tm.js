// netlify/functions/tm.js
// Server-side proxy for the Ticketmaster Discovery API. Keeps the API key out of client code.
// Pages call /.netlify/functions/tm/<resource>.json?<params>  (no apikey needed);
// this injects the real key from the TM_API_KEY env var and forwards to Ticketmaster
// through the shared cache in lib/tm-cache.js (see there for TTLs and the stale fallback).

const { tmFetch } = require('./lib/tm-cache');

const ALLOWED = new Set(['attractions', 'events', 'venues']);
const ALLOW_REFERER = ['concertocity.com', '.netlify.app']; // legit callers; lenient (missing referer is allowed)
const MAX_AGE = { events: 60, venues: 3600, attractions: 3600 };

exports.handler = async function (event) {
  const key = process.env.TICKETMASTER_API_KEY || process.env.TM_API_KEY;
  if (!key) return { statusCode: 500, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'TM key not configured' }) };

  // Anti-piggyback check: if a Referer is present, its hostname must be ours
  // (exact match or a subdomain), parsed, not matched as a substring.
  const ref = event.headers && (event.headers.referer || event.headers.Referer);
  let refHost = '';
  try { refHost = ref ? new URL(ref).hostname.toLowerCase() : ''; } catch { refHost = 'invalid'; }
  const hostOk = (h) => ALLOW_REFERER.some(a => a.startsWith('.') ? h.endsWith(a) : (h === a || h.endsWith('.' + a)));
  if (ref && !hostOk(refHost)) {
    return { statusCode: 403, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'forbidden' }) };
  }

  // Resource = the <name> in /<name>.json anywhere in the path (events, venues, attractions)
  const m = (event.path || '').match(/\/([a-z]+)\.json/i);
  const resource = (m ? m[1] : (event.queryStringParameters && event.queryStringParameters.resource) || '').toLowerCase();
  if (!ALLOWED.has(resource)) return { statusCode: 400, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'bad resource' }) };

  // Rebuild the query; tmFetch drops any client apikey and injects the real one.
  let qs = event.rawQuery;
  if (!qs && event.queryStringParameters) {
    qs = Object.entries(event.queryStringParameters).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
  }
  const params = new URLSearchParams(qs || '');
  params.delete('resource');

  const r = await tmFetch(resource, params, { key, event });
  return {
    statusCode: r.status,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': r.status === 200 ? `public, max-age=${MAX_AGE[resource]}` : 'no-store',
      'X-Concerto-Cache': r.cache,
    },
    body: r.body,
  };
};
