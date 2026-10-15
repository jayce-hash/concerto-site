'use strict';
// Demo partners: a restaurant and a hotel shown as Concerto Partners at ANY venue, for showing
// prospects exactly what they would get. Never public:
//   - website: add ?demo=<PARTNER_DEMO_KEY> to a venue page or the search page (kept for the visit)
//   - app: the "Demo partners" switch in Settings, shown only to the accounts in DEMO_EMAILS
// The demo picks the nearest restaurant and the nearest hotel from Concerto's own Nearby data
// for that venue, so the name, photo and distance are real. Description and Perk are demo text.
const { createClient } = require('@supabase/supabase-js');

const SITE = 'https://concertocity.com';
const KEY = () => process.env.PARTNER_DEMO_KEY || 'cc-demo-7q4m';
const EMAILS = () => String(process.env.DEMO_EMAILS || 'jayce@concertocity.com,partners@concertocity.com').toLowerCase().split(',').map((s) => s.trim()).filter(Boolean);

// Allowed when the demo key matches, or when the signed-in user is on the demo list.
async function demoAllowed(demo, headers) {
  if (!demo) return false;
  if (String(demo) === KEY()) return true;
  const auth = (headers || {}).authorization || (headers || {}).Authorization || '';
  const token = auth.replace(/^Bearer\s+/i, '').trim();
  if (!token || !process.env.SUPABASE_URL) return false;
  try {
    const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const { data: { user } } = await sb.auth.getUser(token);
    return Boolean(user && user.email && EMAILS().includes(user.email.toLowerCase()));
  } catch (_) { return false; }
}

function mapsUrl(p) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.name)}${p.place_id ? `&query_place_id=${encodeURIComponent(p.place_id)}` : ''}`;
}

// { partners, perks } in partner-content's shape, for one venue.
async function demoFor(slug) {
  if (!/^[a-z0-9-]{1,120}$/.test(String(slug || ''))) return { partners: [], perks: [] };
  let nb = null;
  try { const r = await fetch(`${SITE}/data/nearby/${slug}.json`); if (r.ok) nb = await r.json(); } catch (_) {}
  const tabs = (nb && nb.tabs) || {};
  // A believable partner: a sit-down restaurant or a real hotel, not a chain counter, a
  // convenience store or a short-term rental. Closest of those, rated places first.
  const CHAIN = /starbucks|7-eleven|mcdonald|subway|chipotle|raising cane|cava\b|panera|taco bell|wendy|burger king|chick-fil-a|dunkin|sizzler|domino|pizza hut|papa john|popeyes|kfc|jack in the box|five guys|shake shack|sweetgreen|insomnia cookies|panda express|tim hortons|denny|ihop|applebee|olive garden|chili's|wingstop|little caesars|jersey mike|jimmy john|potbelly|smoothie|juice|toastique|walgreens|cvs/i;
  const NOT_FOOD = ['fast_food_restaurant', 'coffee_shop', 'cafe', 'convenience_store', 'bakery', 'dessert_shop', 'ice_cream_shop', 'sandwich_shop', 'juice_shop', 'donut_shop', 'grocery_store', 'gas_station', 'meal_takeaway'];
  const RENTAL = /apartment|studio|bedroom|\bhome\b|house|condo|loft|airbnb|room in|suite in|villa|hostel|motel|rv park|campground|residence|\bapt\b|\d\s?-?(bd|bdr|br)\b|penthouse|wandersphere|luxurious|\bvacation\b/i;
  const ok = {
    restaurants: (i) => (i.types || []).includes('restaurant') && !(i.types || []).some((t) => NOT_FOOD.includes(t)) && !CHAIN.test(i.name),
    hotels: (i) => (i.types || []).some((t) => t === 'hotel' || t === 'lodging') && !RENTAL.test(i.name),
  };
  const pick = (k) => {
    const list = ((tabs[k] && tabs[k].items) || []).filter((i) => i && i.name && i.lat != null && (i.distance_mi == null || i.distance_mi <= 1.5));
    const venueName = String((nb && nb.venueName) || '').toLowerCase();
    const good = list.filter(ok[k]).filter((i) => !venueName || i.name.toLowerCase() !== venueName);
    // Nothing believable nearby (e.g. only rentals): no demo of that kind rather than a bad one.
    return good.find((i) => (i.rating || 0) >= 4) || good[0] || null;
  };
  const partners = [], perks = [];
  const add = (item, kind, offer, details) => {
    if (!item) return;
    const id = `demo-${kind}`;
    partners.push({ id, kind, name: item.name, venue_slugs: [slug], address: item.address || '', url: mapsUrl(item),
      blurb: kind === 'hotel' ? 'Demo listing. The hotel’s one-line description shows here.' : 'Demo listing. The restaurant’s one-line description shows here.',
      lat: item.lat, lng: item.lng, place_id: item.place_id || null, demo: true });
    perks.push({ id: `${id}-perk`, org_id: id, kind, partner_name: item.name, offer, details, url: mapsUrl(item), address: item.address || '', lat: item.lat, lng: item.lng, venue_slugs: [slug], tour_slug: null });
  };
  add(pick('restaurants'), 'restaurant', 'Free dessert on show nights', 'Show this offer in the Concerto app. Dine-in only. (Demo offer)');
  add(pick('hotels'), 'hotel', 'Late checkout after the show', 'Show this offer at check-in. Subject to availability. (Demo offer)');
  return { partners, perks };
}

module.exports = { demoAllowed, demoFor };
