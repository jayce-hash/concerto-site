// netlify/functions/artist-art.js
// One file of artist photos for Medley: /data/artist-art.json -> { "<plain artist name>": { art: "<image url>" } }
//
// The photos are Ticketmaster's, the same ones Concerto shows beside an artist's tour dates.
// Medley shows them beside the setlist, with a link to the tour in Concerto.
//
// Why a function and not a file: the list of artists changes whenever a tour is added, and a
// phone must never call Ticketmaster for 200 artists (one shared key, 5 calls a second,
// 5,000 a day). So the site looks each artist up ONCE, keeps the answer, and every phone
// reads the finished list. A lookup uses the same cached request the Concerto app makes, so
// an artist Concerto has already shown costs nothing.
//
// One run looks up a limited number of new artists and returns what is known so far, so it
// can never run past the function time limit. Until every artist is done the answer is only
// kept for a minute; after that, for a day.
const fs = require('fs');
const path = require('path');
const { tmFetch } = require('./lib/tm-cache');

const PER_RUN = 24;                         // new artists looked up in one run
const BUDGET_MS = 6500;                     // stop starting lookups after this long
const RETRY_EMPTY_MS = 7 * 24 * 3600 * 1000; // an artist with no photo is asked about again weekly
const BLOB_KEY = 'artist-art-v1';
let memory = null;                          // this instance's copy of what is known

/** The same plain form Medley uses to look an artist up: no accents, lower case, single spaces. */
const artKey = (artist) => String(artist || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const tight = (s) => artKey(s).replace(/ /g, '');

/** A wide image big enough for a phone, and no bigger: the smallest 16:9 at 640 px or more. */
function pickImage(images) {
  const ok = (images || []).filter((i) => i && typeof i.url === 'string' && i.url.startsWith('https://') && i.width);
  if (!ok.length) return null;
  const wide = ok.filter((i) => i.ratio === '16_9');
  const pool = (wide.length ? wide : ok).sort((a, b) => a.width - b.width);
  return (pool.find((i) => i.width >= 640) || pool[pool.length - 1]).url;
}

/** The performer whose name IS this artist. Never the first result: a wrong face is worse than none. */
function matchArtist(list, artist) {
  const target = tight(artist);
  if (!target) return null;
  return (list || []).find((a) => a && a.name && tight(a.name) === target) || null;
}

function artistsFromTours() {
  const tours = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'data', 'tours.json'), 'utf8'));
  const seen = new Map();
  for (const t of tours) { const k = artKey(t.artist); if (k && !seen.has(k)) seen.set(k, t.artist); }
  return seen;                               // plain name -> name as written
}

function blobStore(event) {
  try {
    const blobs = require('@netlify/blobs');
    if (event && blobs.connectLambda) blobs.connectLambda(event);
    return blobs.getStore('tm-cache');
  } catch { return null; }
}

/**
 * Looks up artists that are not known yet and returns everything known.
 * @param {Map<string,string>} artists plain name -> name as written
 * @param {object} known { "<plain name>": { art: string|null, t: ms } }
 * @param {(artist:string)=>Promise<{status:number, body:string}>} lookup
 */
async function fill(artists, known, lookup, now = Date.now(), perRun = PER_RUN, budget = BUDGET_MS) {
  const started = Date.now();
  const todo = [...artists.keys()].filter((k) => !known[k] || (!known[k].art && now - known[k].t > RETRY_EMPTY_MS)).slice(0, perRun);
  let changed = false, blocked = false;
  // Four at a time keeps well under Ticketmaster's five calls a second.
  for (let i = 0; i < todo.length && !blocked && Date.now() - started < budget; i += 4) {
    await Promise.all(todo.slice(i, i + 4).map(async (k) => {
      try {
        const r = await lookup(artists.get(k));
        if (r.status === 429) { blocked = true; return; }
        if (r.status !== 200) return;         // a failure is not an answer: try again next run
        const data = JSON.parse(r.body);
        const hit = matchArtist(data && data._embedded && data._embedded.attractions, artists.get(k));
        known[k] = { art: hit ? pickImage(hit.images) : null, t: now };
        changed = true;
      } catch {}
    }));
  }
  const left = [...artists.keys()].filter((k) => !known[k]).length;
  return { changed, left };
}

/** Only artists that are still on a tour, and only the ones with a photo, go out to phones. */
function publicMap(artists, known) {
  const out = {};
  for (const k of artists.keys()) if (known[k] && known[k].art) out[k] = { art: known[k].art };
  return out;
}

exports.handler = async function (event) {
  const headers = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' };
  try {
    const key = process.env.TICKETMASTER_API_KEY || process.env.TM_API_KEY;
    const artists = artistsFromTours();
    const store = blobStore(event);
    let known = memory;
    if (store) { try { const saved = await store.get(BLOB_KEY, { type: 'json' }); if (saved && typeof saved === 'object') known = saved; } catch {} }
    known = known || {};
    let left = [...artists.keys()].filter((k) => !known[k]).length;
    if (key) {
      const lookup = (artist) => tmFetch('attractions', new URLSearchParams({ keyword: artist, classificationName: 'Music', size: '10' }), { key, event });
      const r = await fill(artists, known, lookup);
      left = r.left;
      memory = known;
      if (r.changed && store) { try { await store.setJSON(BLOB_KEY, known); } catch {} }
    }
    return { statusCode: 200, headers: { ...headers, 'Cache-Control': `public, max-age=${left ? 60 : 86400}`, 'X-Concerto-Art-Left': String(left) }, body: JSON.stringify(publicMap(artists, known)) };
  } catch (e) {
    // Medley shows initials when there is no photo, so an empty list is a safe answer.
    return { statusCode: 200, headers: { ...headers, 'Cache-Control': 'no-store' }, body: '{}' };
  }
};
exports._test = { artKey, pickImage, matchArtist, fill, publicMap };
