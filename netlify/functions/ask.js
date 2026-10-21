// netlify/functions/ask.js
// Concerto AI: one answer service for the website's Ask bar and the app's search screen.
//
// How an answer is made, cheapest first:
//   1. Find what the question is about: a venue (by name, short name or former name) and/or a
//      tour (by artist), and the topic (bags, re-entry, doors, parking, rideshare, food,
//      accessibility, tickets, setlist, dates, set times).
//   2. GUIDE ANSWER (free, no AI): quote the matching lines of Concerto's own researched data,
//      with the date it was checked and a link to the section. Most questions end here.
//   3. AI ANSWER (Claude Haiku, capped): only when a venue or tour was found but the question
//      needs reasoning the quote cannot give ("what should I know before MSG?", "is a 13x7 bag
//      ok?"). The model sees only Concerto's data for that venue or tour and must say so when
//      the data does not cover the question. It never answers from general knowledge.
//
// Cost controls (all in Netlify Blobs, store "concerto-ask"):
//   - Per visitor per day: 3 AI answers free (signed out or in), 30 with Concerto+.
//   - Whole site per day and per month: ASK_DAILY_CAP (default 100), ASK_MONTHLY_CAP (default
//     1500). Over any cap, the guide answer is still given; only the AI step is skipped.
//   - Identical questions about the same venue or tour reuse a saved AI answer for 14 days.
//   - Fail closed: if the limits cannot be read, no AI call is made.
// Privacy: the question text is never stored or logged. Visitors are counted by a salted hash
// of their IP that changes daily. Cached answers are keyed by a hash of the question.

const crypto = require('crypto');
const { createClient } = require('@supabase/supabase-js');
const { corsHeaders, limited, refuse, originOf } = require('./lib/guard');
const { tmFetch } = require('./lib/tm-cache');
const { venuePartners, demoVenuePartners } = require('./lib/venue-partners');
const { demoAllowed } = require('./lib/demo-partners');

const VENUES = require('../../data/venues.json');
const INFO = require('../../data/venue_info.json');
const TOURS = require('../../data/tours.json');
const SETS = require('../../setlists.json');

const MODEL = 'claude-haiku-4-5-20251001';
const LIMITS = { anon: 3, member: 3, plus: 30 };
const DAILY_CAP = Number(process.env.ASK_DAILY_CAP || 100);
const MONTHLY_CAP = Number(process.env.ASK_MONTHLY_CAP || 1500);
const CACHE_DAYS = 14;

// ---------- text helpers ----------
const plain = (s) => ' ' + String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
  .replace(/&/g, ' and ').replace(/[’']/g, '').replace(/[^a-z0-9]+/g, ' ').trim() + ' ';
const has = (q, phrase) => q.includes(' ' + phrase.trim() + ' ');
const sents = (t) => String(t || '').split(/(?<=[.!?])\s+/).map((s) => s.trim()).filter(Boolean);
const sectionText = (s) => s ? [s.summary, s.body, s.note].filter(Boolean).join(' ').replace(/\s+/g, ' ').trim() : '';
const sha = (s) => crypto.createHash('sha256').update(s).digest('hex').slice(0, 32);

// ---------- what the question is about ----------
const GENERIC = new Set(['arena', 'center', 'centre', 'stadium', 'amphitheatre', 'amphitheater', 'theatre', 'theater', 'hall', 'field', 'park',
  'music', 'pavilion', 'ballroom', 'club', 'the', 'at', 'live', 'and', 'of', 'auditorium', 'coliseum', 'garden', 'dome', 'bank', 'credit', 'union',
  'festival', 'house', 'room', 'bowl', 'event', 'events', 'square', 'city', 'new', 'york', 'los', 'angeles']);
const ALIASES = {
  'madison-square-garden': ['msg', 'the garden'],
  'nrg-stadium': ['nrg stadium', 'nrg', 'reliant stadium'],
  'sse-arena-belfast': ['sse arena', 'the o2 belfast', 'o2 belfast'],
  'paris-la-defense-arena': ['paris la defense arena', 'la defense arena', 'plenitude arena'],
  'lenovo-center': ['pnc arena'],
  'peoplesbank-arena': ['xl center'],
  'kia-forum': ['the forum', 'kia forum'],
  'radio-city-music-hall': ['radio city'],
  'red-rocks-amphitheatre': ['red rocks'],
  'sofi-stadium': ['sofi'],
  'the-o2': ['the o2 arena', 'o2 arena', 'the o2 london'],
};
const venueKeys = [];
(function buildVenueKeys() {
  const coreCount = {};
  const cores = {};
  for (const v of VENUES) {
    const words = plain(v.name).trim().split(' ').filter((w) => !GENERIC.has(w));
    const core = words.join(' ');
    cores[v.id] = core;
    if (core.length >= 5) coreCount[core] = (coreCount[core] || 0) + 1;
  }
  for (const v of VENUES) {
    const names = new Set([plain(v.name).trim(), plain(v.name).trim().replace(/^the /, '')]);
    (ALIASES[v.id] || []).forEach((a) => names.add(plain(a).trim()));
    const core = cores[v.id];
    if (core && core.length >= 5 && coreCount[core] === 1) names.add(core);
    for (const n of names) if (n) venueKeys.push({ key: n, id: v.id });
  }
  venueKeys.sort((a, b) => b.key.length - a.key.length);
})();
const tourKeys = TOURS.map((t) => ({ key: plain(t.artist).trim(), id: t.tourId })).filter((x) => x.key.length >= 3)
  .sort((a, b) => b.key.length - a.key.length);

function findVenue(q, hint) {
  for (const k of venueKeys) if (has(q, k.key)) return k.id;
  return hint && INFO[hint] ? hint : null;
}
function findTour(q, hint) {
  for (const k of tourKeys) if (has(q, k.key)) return k.id;
  return hint && TOURS.find((t) => t.tourId === hint) ? hint : null;
}

const TOPICS = [
  ['reEntry', ['re enter', 'reenter', 're entry', 'reentry', 'come back in', 'leave and come back', 'in and out', 'step outside', 'go back in', 'leave and return']],
  ['bagPolicy', ['coat check', 'bag check', 'locker', 'lockers', 'storage', 'bag', 'bags', 'backpack', 'backpacks', 'purse', 'purses', 'clutch', 'tote', 'fanny pack', 'clear bag', 'diaper bag', 'camera bag', 'bring', 'allowed in', 'can i take', 'prohibited', 'what can i']],
  ['gates', ['doors', 'door time', 'gates', 'gate', 'entrance', 'entrances', 'which entrance', 'doors open', 'line', 'security']],
  ['parking', ['park', 'parking', 'garage', 'lot', 'lots', 'drive']],
  ['rideshare', ['uber', 'lyft', 'rideshare', 'ride share', 'taxi', 'cab', 'pickup', 'pick up spot', 'drop off', 'get home', 'getting home', 'leave after']],
  ['accessibility', ['wheelchair', 'accessible', 'accessibility', 'ada', 'disabled', 'disability', 'elevator', 'hearing', 'sensory', 'mobility']],
  ['concessions', ['food', 'eat', 'drink', 'drinks', 'beer', 'alcohol', 'snack', 'snacks', 'concession', 'concessions', 'cashless', 'cash', 'water bottle', 'water']],
  ['ticketPickup', ['will call', 'box office', 'pick up tickets', 'ticket pickup', 'print tickets', 'mobile ticket', 'tickets']],
];
const TOUR_TOPICS = [
  ['time', ['what time', 'go on', 'goes on', 'set time', 'set times', 'start', 'starts', 'headliner', 'how long', 'end', 'ends', 'over']],
  ['setlist', ['setlist', 'set list', 'songs', 'song', 'play', 'playing', 'perform', 'open with', 'opener song', 'encore', 'close with']],
  ['dates', ['when', 'dates', 'date', 'where', 'coming to', 'tour', 'tickets', 'near me', 'in']],
];
function tourTopic(q, tour) {
  if (/ (what time|go on|goes on|set time|set times|headliner|start time|starts|how long|end time|ends) /.test(q)) return 'time';
  if (/ (when|where|dates|date|coming to|tour dates|near me|next show|cities) /.test(q)) return 'dates';
  if (/ (setlist|set list|songs|song|encore|open with|opener|close with) /.test(q) || /^ (does|will|did|do) /.test(q)) return 'setlist';
  return ((SETS[tour.tourId] || {}).songs || []).length ? 'setlist' : 'dates';
}
function topicsIn(q, list) { return list.filter(([, words]) => words.some((w) => has(q, w))).map(([k]) => k); }

const TOPIC_BOOST = {
  gates: ['open', 'opens', 'doors open', 'gates open', 'before'], accessibility: ['accessible', 'wheelchair', 'ada', 'elevator', 'seating'],
  reEntry: ['re entry', 'reentry', 're enter', 'exit'], ticketPickup: ['will call', 'box office', 'pick up', 'pickup'],
  concessions: ['food', 'drink', 'beer', 'menu', 'stands', 'sold', 'offers'], parking: ['parking', 'lot', 'garage', 'park'],
  rideshare: ['rideshare', 'uber', 'lyft', 'pickup', 'zone'], bagPolicy: ['bag', 'bags', 'clear', 'size', 'allowed'],
};
const SECTION_LABEL = { bagPolicy: 'Bag policy', gates: 'Entrances and doors', parking: 'Parking', rideshare: 'Rideshare', accessibility: 'Accessibility',
  concessions: 'Food and drink', reEntry: 'Re-entry', ticketPickup: 'Tickets and will call' };
const ANCHOR = { bagPolicy: 'bag-policy', gates: 'entrances', parking: 'parking', rideshare: 'rideshare', accessibility: 'accessibility',
  concessions: 'concessions', reEntry: 're-entry', ticketPickup: 'ticket-pickup' };
const ITEM_WORDS = ['backpack', 'purse', 'clutch', 'tote', 'fanny pack', 'camera', 'umbrella', 'chair', 'blanket', 'water bottle', 'bottle', 'vape', 'e cigarette',
  'sign', 'poster', 'laptop', 'tablet', 'selfie stick', 'food', 'drink', 'cooler', 'stroller', 'diaper bag', 'medical bag', 'binoculars', 'hat', 'sunscreen',
  'battery', 'charger', 'power bank', 'lighter', 'cigarette', 'makeup', 'perfume', 'glow stick', 'fan', 'banner', 'flag', 'hydration pack', 'camelbak', 'wallet', 'phone'];
const stem = (w) => w.replace(/s$/, '');

function pretty(d) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(d || '');
  if (!m) return '';
  return `${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][+m[2] - 1]} ${+m[3]}, ${m[1]}`;
}
function venueName(id) { return (VENUES.find((v) => v.id === id) || {}).name || id; }
function source(id, key) {
  const s = (INFO[id] || {})[key] || {};
  return { label: `${venueName(id)} · ${SECTION_LABEL[key]}`, url: `/venue/${id}#${ANCHOR[key]}`, checked: pretty(s.verified), official: /^https:\/\//.test(s.officialLink || '') ? s.officialLink : '' };
}

// ---------- free guide answers ----------
function venueGuideAnswer(id, key, q) {
  const s = (INFO[id] || {})[key];
  if (!s) return null;
  const text = sectionText(s);
  if (!text) return null;
  const allowed = (s.allowed || []).map(String), prohibited = (s.prohibited || []).map(String);
  const item = itemIn(q);
  const lines = [];
  if (item) {
    const it = stem(item);
    const no = prohibited.find((x) => plain(x).includes(' ' + it));
    const yes = allowed.find((x) => plain(x).includes(' ' + it));
    if (no && !yes) lines.push(`Not allowed: ${no.replace(/\.$/, '')}.`);
    else if (yes && !no) lines.push(`Allowed: ${yes.replace(/\.$/, '')}.`);
    else if (yes && no) lines.push(`Allowed: ${yes.replace(/\.$/, '')}.`, `Not allowed: ${no.replace(/\.$/, '')}.`);
  }
  // The guide's own sentences, most relevant first, at most two.
  const words = q.trim().split(' ').filter((w) => w.length > 3 && !GENERIC.has(w));
  const topicWords = ((TOPICS.find(([k]) => k === key) || [])[1] || []).concat(TOPIC_BOOST[key] || []);
  const usable = sents(text).filter((x) => !/^Policies may change|^Review the linked/i.test(x));
  const whole = usable.filter((x) => x.length >= 25 && /^[A-Z0-9"“(]/.test(x));
  const ranked = (whole.length ? whole : usable).map((x, i) => {
    const p = plain(x); let sc = 0;
    for (const w of words) if (p.includes(' ' + stem(w))) sc += 2;
    for (const w of topicWords) if (p.includes(' ' + w)) sc += 1.5;
    if (item && p.includes(' ' + stem(item))) sc += 4;
    if (/\d/.test(x)) sc += 1;
    return { x, sc: sc - i * 0.3 };
  }).sort((a, b) => b.sc - a.sc);
  const listed = lines.map((l) => plain(l.replace(/^(Not allowed|Allowed): /, '')));
  const fresh = ranked.filter((r) => !listed.some((l) => plain(r.x).includes(l.trim()) || l.includes(plain(r.x).trim())));
  const take = item && lines.length ? fresh.slice(0, 1) : fresh.slice(0, 2);
  const keep = sents(text);
  take.sort((a, b) => keep.indexOf(a.x) - keep.indexOf(b.x)).forEach((r) => lines.push(r.x));
  return { text: lines.join(' '), sources: [source(id, key)] };
}

const ITEM_ALIASES = { 'water bottle': ['water bottle', 'bottle', 'water', 'beverage', 'beverages', 'drinks', 'liquid', 'hydration pack'], 'food': ['outside food', 'food'], 'drink': ['outside beverage', 'beverage', 'drink', 'liquid'], 'vape': ['vape', 'vaping', 'e cigarette', 'electronic cigarette'], 'camera': ['camera'],
  'fanny pack': ['fanny pack', 'belt bag', 'waist pack'], 'power bank': ['power bank', 'portable charger', 'battery pack'], 'chair': ['chair', 'lawn chair'],
  'camelbak': ['camelbak', 'hydration pack'], 'hydration pack': ['hydration pack', 'camelbak'], 'e cigarette': ['e cigarette', 'vape', 'electronic cigarette'] };
const BAG_ITEMS = /backpack|purse|clutch|tote|fanny pack|diaper bag|camera bag|wallet|hydration pack|camelbak|medical bag/;
// An item makes it a "can I bring this in" question only when the question is about bringing it.
function itemIn(q) {
  const w = ITEM_WORDS.find((x) => has(q, x) || has(q, x + 's'));
  if (!w) return null;
  if (BAG_ITEMS.test(w)) return w;
  return / (bring|take|carry|allowed|allow|permitted|have|sneak|bringing|carrying) /.test(q) ? w : null;
}
// "Can I bring X": the guide's own line about X, from whichever section has it.
function itemAnswer(id, item) {
  const rec = INFO[id] || {};
  const names = (ITEM_ALIASES[item] || [item]).map(stem);
  const hit = (txt) => { const p = plain(txt); return names.some((n) => p.includes(' ' + n)); };
  const order = ['bagPolicy', 'concessions', 'gates', 'accessibility', 'reEntry', 'parking', 'rideshare', 'ticketPickup'];
  for (const key of order) {
    const sec = rec[key]; if (!sec) continue;
    const no = (sec.prohibited || []).map(String).find(hit), yes = (sec.allowed || []).map(String).find(hit);
    const lines = [];
    if (yes) lines.push(`Allowed: ${yes.replace(/\.$/, '')}.`);
    if (no) lines.push(`Not allowed: ${no.replace(/\.$/, '')}.`);
    const listed = [yes, no].filter(Boolean).map((x) => plain(x));
    const said = sents(sectionText(sec)).filter((x) => !/^Policies may change|^Review the linked/i.test(x)).filter(hit)
      .filter((x) => !listed.some((l) => plain(x).includes(l) || l.includes(plain(x)))).slice(0, lines.length ? 1 : 2);
    lines.push(...said);
    if (lines.length) return { text: lines.join(' '), sources: [source(id, key)] };
  }
  const bag = rec.bagPolicy ? source(id, 'bagPolicy') : null;
  if (bag && /backpack|purse|clutch|tote|fanny pack|diaper bag|camera bag|wallet|hydration pack|camelbak/.test(item)) {
    const g = venueGuideAnswer(id, 'bagPolicy', ' ');
    if (g) return { text: `The guide doesn't list ${item}s by name. The bag rule: ${g.text}`, sources: g.sources };
  }
  return { text: `Concerto's ${venueName(id)} guide doesn't mention ${item}s. The venue's official page has the full list of what is allowed.`, sources: bag ? [bag] : [] };
}

function songMatch(q, songs) {
  let best = null;
  for (const s of songs) {
    const p = plain(s.replace(/\(.*?\)|\[.*?\]/g, '')).trim();
    if (p.length >= 3 && has(q, p) && (!best || p.length > best.p.length)) best = { s, p };
  }
  return best && best.s;
}
async function tourDates(t, event) {
  try {
    const now = new Date();
    const params = { keyword: t.artist, classificationName: 'Music', size: '100', sort: 'date,asc', startDateTime: now.toISOString().split('.')[0] + 'Z' };
    const r = await tmFetch('events', params, { event });
    if (r.status !== 200) return [];
    const want = plain(t.artist);
    const list = (JSON.parse(r.body)._embedded || {}).events || [];
    return list.filter((ev) => ((ev._embedded || {}).attractions || []).some((a) => plain(a.name) === want))
      .filter((ev) => !['cancelled', 'postponed'].includes(((ev.dates || {}).status || {}).code))
      .map((ev) => {
        const v = ((ev._embedded || {}).venues || [])[0] || {};
        return { date: (ev.dates.start || {}).localDate, time: (ev.dates.start || {}).localTime, tba: !!(ev.dates.start || {}).timeTBA,
          venue: v.name || '', city: [v.city && v.city.name, (v.state && v.state.stateCode) || (v.country && v.country.countryCode !== 'US' ? v.country.name : '')].filter(Boolean).join(', ') };
      });
  } catch (e) { return []; }
}
function clock(t) { if (!t) return ''; const [h, m] = t.split(':').map(Number); return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`; }

async function tourGuideAnswer(t, topic, q, event) {
  const s = SETS[t.tourId] || {};
  const songs = s.songs || [];
  const tourLink = { label: `${t.artist} · ${t.tourName}`, url: `/tour/${t.tourId}`, checked: '', official: '' };
  if (topic === 'setlist') {
    if (!songs.length) return { text: `There is no confirmed setlist for ${t.artist}'s ${t.tourName} yet. Concerto adds one when there is a reliable source, never a guess.`, sources: [tourLink] };
    const src = { label: `${t.artist} setlist`, url: `/setlist/${t.tourId}`, checked: pretty(s.updated), official: '' };
    const song = songMatch(q, songs);
    if (song) return { text: `Yes. "${song}" is song ${songs.indexOf(song) + 1} of ${songs.length} on the current setlist. Setlists change by night.`, sources: [src] };
    if (/ (play|perform)s? /.test(q) && !has(q, 'setlist') && !has(q, 'songs')) {
      return { text: `That song isn't on the current setlist (${songs.length} songs). Setlists change by night.`, sources: [src] };
    }
    return { text: `${songs.length} songs. It opens with "${songs[0]}" and ends with "${songs[songs.length - 1]}". Setlists change by night.`, sources: [src] };
  }
  if (topic === 'time' && / how long | length /.test(q)) {
    return { text: `Concerto doesn't have show lengths. ${songs.length ? `The current setlist has ${songs.length} songs.` : ''}`.trim(), sources: [songs.length ? { label: `${t.artist} setlist`, url: `/setlist/${t.tourId}`, checked: pretty(s.updated), official: '' } : tourLink] };
  }
  const dates = await tourDates(t, event);
  const cityHit = dates.filter((d) => d.city && has(q, plain(d.city.split(',')[0]).trim()));
  const pick = cityHit.length ? cityHit : dates;
  const datesLink = { ...tourLink, label: `${t.artist} tour dates`, url: `/tour/${t.tourId}#dates-h` };
  if (!pick.length) return { text: `Concerto doesn't see upcoming ${t.artist} dates on Ticketmaster right now.`, sources: [tourLink] };
  if (topic === 'time') {
    const d = pick[0];
    const when = d.tba ? 'The start time has not been announced yet.' : `Ticketmaster lists the show at ${clock(d.time)}, which is usually when the first act starts, not the headliner.`;
    return { text: `${t.artist} at ${d.venue}, ${d.city} on ${pretty(d.date)}: ${when} Set times are added when the venue posts them.`, sources: [datesLink] };
  }
  const shown = pick.slice(0, 3).map((d) => `${pretty(d.date)} at ${d.venue}, ${d.city}`);
  return { text: (cityHit.length ? '' : `Next ${shown.length === 1 ? 'date' : 'dates'}: `) + shown.join('; ') + '.' + (pick.length > 3 ? ` Plus ${pick.length - 3} more.` : ''), sources: [datesLink] };
}

async function venueUpcoming(id, event) {
  const v = VENUES.find((x) => x.id === id) || {};
  try {
    const params = { keyword: v.name, size: '20', sort: 'date,asc', classificationName: 'Music', startDateTime: new Date().toISOString().split('.')[0] + 'Z' };
    if (v.lat != null) { params.latlong = `${v.lat},${v.lng}`; params.radius = '2'; params.unit = 'miles'; }
    const r = await tmFetch('events', params, { event });
    if (r.status !== 200) return null;
    const want = plain(v.name);
    const list = ((JSON.parse(r.body)._embedded || {}).events || []).filter((ev) => {
      const got = plain((((ev._embedded || {}).venues || [])[0] || {}).name);
      return got && (got === want || got.startsWith(want) || want.startsWith(got));
    });
    return list.slice(0, 4).map((ev) => `${ev.name} on ${pretty((ev.dates.start || {}).localDate)}`);
  } catch (e) { return null; }
}

// ---------- places to eat and stay near the venue ----------
// Concerto Partners (paid restaurant and hotel listings for this venue) are suggested first,
// always labeled. Without a partner, the answer points to the Nearby rows in the app.
const HOTEL_Q = / (hotel|hotels|motel|stay|staying|stay over|place to stay|places to stay|where to stay|sleep|lodging|airbnb|room for the night) /;
const FOOD_Q = / (restaurant|restaurants|dinner|lunch|brunch|breakfast|eat before|eat after|eat near|eat nearby|eat around|eat close|where to eat|where should we eat|where should i eat|where can i eat|where can we eat|places to eat|place to eat|food near|food nearby|food around|good food|bar|bars|pregame|pre game|drinks before|drinks after|drinks near|drink before|grab a drink|grab a bite|bite to eat|happy hour|cocktails|pizza|tacos|sushi|steak|coffee) /;
function nearbyKind(qt) {
  if (HOTEL_Q.test(qt)) return 'hotel';
  if (FOOD_Q.test(qt) && !/ (inside|in the venue|in the arena|in the stadium|concession|concessions|stands|outside food|bring food|bring in) /.test(qt)) return 'restaurant';
  return null;
}
// What the client shows under the answer. The offer itself is for signed-in app users,
// the same as the gold star in the Nearby row.
function partnerOut(p, tier) {
  return { id: p.id, name: p.name, kind: p.kind, miles: p.miles, address: p.address, blurb: p.blurb, url: p.url,
    perk: p.perk ? (tier === 'anon' ? { locked: true } : { offer: p.perk.offer, details: p.perk.details, url: p.perk.url }) : null };
}
function nearbyAnswer(id, kind, list) {
  const row = kind === 'hotel' ? 'Nearby Hotels' : 'Nearby Restaurants';
  const where = venueName(id);
  const mine = list.filter((p) => p.kind === kind).slice(0, 2);
  const src = [{ label: `${where} venue guide`, url: `/venue/${id}`, checked: '', official: '' }];
  if (!mine.length) {
    return { text: `The ${where} page in the Concerto app has a ${row} row with places close to the venue.`, sources: src, partners: [] };
  }
  // The card under the answer carries the address, the Perk and Reserve, so the text stays short.
  const say = mine.map((p, i) => {
    const dist = p.miles != null ? (p.miles < 0.1 ? `steps from ${where}` : `${p.miles} ${p.miles === 1 ? 'mile' : 'miles'} from ${where}`) : `near ${where}`;
    return i === 0 ? `${p.name}, a Concerto Partner, is ${dist}.` : `${p.name}, also a Concerto Partner, is ${dist}.`;
  });
  return { text: say.join(' ') + ` More ${kind === 'hotel' ? 'hotels' : 'places to eat'} nearby are in the ${row} row in the Concerto app.`, sources: src, partners: mine };
}

// ---------- limits and cache ----------
let blobs = null;
function blobStore(event) {
  if (blobs !== null) return blobs;
  try {
    const b = require('@netlify/blobs');
    if (event && b.connectLambda) b.connectLambda(event);
    blobs = b.getStore('concerto-ask');
  } catch (e) { blobs = false; }
  return blobs;
}
async function readJSON(s, k) { try { return (await s.get(k, { type: 'json' })) || null; } catch (e) { return undefined; } }
async function bump(s, k, by = 1) { const cur = (await readJSON(s, k)) || { n: 0 }; await s.setJSON(k, { n: (cur.n || 0) + by }); }

async function tierFor(event) {
  const auth = (event.headers || {}).authorization || (event.headers || {}).Authorization || '';
  const token = auth.replace(/^Bearer\s+/i, '').trim();
  if (!token) return 'anon';
  try {
    const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const { data: { user } } = await sb.auth.getUser(token);
    if (!user) return 'anon';
    const { data: p } = await sb.from('profiles').select('is_premium').eq('id', user.id).single();
    if (p && p.is_premium) return 'plus';
    // A Show Pass unlocks everything for one show, Concerto AI included. The table is written
    // only by the RevenueCat webhook; if it doesn't exist yet this simply finds nothing.
    try {
      const { data: pass } = await sb.from('show_passes').select('until').eq('user_id', user.id)
        .gt('until', new Date().toISOString()).limit(1);
      if (pass && pass.length) return 'plus';
    } catch (e) { /* no pass table yet */ }
    return 'member';
  } catch (e) { return 'anon'; }
}

async function allowAI(event, tier) {
  const s = blobStore(event);
  if (!s || !process.env.ANTHROPIC_API_KEY) return { ok: false, reason: 'off' };
  const day = new Date().toISOString().slice(0, 10), month = day.slice(0, 7);
  const ip = (event.headers || {})['x-nf-client-connection-ip'] || String((event.headers || {})['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
  const who = `visitor/${day}/${sha(day + ip + (process.env.ASK_SALT || 'concerto'))}`;
  const [g, m, v] = await Promise.all([readJSON(s, `global/${day}`), readJSON(s, `month/${month}`), readJSON(s, who)]);
  if (g === undefined || m === undefined || v === undefined) return { ok: false, reason: 'off' };   // fail closed
  if ((g && g.n) >= DAILY_CAP || (m && m.n) >= MONTHLY_CAP) return { ok: false, reason: 'site' };
  const used = (v && v.n) || 0;
  if (used >= LIMITS[tier]) return { ok: false, reason: 'visitor', used };
  return { ok: true, used, keys: [`global/${day}`, `month/${month}`, who], store: s };
}

function contextFor(venueId, tour, dates, partners) {
  const out = [];
  if (venueId) {
    const rec = INFO[venueId] || {};
    out.push(`VENUE: ${venueName(venueId)} (${[rec.city, rec.state].filter(Boolean).join(', ')})`);
    for (const k of Object.keys(SECTION_LABEL)) {
      const s = rec[k]; if (!s) continue;
      const lines = [sectionText(s)];
      if ((s.allowed || []).length) lines.push('Allowed: ' + s.allowed.join('; '));
      if ((s.prohibited || []).length) lines.push('Not allowed: ' + s.prohibited.join('; '));
      out.push(`[${k}] ${SECTION_LABEL[k]} (checked ${pretty(s.verified) || 'date unknown'}): ${lines.join(' ')}`);
    }
    if (partners && partners.length) {
      out.push('[partners] Concerto Partners near this venue: ' + partners.map((p) => `${p.name} (${p.kind}${p.miles != null ? ', ' + p.miles + ' mi' : ''})${p.blurb ? ': ' + p.blurb : ''}${p.perk ? ' Has a Concerto Perk in the app.' : ''}`).join(' | '));
    }
  }
  if (tour) {
    const s = SETS[tour.tourId] || {};
    out.push(`TOUR: ${tour.artist}, ${tour.tourName}`);
    if ((s.songs || []).length) out.push(`[setlist] ${s.songs.length} songs (${s.note || 'source not stated'}): ${s.songs.map((x, i) => `${i + 1}. ${x}`).join(' | ')}`);
    if (dates && dates.length) out.push(`[dates] ` + dates.slice(0, 25).map((d) => `${d.date} ${d.venue}, ${d.city}${d.time && !d.tba ? ' show ' + clock(d.time) : ''}`).join(' | '));
  }
  return out.join('\n');
}

const SYSTEM = `You are Concerto, a concert companion. Answer the fan's question using ONLY the CONTEXT, which is Concerto's researched venue guide and tour data.
Rules:
- If the CONTEXT does not answer the question, say "Concerto's guide doesn't cover that yet." and suggest checking the venue's official page or the event page. Never use outside knowledge, never guess times, prices, sizes, or rules.
- Keep the exact sizes, times and wording of rules from the CONTEXT. If a rule is for sports events or varies by event, say so.
- If the CONTEXT has [partners] and the question is about eating, drinking, staying over, or planning the night around the show, name the partner first and call it a Concerto Partner. Mention its Perk only as "a Concerto Perk in the app". Never name other restaurants or hotels.
- Be direct and plain: answer first, in at most 60 words. No greetings, no exclamation marks, no em dashes.
Return only JSON: {"answer": "...", "sections": ["bagPolicy", ...]} where sections lists the CONTEXT keys you used (bagPolicy, gates, parking, rideshare, accessibility, concessions, reEntry, ticketPickup, setlist, dates, partners).`;

async function aiAnswer(question, venueId, tour, dates, partners) {
  const ctx = contextFor(venueId, tour, dates, partners);
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': process.env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({ model: MODEL, max_tokens: 300, system: SYSTEM, messages: [{ role: 'user', content: `CONTEXT:\n${ctx}\n\nQUESTION: ${question}` }] }),
  });
  if (!r.ok) throw new Error('model ' + r.status);
  const data = await r.json();
  const raw = ((data.content || [])[0] || {}).text || '';
  const m = raw.match(/\{[\s\S]*\}/);
  const parsed = JSON.parse(m ? m[0] : raw);
  const answer = String(parsed.answer || '').replace(/\s*[—–]\s*/g, ', ').trim();
  if (!answer) throw new Error('empty');
  const secs = (parsed.sections || []).filter((k) => SECTION_LABEL[k] || k === 'setlist' || k === 'dates');
  const sources = [];
  for (const k of secs) {
    if (SECTION_LABEL[k] && venueId) sources.push(source(venueId, k));
    if (k === 'setlist' && tour) sources.push({ label: `${tour.artist} setlist`, url: `/setlist/${tour.tourId}`, checked: pretty((SETS[tour.tourId] || {}).updated), official: '' });
    if (k === 'dates' && tour) sources.push({ label: `${tour.artist} tour dates`, url: `/tour/${tour.tourId}#dates-h`, checked: '', official: '' });
  }
  const usedPartners = secs.includes('partners') && partners && partners.length ? partners.filter((p) => answer.includes(p.name)) : [];
  if (!sources.length) sources.push(venueId ? { label: `${venueName(venueId)} venue guide`, url: `/venue/${venueId}`, checked: '', official: '' } : { label: `${tour.artist} · ${tour.tourName}`, url: `/tour/${tour.tourId}`, checked: '', official: '' });
  return { text: answer, sources, partners: usedPartners };
}

// ---------- handler ----------
exports.handler = async (event) => {
  const methods = 'GET, POST, OPTIONS';
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: corsHeaders(event, methods), body: '' };
  if (!originOf(event).ok) return refuse(event, 403, 'Forbidden', methods);
  if (limited(event, 30, 60000)) return refuse(event, 429, 'Too many questions at once. Try again in a minute.', methods);

  let body = {};
  try { body = event.httpMethod === 'POST' ? JSON.parse(event.body || '{}') : (event.queryStringParameters || {}); } catch (e) { body = {}; }
  const question = String(body.q || '').slice(0, 200).trim();
  const headers = { ...corsHeaders(event, methods), 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
  // Every question is logged anonymously (no account, no IP, no device id): the words, what it was
  // about, and how it was answered. It shows what fans actually want to know. Demo traffic is skipped.
  const reply = async (o) => {
    if (!body.demo) await logQuestion(event, question, o, body).catch(() => {});
    return { statusCode: 200, headers, body: JSON.stringify(o) };
  };
  if (question.length < 3) return reply({ mode: 'none', text: 'Ask about a venue or a tour, like "Can I bring a backpack to Madison Square Garden?"', sources: [] });

  const q = plain(question);
  const venueId = findVenue(q, body.venue);
  const tourId = findTour(q, body.tour);
  const tour = tourId ? TOURS.find((t) => t.tourId === tourId) : null;
  // Topics are read with the names taken out, so "Fenway Park" is not a parking question.
  let qt = q;
  for (const k of venueKeys) if (k.id === venueId && has(qt, k.key)) qt = qt.replace(' ' + k.key + ' ', ' ');
  if (tour) qt = qt.replace(plain(tour.artist), ' ');
  const item = venueId ? itemIn(qt) : null;
  const vTopics = topicsIn(qt, TOPICS);
  if (item && !vTopics.includes('bagPolicy')) vTopics.unshift('bagPolicy');
  if (/ (policy|policies|rules|allowed|allow|permitted) /.test(qt) && !vTopics.length) vTopics.push('bagPolicy');
  const tTopics = topicsIn(qt, TOUR_TOPICS);
  // Demo partners for showing prospects (private: demo key or a demo account).
  const demo = venueId && body.demo ? await demoAllowed(body.demo, event.headers) : false;
  const partnersFor = async (id) => {
    const venue = VENUES.find((v) => v.id === id);
    const [real, fake] = await Promise.all([venuePartners(id, venue), demo ? demoVenuePartners(id, venue) : []]);
    return fake.concat(real);
  };
  const entity = { venue: venueId ? { slug: venueId, name: venueName(venueId) } : null, tour: tour ? { slug: tour.tourId, artist: tour.artist, name: tour.tourName } : null };

  if (!venueId && !tour) {
    if (/ (setlist|set list|songs|tour|tour dates) /.test(q)) return reply({ mode: 'none', entity, text: "Concerto doesn't have that tour yet. Try another artist, or browse the tours Concerto covers.", sources: [{ label: 'All tours', url: '/tours', checked: '', official: '' }] });
    return reply({ mode: 'none', entity, text: "Concerto couldn't tell which venue or tour you mean. Try including the venue or artist name, like \"parking at Kia Forum\" or \"Noah Kahan setlist\".", sources: [{ label: 'All venues', url: '/venues', checked: '', official: '' }] });
  }
  // "Is there a bag check?": a place to leave a bag, from any section that mentions one.
  if (venueId && / (bag check|coat check|check my bag|check a bag|locker|lockers|storage|store my|cloakroom|bag drop) /.test(qt)) {
    const rec = INFO[venueId] || {};
    for (const key of ['bagPolicy', 'gates', 'ticketPickup', 'accessibility']) {
      const hits = sents(sectionText(rec[key])).filter((x) => /bag check|coat check|check(ed)? (your |a )?bags?|lockers?|storage|stored|cloakroom|bag drop|item[- ]check|left luggage|binbox/i.test(x)).slice(0, 2);
      if (hits.length) return reply({ mode: 'guide', entity, text: hits.join(' '), sources: [source(venueId, key)] });
    }
    return reply({ mode: 'guide', entity, text: `Concerto's ${venueName(venueId)} guide doesn't mention a bag check or lockers. Plan to bring only what the bag rule allows.`, sources: rec.bagPolicy ? [source(venueId, 'bagPolicy')] : [] });
  }
  // Free, specific answers that need no guide section.
  if (venueId && !tour && / (who is playing|whos playing|who plays|what shows|shows at|upcoming|this weekend|tonight|next show|events at|concerts at|lineup) /.test(qt)) {
    const list = await venueUpcoming(venueId, event);
    const link = { label: `Upcoming shows at ${venueName(venueId)}`, url: `/venue/${venueId}#up-h`, checked: '', official: '' };
    if (list && list.length) return reply({ mode: 'guide', entity, text: `Next at ${venueName(venueId)}: ${list.join('; ')}.`, sources: [link] });
    return reply({ mode: 'guide', entity, text: `Concerto doesn't see upcoming music shows at ${venueName(venueId)} on Ticketmaster right now.`, sources: [link] });
  }
  if (/ (weather|forecast|rain|cold|hot|temperature) /.test(qt)) {
    return reply({ mode: 'guide', entity, text: 'Concerto shows the show-day forecast seven days out, on the venue page and in Your Night in the app.', sources: venueId ? [{ label: `${venueName(venueId)} venue guide`, url: `/venue/${venueId}`, checked: '', official: '' }] : [] });
  }

  // Where to eat, drink or stay near the venue: Concerto Partners first. Free, no AI.
  const nk = venueId ? nearbyKind(qt) : null;
  if (nk) {
    const [list, tierN] = await Promise.all([partnersFor(venueId), tierFor(event)]);
    const a = nearbyAnswer(venueId, nk, list);
    return reply({ mode: 'guide', entity, text: a.text, sources: a.sources, partners: a.partners.map((p) => partnerOut(p, tierN)) });
  }

  // Questions a quote can answer well: one clear topic, no sizes to compare, no open-ended ask.
  const needsReasoning = /\d+\s*(x|by|inch|in|cm)\b|\d+\s*(x|by)\s*\d+/.test(question) || /\b(should i|best way|tips|what do i need to know|what should|recommend|worth|vs|or should|explain)\b/i.test(question);
  let guide = null;
  if (venueId && item && !needsReasoning) {
    guide = itemAnswer(venueId, item);
  } else if (venueId && vTopics.length && !needsReasoning && !(tour && tTopics.length && !vTopics.includes('bagPolicy'))) {
    guide = venueGuideAnswer(venueId, vTopics[0], q);
  } else if (tour && (tTopics.length || !venueId) && !needsReasoning) {
    guide = await tourGuideAnswer(tour, tourTopic(qt, tour), q, event);
  }
  if (guide && guide.text) return reply({ mode: 'guide', entity, ...guide });

  // Reasoning needed: AI within the caps, otherwise the best guide answer we can give.
  const tier = await tierFor(event);
  const fallback = () => {
    if (venueId) {
      const key = vTopics[0] || 'bagPolicy';
      const g = venueGuideAnswer(venueId, key, q);
      if (g) return g;
    }
    return { text: `Open the ${venueId ? venueName(venueId) + ' venue guide' : tour.artist + ' tour page'} for the full details.`, sources: [venueId ? { label: `${venueName(venueId)} venue guide`, url: `/venue/${venueId}`, checked: '', official: '' } : { label: `${tour.artist} · ${tour.tourName}`, url: `/tour/${tour.tourId}`, checked: '', official: '' }] };
  };
  const partners = venueId ? await partnersFor(venueId) : [];
  // A new partner changes the answer, so the partner list is part of the cache key.
  const cacheKey = `cache/${sha(q + '|' + (venueId || '') + '|' + (tourId || '') + '|' + partners.map((p) => p.id).sort().join(','))}`;
  const s = blobStore(event);
  if (s) {
    const hit = await readJSON(s, cacheKey);
    if (hit && hit.t && Date.now() - hit.t < CACHE_DAYS * 86400000) {
      const named = partners.filter((p) => (hit.partnerIds || []).includes(p.id)).map((p) => partnerOut(p, tier));
      return reply({ mode: 'ai', entity, text: hit.text, sources: hit.sources, partners: named, cached: true });
    }
  }
  const gate = await allowAI(event, tier);
  if (!gate.ok) {
    const note = gate.reason === 'visitor'
      ? (tier === 'plus' ? "You've used today's Concerto AI answers. Here is what the guide says." : `You've used today's ${LIMITS[tier]} Concerto AI answers. Concerto+ members get ${LIMITS.plus} a day. Here is what the guide says.`)
      : 'Here is what the guide says.';
    return reply({ mode: 'guide', entity, limited: gate.reason, note, tier, ...fallback() });
  }
  try {
    const dates = tour ? await tourDates(tour, event) : [];
    const a = await aiAnswer(question, venueId, tour, dates, partners);
    await Promise.all(gate.keys.map((k) => bump(gate.store, k))).catch(() => {});
    await gate.store.setJSON(cacheKey, { t: Date.now(), text: a.text, sources: a.sources, partnerIds: a.partners.map((p) => p.id) }).catch(() => {});
    return reply({ mode: 'ai', entity, text: a.text, sources: a.sources, partners: a.partners.map((p) => partnerOut(p, tier)), remaining: Math.max(0, LIMITS[tier] - gate.used - 1), tier });
  } catch (e) {
    console.error('ask: model failed', e && e.message);
    return reply({ mode: 'guide', entity, ...fallback() });
  }
};

async function logQuestion(event, question, o, body) {
  if (!question || question.length < 3 || !process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) return;
  const origin = String((event.headers || {}).origin || (event.headers || {}).Origin || '');
  const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  const e = o.entity || {};
  const insert = sb.from('ai_questions').insert({
    question: question.slice(0, 200),
    venue_slug: (e.venue && e.venue.slug) || null,
    tour_slug: (e.tour && e.tour.slug) || null,
    mode: o.mode || null,
    limited: o.limited || null,
    surface: /concertocity\.com/.test(origin) ? 'web' : 'app',
  });
  // Never let logging slow an answer down by more than a moment.
  await Promise.race([insert, new Promise((r) => setTimeout(r, 800))]);
}

// Exposed for tests (scripts/test-ask.js).
exports._test = { plain, findVenue, findTour, topicsIn, TOPICS, TOUR_TOPICS, venueGuideAnswer, tourGuideAnswer, contextFor, SYSTEM, nearbyKind, nearbyAnswer, partnerOut };
