// netlify/functions/tm.js
// Server-side proxy for the Ticketmaster Discovery API. Keeps the API key out of client code.
// Pages call /.netlify/functions/tm/<resource>.json?<params>  (no apikey needed);
// this injects the real key from the TM_API_KEY env var and forwards to Ticketmaster.

const TM_BASE = 'https://app.ticketmaster.com/discovery/v2';
const ALLOWED = new Set(['attractions', 'events', 'venues']);
// 'claude.ai' added Aug 13 so a Claude Design prototype can pull real
// tour/artist images through this proxy instead of needing its own
// Ticketmaster key baked into client-side code, which browser dev
// tools would make trivially visible to anyone who loads the page.
// If Claude Design's canvas actually runs from a different origin
// (a subdomain, a sandboxed iframe host), that's the string to swap
// in here instead -- check the failing request's Referer header if
// this still 403s.
const ALLOW_REFERER = ['concertocity.com', '.netlify.app', 'claude.ai']; // legit callers; lenient (missing referer is allowed)
const CORS = { 'Access-Control-Allow-Origin': '*' };

export async function handler(event) {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: CORS, body: '' };
  }
  const key = process.env.TICKETMASTER_API_KEY || process.env.TM_API_KEY;
  if (!key) return { statusCode: 500, headers: { ...CORS, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'TM key not configured' }) };

  // Light anti-piggyback check: if a Referer is present, it must look like our site.
  const ref = event.headers && (event.headers.referer || event.headers.Referer);
  if (ref && !ALLOW_REFERER.some(h => ref.includes(h))) {
    return { statusCode: 403, headers: { ...CORS, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'forbidden' }) };
  }

  // Resource = the <name> in /<name>.json anywhere in the path (events, venues, attractions)
  const m = (event.path || '').match(/\/([a-z]+)\.json/i);
  const resource = (m ? m[1] : (event.queryStringParameters && event.queryStringParameters.resource) || '').toLowerCase();
  if (!ALLOWED.has(resource)) return { statusCode: 400, headers: { ...CORS, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'bad resource' }) };

  // Rebuild the query, drop any client apikey, inject the real one.
  let qs = event.rawQuery;
  if (!qs && event.queryStringParameters) {
    qs = Object.entries(event.queryStringParameters).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
  }
  const params = new URLSearchParams(qs || '');
  params.delete('apikey');
  params.delete('resource');
  params.set('apikey', key);

  try {
    const r = await fetch(`${TM_BASE}/${resource}.json?${params.toString()}`);
    const body = await r.text();
    return { statusCode: r.status, headers: { ...CORS, 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=60' }, body };
  } catch (e) {
    return { statusCode: 502, headers: { ...CORS, 'Content-Type': 'application/json' }, body: JSON.stringify({ error: 'proxy failed' }) };
  }
}
