// Offline tests for netlify/functions/lib/tm-cache.js and tm.js. No network: Ticketmaster and
// Netlify Blobs are both faked.  Run: npm run test:tm-cache
const test = require('node:test');
const assert = require('node:assert');
const cache = require('../netlify/functions/lib/tm-cache');

function fakeTM(status = 200) {
  const calls = [];
  const impl = async (url) => { calls.push(url); return { status: impl.status, text: async () => JSON.stringify({ n: calls.length }) }; };
  impl.status = status; impl.calls = calls; return impl;
}
function fakeStore() {
  const m = new Map();
  return { m, get: async (k) => (m.has(k) ? JSON.parse(m.get(k)) : null), setJSON: async (k, v) => { m.set(k, JSON.stringify(v)); } };
}
const T0 = Date.parse('2026-09-28T21:40:00Z');
const q = (sec, lat) => ({ startDateTime: `2026-09-28T21:4${sec}:1${sec}Z`, endDateTime: `2026-10-05T21:4${sec}:1${sec}Z`, latlong: `${lat},-77.02091`, radius: '75', size: '20', apikey: 'client-junk' });

test('equivalent requests (seconds, GPS jitter) cost one Ticketmaster call', async () => {
  cache._reset(); const tm = fakeTM(); const store = fakeStore();
  const a = await cache.tmFetch('events', q(1, '38.89812'), { key: 'K', now: T0, fetchImpl: tm, store });
  const b = await cache.tmFetch('events', q(3, '38.89977'), { key: 'K', now: T0 + 5000, fetchImpl: tm, store });
  assert.equal(tm.calls.length, 1); assert.equal(a.cache, 'miss'); assert.equal(b.cache, 'hit'); assert.equal(a.body, b.body);
});

test('the real key is sent, a client key is dropped, and the key is never cached', async () => {
  cache._reset(); const tm = fakeTM(); const store = fakeStore();
  await cache.tmFetch('events', q(1, '38.9'), { key: 'REAL', now: T0, fetchImpl: tm, store });
  assert.match(tm.calls[0], /apikey=REAL/); assert.doesNotMatch(tm.calls[0], /client-junk/);
  assert.ok(![...store.m.values()].some((v) => v.includes('REAL')));
  assert.match(tm.calls[0], /latlong=38\.90%2C-77\.02/); assert.match(tm.calls[0], /startDateTime=2026-09-28T21%3A30%3A00Z/);
});

test('events refresh after 10 minutes; venues and attractions keep 7 days', async () => {
  cache._reset(); const tm = fakeTM(); const store = fakeStore();
  await cache.tmFetch('events', { keyword: 'x' }, { key: 'K', now: T0, fetchImpl: tm, store });
  await cache.tmFetch('events', { keyword: 'x' }, { key: 'K', now: T0 + 9 * 60e3, fetchImpl: tm, store });
  assert.equal(tm.calls.length, 1);
  await cache.tmFetch('events', { keyword: 'x' }, { key: 'K', now: T0 + 11 * 60e3, fetchImpl: tm, store });
  assert.equal(tm.calls.length, 2);
  await cache.tmFetch('attractions', { keyword: 'Charli xcx' }, { key: 'K', now: T0, fetchImpl: tm, store });
  await cache.tmFetch('attractions', { keyword: 'Charli xcx ' }, { key: 'K', now: T0 + 6 * 86400e3, fetchImpl: tm, store });
  assert.equal(tm.calls.length, 3);
});

test('a second function instance reuses the shared Blobs cache', async () => {
  cache._reset(); const tm = fakeTM(); const store = fakeStore();
  await cache.tmFetch('venues', { keyword: 'Capital One Arena', size: '1' }, { key: 'K', now: T0, fetchImpl: tm, store });
  cache._reset();                                   // new instance: empty memory, same store
  const r = await cache.tmFetch('venues', { keyword: 'Capital One Arena', size: '1' }, { key: 'K', now: T0 + 60e3, fetchImpl: tm, store });
  assert.equal(tm.calls.length, 1); assert.equal(r.cache, 'hit');
});

test('over quota: serve the last good answer, pause calls for 2 minutes, never cache the error', async () => {
  cache._reset(); const tm = fakeTM(); const store = fakeStore();
  const good = await cache.tmFetch('events', { keyword: 'y' }, { key: 'K', now: T0, fetchImpl: tm, store });
  tm.status = 429;
  const r1 = await cache.tmFetch('events', { keyword: 'y' }, { key: 'K', now: T0 + 20 * 60e3, fetchImpl: tm, store });
  assert.equal(r1.cache, 'stale'); assert.equal(r1.status, 200); assert.equal(r1.body, good.body);
  const before = tm.calls.length;
  const r2 = await cache.tmFetch('events', { keyword: 'y' }, { key: 'K', now: T0 + 21 * 60e3, fetchImpl: tm, store });
  assert.equal(tm.calls.length, before, 'no Ticketmaster call during the pause'); assert.equal(r2.cache, 'stale');
  const r3 = await cache.tmFetch('events', { keyword: 'never-seen' }, { key: 'K', now: T0 + 21 * 60e3, fetchImpl: tm, store });
  assert.equal(r3.status, 429);
  tm.status = 200;
  const r4 = await cache.tmFetch('events', { keyword: 'y' }, { key: 'K', now: T0 + 24 * 60e3, fetchImpl: tm, store });
  assert.equal(r4.cache, 'miss');
});

test('network failure with nothing cached returns 502 and caches nothing', async () => {
  cache._reset(); const store = fakeStore();
  const r = await cache.tmFetch('events', { keyword: 'z' }, { key: 'K', now: T0, fetchImpl: async () => { throw new Error('down'); }, store });
  assert.equal(r.status, 502); assert.equal(store.m.size, 0);
});

test('works with no Blobs store at all (memory only)', async () => {
  cache._reset(); const tm = fakeTM();
  await cache.tmFetch('events', { keyword: 'm' }, { key: 'K', now: T0, fetchImpl: tm, store: null });
  const r = await cache.tmFetch('events', { keyword: 'm' }, { key: 'K', now: T0 + 1000, fetchImpl: tm, store: null });
  assert.equal(tm.calls.length, 1); assert.equal(r.cache, 'hit');
});

test('tm.js handler: same responses and checks as before, plus the cache header', async () => {
  cache._reset();
  process.env.TICKETMASTER_API_KEY = 'K';
  const calls = []; global.fetch = async (u) => { calls.push(u); return { status: 200, text: async () => '{"ok":1}' }; };
  const { handler } = require('../netlify/functions/tm.js');
  const ev = (ref, path = '/.netlify/functions/tm/events.json') => ({ path, rawQuery: 'keyword=a&apikey=evil', headers: ref ? { referer: ref } : {} });
  assert.equal((await handler(ev('https://evil.example/'))).statusCode, 403);
  assert.equal((await handler(ev(null, '/.netlify/functions/tm/users.json'))).statusCode, 400);
  const r1 = await handler(ev(null)); const r2 = await handler(ev('https://concertocity.com/near-me'));
  assert.equal(r1.statusCode, 200); assert.equal(r1.body, '{"ok":1}');
  assert.equal(r1.headers['X-Concerto-Cache'], 'miss'); assert.equal(r2.headers['X-Concerto-Cache'], 'hit');
  assert.equal(calls.length, 1); assert.doesNotMatch(calls[0], /evil/);
});
