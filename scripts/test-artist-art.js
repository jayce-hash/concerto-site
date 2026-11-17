// Offline tests for netlify/functions/artist-art.js. No network: Ticketmaster is faked.
// Run: node --test scripts/test-artist-art.js
const test = require('node:test');
const assert = require('node:assert');
const { artKey, pickImage, matchArtist, fill, publicMap } = require('../netlify/functions/artist-art')._test;

const img = (w, ratio = '16_9') => ({ url: `https://s1.ticketm.net/x_${ratio}_${w}.jpg`, width: w, ratio });
const answer = (name, images) => ({ status: 200, body: JSON.stringify({ _embedded: { attractions: [{ name: 'Someone Else', images: [img(1024)] }, { name, images }] } }) });

test('the key matches the one Medley uses', () => {
  assert.equal(artKey('Beyoncé'), 'beyonce'); assert.equal(artKey('AC/DC'), 'ac dc'); assert.equal(artKey('  P!nk '), 'p nk');
});
test('the smallest wide image of 640 or more is used', () => {
  assert.equal(pickImage([img(2048), img(305), img(640), img(1024), img(1024, '3_2')]), img(640).url);
  assert.equal(pickImage([img(100), img(205)]), img(205).url);
  assert.equal(pickImage([{ url: 'http://not-secure/x.jpg', width: 900, ratio: '16_9' }]), null);
  assert.equal(pickImage([]), null);
});
test('only the performer with the same name counts, never the first result', () => {
  const list = [{ name: 'Ed Sheeran Tribute', images: [] }, { name: 'ED SHEERAN', images: [] }];
  assert.equal(matchArtist(list, 'Ed Sheeran').name, 'ED SHEERAN');
  assert.equal(matchArtist([{ name: 'Ed Sheeran Tribute' }], 'Ed Sheeran'), null);
});
test('a run looks up a limited number and remembers the answers', async () => {
  const artists = new Map([['a', 'A'], ['b', 'B'], ['c', 'C'], ['d', 'D'], ['e', 'E']]);
  const known = {}; const calls = [];
  const lookup = async (name) => { calls.push(name); return name === 'B' ? answer('Nobody', [img(640)]) : answer(name, [img(640)]); };
  const first = await fill(artists, known, lookup, 1000, 3);
  assert.equal(calls.length, 3); assert.equal(first.left, 2); assert.equal(known.b.art, null);
  const second = await fill(artists, known, lookup, 2000, 3);
  assert.equal(calls.length, 5); assert.equal(second.left, 0);
  const third = await fill(artists, known, lookup, 3000, 3);
  assert.equal(calls.length, 5); assert.equal(third.changed, false);
  assert.deepEqual(Object.keys(publicMap(artists, known)), ['a', 'c', 'd', 'e']);
});
test('a failure is not remembered, and a 429 stops the run', async () => {
  const artists = new Map(['a', 'b', 'c', 'd', 'e', 'f'].map((k) => [k, k.toUpperCase()]));
  const known = {}; let n = 0;
  const r = await fill(artists, known, async () => { n += 1; return { status: n === 1 ? 500 : 429, body: '{}' }; }, 1000, 6);
  assert.equal(r.left, 6); assert.deepEqual(known, {}); assert.ok(n <= 4);
});
test('an artist with no photo is asked about again after a week', async () => {
  const artists = new Map([['a', 'A']]); const known = { a: { art: null, t: 0 } }; let n = 0;
  await fill(artists, known, async () => { n += 1; return answer('A', [img(640)]); }, 3 * 24 * 3600 * 1000);
  assert.equal(n, 0);
  await fill(artists, known, async () => { n += 1; return answer('A', [img(640)]); }, 8 * 24 * 3600 * 1000);
  assert.equal(n, 1); assert.ok(known.a.art);
});
