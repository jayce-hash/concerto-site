// netlify/functions/lib/tm-cache.js
// One shared cache in front of the Ticketmaster Discovery API, so thousands of app opens
// cost a handful of Ticketmaster calls instead of one each.
//
// Why: every Concerto user, the website and the alerts job share ONE Ticketmaster key
// (default quota 5,000 calls a day, 5 a second). Before this, every request went straight
// through: the app sends startDateTime to the second and raw GPS, so no two requests matched
// and nothing could be reused. On 2026-09-28 the key ran out and Near Me went empty for everyone.
//
// How:
//   1. Normalise the request so equivalent requests share one key: times rounded down to
//      15 minutes, lat/lng rounded to 2 decimals (about 1 km), params sorted, apikey removed.
//      The normalised request is also what gets sent, so the cached answer matches it exactly.
//   2. Two layers: a per-instance memory map (instant) and Netlify Blobs (shared by every
//      function instance and every deploy of this site).
//   3. Fresh for TTL: events 10 minutes; venues and attractions 7 days (names and photos).
//   4. If Ticketmaster fails (429 over quota, 5xx, network), serve the last good answer up to
//      3 days old instead of an empty screen, and pause calls for 2 minutes after a 429.
//   5. Never cache a failure.
// If Netlify Blobs is unavailable (local runs, misconfiguration) it falls back to memory only
// and never throws, so the worst case is today's behaviour.

const crypto = require('crypto');

const TM_BASE = 'https://app.ticketmaster.com/discovery/v2';
const MIN = 60 * 1000;
const TTL = { events: 10 * MIN, venues: 7 * 24 * 60 * MIN, attractions: 7 * 24 * 60 * MIN };
const STALE_MAX = 3 * 24 * 60 * MIN;
const COOLDOWN = 2 * MIN;
const MEM_MAX = 500;

const mem = new Map();          // key -> { t, status, body }
let coolUntil = 0;              // this instance's 429 pause
let blobsStore;                 // undefined = not tried, null = unavailable

function store(event) {
  if (blobsStore !== undefined) return blobsStore;
  try {
    const blobs = require('@netlify/blobs');
    if (event && blobs.connectLambda) blobs.connectLambda(event);   // Lambda-style handlers need this once
    blobsStore = blobs.getStore('tm-cache');
  } catch (e) {
    blobsStore = null;
  }
  return blobsStore;
}

const floorTo = (iso, step) => {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  return new Date(Math.floor(t / step) * step).toISOString().replace(/\.\d{3}Z$/, 'Z');
};

// Returns the params that will actually be sent (without apikey), normalised.
function normalise(params) {
  const p = new URLSearchParams(params);
  p.delete('apikey');
  for (const k of ['startDateTime', 'endDateTime']) if (p.get(k)) p.set(k, floorTo(p.get(k), 15 * MIN));
  const ll = p.get('latlong');
  if (ll) {
    const [a, b] = ll.split(',').map(Number);
    if (Number.isFinite(a) && Number.isFinite(b)) p.set('latlong', `${a.toFixed(2)},${b.toFixed(2)}`);
  }
  if (p.get('keyword')) p.set('keyword', p.get('keyword').trim());
  const sorted = new URLSearchParams([...p.entries()].sort(([x], [y]) => (x < y ? -1 : x > y ? 1 : 0)));
  return sorted;
}

const keyOf = (resource, p) => crypto.createHash('sha256').update(`${resource}?${p.toString()}`).digest('hex').slice(0, 40);

async function readBlob(s, key) {
  if (!s) return null;
  try { return await s.get(key, { type: 'json' }); } catch { return null; }
}
async function writeBlob(s, key, value) {
  if (!s) return;
  try { await s.setJSON(key, value); } catch { /* cache write failures never fail the request */ }
}
function remember(key, value) {
  if (mem.size >= MEM_MAX) mem.delete(mem.keys().next().value);
  mem.set(key, value);
}

/**
 * Fetch a Ticketmaster Discovery resource through the shared cache.
 * @param {'events'|'venues'|'attractions'} resource
 * @param {string|URLSearchParams|object} params  query params (apikey is ignored and injected here)
 * @param {object} [opts] { key: api key, event: the Netlify function event, now: ms (tests), fetchImpl (tests) }
 * @returns {Promise<{status:number, body:string, cache:'hit'|'miss'|'stale'|'bypass'}>}
 */
async function tmFetch(resource, params, opts = {}) {
  const now = opts.now ?? Date.now();
  const fetchImpl = opts.fetchImpl ?? fetch;
  const p = normalise(params);
  const key = keyOf(resource, p);
  const ttl = TTL[resource] ?? 10 * MIN;
  const s = opts.store !== undefined ? opts.store : store(opts.event);

  let cached = mem.get(key);
  if (!cached || now - cached.t >= ttl) {
    const fromBlob = await readBlob(s, key);
    if (fromBlob && (!cached || fromBlob.t > cached.t)) { cached = fromBlob; remember(key, fromBlob); }
  }
  if (cached && now - cached.t < ttl) return { status: cached.status, body: cached.body, cache: 'hit' };

  const stale = () => (cached && now - cached.t < STALE_MAX ? { status: cached.status, body: cached.body, cache: 'stale' } : null);
  if (now < coolUntil) return stale() ?? { status: 429, body: JSON.stringify({ error: 'Ticketmaster is busy, try again shortly' }), cache: 'bypass' };

  const send = new URLSearchParams(p);
  send.set('apikey', opts.key || process.env.TICKETMASTER_API_KEY || process.env.TM_API_KEY || '');
  let r, body;
  try {
    r = await fetchImpl(`${TM_BASE}/${resource}.json?${send.toString()}`);
    body = await r.text();
  } catch (e) {
    return stale() ?? { status: 502, body: JSON.stringify({ error: 'proxy failed' }), cache: 'bypass' };
  }
  if (r.status === 429) coolUntil = now + COOLDOWN;
  if (r.status !== 200) return stale() ?? { status: r.status, body, cache: 'bypass' };

  const entry = { t: now, status: 200, body };
  remember(key, entry);
  await writeBlob(s, key, entry);
  return { status: 200, body, cache: 'miss' };
}

module.exports = { tmFetch, normalise, _reset: () => { mem.clear(); coolUntil = 0; blobsStore = undefined; } };
