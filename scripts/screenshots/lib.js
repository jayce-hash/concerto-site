// Shared set-up for the website screenshots: the real app (web build), real listings typed in by
// hand, and Concerto's own illustrations in place of every Ticketmaster and Google photo.
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const HERE = __dirname;
const ART = (n) => fs.readFileSync(path.join(HERE, n + '.jpg'));
const BASE = 'http://localhost:8791';

const img = (n) => [{ url: `${BASE}/__art/${n}.jpg`, width: 1024, height: 576, ratio: '16_9' }];
const pick = (s, set) => set[[...String(s)].reduce((a, c) => a + c.charCodeAt(0), 0) % set.length];
const A = ['artist', 'artist2', 'artist3'], V = ['venue', 'venue2', 'venue3'];

// Olivia Rodrigo, The Unraveled Tour: dates as announced by Live Nation. Only the day is used
// where no start time is known.
const OR = [
  ['2026-11-19', 'Amerant Bank Arena', 'Sunrise', 'FL', 'America/New_York'], ['2026-11-20', 'Amerant Bank Arena', 'Sunrise', 'FL', 'America/New_York'],
  ['2026-11-23', 'Bridgestone Arena', 'Nashville', 'TN', 'America/Chicago'], ['2026-11-24', 'Bridgestone Arena', 'Nashville', 'TN', 'America/Chicago'],
  ['2026-12-01', 'Rogers Arena', 'Vancouver', 'BC', 'America/Vancouver', 'CA'], ['2026-12-02', 'Rogers Arena', 'Vancouver', 'BC', 'America/Vancouver', 'CA'],
  ['2026-12-07', 'Climate Pledge Arena', 'Seattle', 'WA', 'America/Los_Angeles'], ['2026-12-08', 'Climate Pledge Arena', 'Seattle', 'WA', 'America/Los_Angeles'],
  ['2026-12-11', 'Oakland Arena', 'Oakland', 'CA', 'America/Los_Angeles'], ['2026-12-12', 'Oakland Arena', 'Oakland', 'CA', 'America/Los_Angeles'],
  ['2026-12-15', 'Golden 1 Center', 'Sacramento', 'CA', 'America/Los_Angeles'], ['2026-12-16', 'Golden 1 Center', 'Sacramento', 'CA', 'America/Los_Angeles'],
  ['2026-12-19', 'T-Mobile Arena', 'Las Vegas', 'NV', 'America/Los_Angeles'], ['2026-12-20', 'T-Mobile Arena', 'Las Vegas', 'NV', 'America/Los_Angeles'],
  ['2027-01-12', 'Intuit Dome', 'Inglewood', 'CA', 'America/Los_Angeles'], ['2027-01-13', 'Intuit Dome', 'Inglewood', 'CA', 'America/Los_Angeles'],
  ['2027-01-16', 'Intuit Dome', 'Inglewood', 'CA', 'America/Los_Angeles'], ['2027-01-17', 'Intuit Dome', 'Inglewood', 'CA', 'America/Los_Angeles'],
  ['2027-02-11', 'Barclays Center', 'Brooklyn', 'NY', 'America/New_York'], ['2027-02-12', 'Barclays Center', 'Brooklyn', 'NY', 'America/New_York'],
  ['2027-02-15', 'Barclays Center', 'Brooklyn', 'NY', 'America/New_York'], ['2027-02-16', 'Barclays Center', 'Brooklyn', 'NY', 'America/New_York'],
];
// Los Angeles, week of Nov 16, 2026: from a public concert calendar. No start times were listed.
const LA = [
  ['2026-11-16', 'Natanya', 'El Rey Theatre', 'Los Angeles'], ['2026-11-16', 'The Aces', 'Pacific Electric', 'Los Angeles'], ['2026-11-16', 'The Don Brown Collective', 'Blue Note Los Angeles', 'Los Angeles'],
  ['2026-11-17', 'The Damned', 'The Wiltern', 'Los Angeles'], ['2026-11-17', 'Margaret Glaspy', 'Troubadour', 'West Hollywood'], ['2026-11-17', 'Weston Estate', 'The Roxy Theatre', 'West Hollywood'],
  ['2026-11-18', 'Teddy Swims', 'Kia Forum', 'Inglewood'], ['2026-11-18', 'Jonas Brothers', 'Hollywood Bowl', 'Los Angeles'], ['2026-11-18', 'Manic Street Preachers', 'The Wiltern', 'Los Angeles'],
  ['2026-11-19', 'Em Beihold', 'Teragram Ballroom', 'Los Angeles'], ['2026-11-19', 'Jackson Browne', 'Hollywood Pantages Theatre', 'Los Angeles'], ['2026-11-19', 'The Amity Affliction', 'The Novo', 'Los Angeles'],
  ['2026-11-20', 'Rhye', 'Hollywood Palladium', 'Los Angeles'], ['2026-11-20', 'Houndmouth', 'The Wiltern', 'Los Angeles'], ['2026-11-20', 'BoyNextDoor', 'Peacock Theater', 'Los Angeles'],
  ['2026-11-21', 'Katseye', 'Crypto.com Arena', 'Los Angeles'], ['2026-11-21', 'Steve Lacy', 'Hollywood Bowl', 'Los Angeles'], ['2026-11-21', 'Maddie Zahm', 'Pacific Electric', 'Los Angeles'],
  ['2026-11-22', 'Three Days Grace', 'Intuit Dome', 'Inglewood'], ['2026-11-22', 'Katseye', 'Crypto.com Arena', 'Los Angeles'], ['2026-11-22', 'Silverstein & Story Of The Year', 'The Wiltern', 'Los Angeles'],
];
const ev = (id, name, date, venue, city, st, tz, acts, time, cc) => ({
  id, name, url: 'https://concertocity.com', images: img(pick(acts[0], A)),
  dates: { start: time ? { localDate: date, localTime: time, dateTime: new Date(`${date}T${time}-08:00`).toISOString() } : { localDate: date, timeTBA: true, noSpecificTime: true }, timezone: tz, status: { code: 'onsale' } },
  _embedded: { venues: [{ name: venue, city: { name: city }, state: { stateCode: st }, country: { countryCode: cc || 'US' } }], attractions: acts.map((n) => ({ name: n, images: img(pick(n, A)) })) },
});
const orEvents = () => OR.map((r, i) => ev('or' + i, 'Olivia Rodrigo: The Unraveled Tour', r[0], r[1], r[2], r[3], r[4], ['Olivia Rodrigo', 'Devon Again'], r[1] === 'Intuit Dome' && r[0] === '2027-01-12' ? '19:00:00' : null, r[5]));
const laEvents = () => LA.map((r, i) => ev('la' + i, r[1], r[0], r[2], r[3], 'CA', 'America/Los_Angeles', r[1].split(' & ')));
const wrap = (events) => JSON.stringify({ _embedded: { events }, page: { totalPages: 1, totalElements: events.length } });

async function routes(ctx) {
  await ctx.route('**/__art/*.jpg', (r) => r.fulfill({ contentType: 'image/jpeg', body: ART(path.basename(new URL(r.request().url()).pathname, '.jpg')) }));
  await ctx.route('**/.netlify/functions/tm/**', (r) => {
    const u = new URL(r.request().url()); const kw = u.searchParams.get('keyword') || '';
    const send = (body) => r.fulfill({ contentType: 'application/json', headers: { 'Access-Control-Allow-Origin': '*' }, body });
    if (u.pathname.endsWith('attractions.json')) return send(JSON.stringify({ _embedded: { attractions: [{ name: kw, images: img(pick(kw, A)) }] } }));
    if (u.pathname.endsWith('venues.json')) return send(JSON.stringify({ _embedded: { venues: [{ name: kw, images: img(pick(kw, V)) }] } }));
    if (/olivia rodrigo/i.test(kw)) return send(wrap(orEvents()));
    if (u.searchParams.get('latlong')) return send(wrap(laEvents()));
    if (kw) return send(wrap([{ id: 'k', name: kw, images: img(pick(kw, A)), _embedded: { attractions: [{ name: kw, images: img(pick(kw, A)) }] } }]));
    return send(wrap(laEvents()));
  });
  await ctx.route('**/.netlify/functions/venue-photo**', (r) => {
    const n = new URL(r.request().url()).searchParams.get('name') || '';
    r.fulfill({ contentType: 'application/json', body: JSON.stringify({ src: `${BASE}/__art/${n === 'Intuit Dome' ? 'venue' : pick(n, V)}.jpg`, credit: '' }) });
  });
  // Anything else that would be someone else's photo becomes an illustration too.
  await ctx.route(/ticketm\.net|googleusercontent|maps\.googleapis|wikimedia/, (r) => r.fulfill({ contentType: 'image/jpeg', body: ART('artist') }));
}

const SHOW = { id: 'or14', name: 'Olivia Rodrigo: The Unraveled Tour', venueName: 'Intuit Dome', venueCity: 'Inglewood, CA', venueSlug: 'intuit-dome', date: '2027-01-13T03:00:00.000Z', doors: '7:00 PM', timezone: 'America/Los_Angeles', lineup: ['Olivia Rodrigo', 'Devon Again'], image: `${BASE}/__art/artist.jpg` };

async function open({ night, plus } = {}) {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 402, height: 815 }, deviceScaleFactor: 3, geolocation: { latitude: 34.0522, longitude: -118.2437 }, permissions: ['geolocation'], timezoneId: 'America/Los_Angeles', locale: 'en-US' });
  await routes(ctx);
  const rec = night ? { ...night, ...(plus ? { showPassUntil: '2027-01-14T20:00:00.000Z' } : {}) } : (plus ? { showPassUntil: '2027-01-14T20:00:00.000Z' } : null);
  await ctx.addInitScript(({ show, rec }) => {
    if (localStorage.getItem('cap')) return; localStorage.setItem('cap', '1');
    localStorage.setItem('concerto.myShows.v1', JSON.stringify([show]));
    for (const k of ['concerto.welcome.done.v1', 'concerto.welcome.dismissed.v1', 'concerto.tour.v1']) localStorage.setItem(k, '1');
    localStorage.setItem('concerto.place.v1', JSON.stringify({ name: 'Los Angeles, CA', lat: 34.0522, lng: -118.2437 }));
    if (rec) localStorage.setItem('concerto.night.v1', JSON.stringify({ [show.id]: rec }));
  }, { show: SHOW, rec });
  const p = await ctx.newPage(); const errs = [];
  p.on('pageerror', (e) => { if (!/#418|#423|#425/.test(String(e))) errs.push(String(e).slice(0, 200)); });
  return { b, ctx, p, errs };
}
const scrollMain = (p, y) => p.evaluate((y) => { const els = [...document.querySelectorAll('*')].filter((e) => e.scrollHeight > e.clientHeight + 40 && getComputedStyle(e).overflowY !== 'visible'); const el = els.sort((a, b) => b.scrollHeight - a.scrollHeight)[0]; if (el) el.scrollTop = y; }, y);
const tap = async (p, text, opt = {}) => { try { const l = p.getByText(text, { exact: opt.exact ?? true }).locator('visible=true'); await (opt.last ? l.last() : l.first()).click({ timeout: 4000 }); return true; } catch { console.log('MISS', text); return false; } };
module.exports = { open, BASE, SHOW, scrollMain, tap, HERE };
// The web build adds a site header the phone app does not have; captures leave it out.
module.exports.clean = (p) => p.evaluate(() => { for (const e of document.querySelectorAll('div')) { const r = e.getBoundingClientRect(); if (getComputedStyle(e).position === 'sticky' && r.top <= 0 && r.height > 50 && r.height < 80 && r.width > 380) e.style.display = 'none'; } });
