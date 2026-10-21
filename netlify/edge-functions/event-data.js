// Event structured data for tour and venue pages.
//
// Tour dates and upcoming shows are drawn in the browser by js/public-v6.js, so Google's first
// read of the page sees an empty list. This adds the same dates as schema.org MusicEvent data
// to the page itself, which is what lets Google show them as events in search.
//
// It asks the site's own Ticketmaster proxy with exactly the parameters the page script uses,
// so both share one cached answer (netlify/functions/lib/tm-cache.js) and it costs almost no
// extra Ticketmaster calls. The finished page is cached at the edge for an hour.
//
// Fails open: any error, a slow answer, or no dates, and the page goes out exactly as built.

const TIMEOUT_MS = 2500;
const MAX_TOUR = 25;
const MAX_VENUE = 8;

const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/^the\s+/, '').replace(/[^a-z0-9]/g, '');
const realEvent = (ev) => { const c = ev?.dates?.status?.code; return c !== 'cancelled' && c !== 'postponed'; };
const isoSec = (d) => d.toISOString().split('.')[0] + 'Z';
const attr = (html, name) => {
  const m = html.match(new RegExp(name + '="([^"]*)"'));
  return m ? m[1].replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#x27;|&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>') : '';
};

async function tmEvents(origin, params) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(`${origin}/.netlify/functions/tm/events.json?${params}`, { signal: ctl.signal, headers: { Referer: origin + '/' } });
    if (!r.ok) return [];
    const d = await r.json();
    return d?._embedded?.events || [];
  } catch { return []; } finally { clearTimeout(t); }
}

function bestImage(ev) {
  const imgs = (ev.images || []).filter((i) => i.url && /^https:/.test(i.url));
  imgs.sort((a, b) => (b.ratio === '16_9') - (a.ratio === '16_9') || (b.width || 0) - (a.width || 0));
  return imgs[0]?.url;
}

function toSchema(ev, pageUrl) {
  const v = ev._embedded?.venues?.[0] || {};
  const s = ev.dates?.start || {};
  const startDate = s.dateTime || (s.localDate ? s.localDate + (s.localTime ? 'T' + s.localTime : '') : null);
  if (!startDate || !v.name) return null;
  const performers = (ev._embedded?.attractions || []).filter((a) => a.name).map((a) => ({ '@type': 'MusicGroup', name: a.name }));
  const address = {
    '@type': 'PostalAddress',
    streetAddress: v.address?.line1, addressLocality: v.city?.name, addressRegion: v.state?.stateCode,
    postalCode: v.postalCode, addressCountry: v.country?.countryCode,
  };
  Object.keys(address).forEach((k) => address[k] === undefined && delete address[k]);
  const out = {
    '@context': 'https://schema.org', '@type': 'MusicEvent', name: ev.name, startDate,
    // Google requires previousStartDate with EventRescheduled, and Ticketmaster never gives the
    // old date. startDate is already the new date, so Scheduled is accurate.
    eventStatus: 'https://schema.org/EventScheduled',
    eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
    location: { '@type': 'Place', name: v.name, address },
    url: pageUrl,
  };
  if (performers.length) out.performer = performers;
  // Ticketmaster has no end time. Matching the start (rather than guessing a time, or a local
  // date that can fall before a UTC start) keeps the field honest and never ends before it begins.
  out.endDate = startDate;
  const who = performers.map((p) => p.name).slice(0, 3).join(', ') || ev.name;
  const where = [v.name, v.city?.name].filter(Boolean).join(', ');
  out.description = `${who} at ${where}. Plan the night with Concerto: the venue guide, the setlist, and places to eat and stay nearby.`;
  const img = bestImage(ev); if (img) out.image = [img];
  if (ev.url && /^https:\/\//.test(ev.url)) {
    const offer = { '@type': 'Offer', url: ev.url };
    const pr = (ev.priceRanges || []).find((r) => typeof r.min === 'number');
    if (pr) { offer.price = pr.min; offer.priceCurrency = pr.currency || 'USD'; }
    const code = ev.dates?.status?.code;
    offer.availability = code === 'offsale' ? 'https://schema.org/SoldOut' : 'https://schema.org/InStock';
    const from = ev.sales?.public?.startDateTime;
    if (from) offer.validFrom = from;
    out.offers = offer;
  }
  return out;
}

function dedupe(list) {
  const seen = new Set();
  return list.filter((ev) => {
    const k = (ev._embedded?.venues?.[0]?.name || '') + (ev.dates?.start?.localDate || '') + ev.name;
    if (seen.has(k)) return false; seen.add(k); return true;
  });
}

async function eventsForTour(html, origin) {
  const tag = (html.match(/<section[^>]*data-tour-dates[^>]*>/) || [])[0] || '';
  const artist = attr(tag, 'data-tour-artist');
  if (!artist) return [];
  // Shows that aren't concerts search by their own name, in every category, matching the start of the billing.
  const keyword = attr(tag, 'data-tour-keyword') || artist;
  const prefix = attr(tag, 'data-tour-match') === 'prefix';
  // Same query as tourDates() in js/public-v6.js, so the two share a cache entry.
  const now = new Date(), end = new Date(now.getTime() + 400 * 86400000);
  const p = new URLSearchParams({ keyword, classificationName: 'Music', size: '100', sort: 'date,asc', startDateTime: isoSec(now), endDateTime: isoSec(end) });
  if (/\sdata-tour-any[\s>=]/.test(tag)) p.delete('classificationName');
  const want = norm(prefix ? keyword : artist);
  const list = (await tmEvents(origin, p)).filter(realEvent)
    .filter((ev) => (ev._embedded?.attractions || []).some((a) => (prefix ? norm(a.name).startsWith(want) : norm(a.name) === want)));
  return dedupe(list).slice(0, MAX_TOUR);
}

async function eventsForVenue(html, origin) {
  const tag = (html.match(/<div[^>]*data-venue-tonight[^>]*>/) || [])[0];
  if (!tag) return [];
  const name = attr(tag, 'data-name'), country = attr(tag, 'data-country'), lat = attr(tag, 'data-lat'), lng = attr(tag, 'data-lng');
  if (!name) return [];
  // Same query as venueUpcoming() in js/public-v6.js.
  const p = new URLSearchParams({ keyword: name, size: '20', sort: 'date,asc', classificationName: 'Music', startDateTime: isoSec(new Date()) });
  if (country) p.set('countryCode', country);
  if (lat && lng) { p.set('latlong', lat + ',' + lng); p.set('radius', '2'); p.set('unit', 'miles'); }
  const want = norm(name);
  const list = (await tmEvents(origin, p)).filter(realEvent).filter((ev) => {
    const got = norm(ev._embedded?.venues?.[0]?.name);
    return got && (got === want || got.startsWith(want) || want.startsWith(got));
  });
  return dedupe(list).slice(0, MAX_VENUE);
}

export default async (request, context) => {
  const res = await context.next();
  try {
    if (request.method !== 'GET' || res.status !== 200 || !(res.headers.get('content-type') || '').includes('text/html')) return res;
    const html = await res.clone().text();
    if (html.includes('data-event-schema')) return res;
    const url = new URL(request.url);
    const isTour = url.pathname.startsWith('/tour/');
    const events = isTour ? await eventsForTour(html, url.origin) : await eventsForVenue(html, url.origin);
    const pageUrl = `https://concertocity.com${url.pathname.replace(/\.html$/, '').replace(/\/$/, '')}`;
    const data = events.map((ev) => toSchema(ev, pageUrl)).filter(Boolean);
    if (!data.length || !html.includes('</head>')) return res;
    const json = JSON.stringify(data).replace(/</g, '\\u003c');
    const out = html.replace('</head>', `<script type="application/ld+json" data-event-schema>${json}</script></head>`);
    const headers = new Headers(res.headers);
    headers.delete('content-length');
    headers.set('Netlify-CDN-Cache-Control', 'public, durable, s-maxage=3600, stale-while-revalidate=86400');
    return new Response(out, { status: 200, headers });
  } catch {
    return res;
  }
};

export const config = {
  path: ['/tour/*', '/venue/*'],
  excludedPath: ['/tour/*.json', '/venue/*.json'],
  cache: 'manual',
  onError: 'bypass',
};
