'use strict';
// Demo partners: a made-up restaurant and hotel shown as Concerto Partners at ANY venue, for
// showing prospects exactly what they would get. Never public:
//   - website: add ?demo=<PARTNER_DEMO_KEY> to a venue page or the search page (kept for the visit)
//   - app: the "Demo partners" switch in Settings, shown only to the accounts in DEMO_EMAILS
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

// Two made-up partners, placed a short walk from whichever venue is open, for showing
// prospects (and for screenshots). Fictional names, their own photos on concertocity.com, and
// directions to the spot on the map; Reserve and Book open the partner pages.
const VENUES = require('../../../data/venues.json');
const DEMO = [
  { kind: 'restaurant', id: 'demo-restaurant', name: 'Overture Kitchen & Bar', dLat: 0.0029, dLng: 0.0008,
    blurb: 'Seasonal American plates and cocktails, a short walk from the venue. Open late on show nights.',
    photo: `${SITE}/img/demo/overture-kitchen.jpg?v=2`, url: `${SITE}/partners/restaurants`,
    offer: 'Free dessert on show nights', details: 'Show this in the Concerto app when you order. Dine-in only.' },
  { kind: 'hotel', id: 'demo-hotel', name: 'The Coda Hotel', dLat: -0.0012, dLng: 0.0041,
    blurb: 'Boutique rooms steps from the venue, with a rooftop bar that stays open after the show.',
    photo: `${SITE}/img/demo/coda-hotel.jpg?v=2`, url: `${SITE}/partners/hotels`,
    offer: 'Late checkout after the show', details: 'Show this at check-in. Subject to availability.' },
];

// { partners, perks } in partner-content's shape, for one venue.
async function demoFor(slug) {
  const v = VENUES.find((x) => (x.id || x.slug) === slug);
  if (!v || v.lat == null || v.lng == null) return { partners: [], perks: [] };
  const partners = [], perks = [];
  for (const d of DEMO) {
    const lat = Math.round((v.lat + d.dLat) * 1e6) / 1e6, lng = Math.round((v.lng + d.dLng) * 1e6) / 1e6;
    const address = `Near ${v.name}${v.city ? ', ' + v.city : ''}`;
    const r = (x) => x * Math.PI / 180, h = Math.sin(r(lat - v.lat) / 2) ** 2 + Math.cos(r(v.lat)) * Math.cos(r(lat)) * Math.sin(r(lng - v.lng) / 2) ** 2;
    const distance_mi = Math.round(2 * 3958.8 * Math.asin(Math.sqrt(h)) * 10) / 10;
    partners.push({ id: d.id, kind: d.kind, name: d.name, venue_slugs: [slug], address, url: d.url, blurb: d.blurb, lat, lng, distance_mi, photo: d.photo, demo: true });
    perks.push({ id: `${d.id}-perk`, org_id: d.id, kind: d.kind, partner_name: d.name, offer: d.offer, details: d.details, url: d.url, address, lat, lng, venue_slugs: [slug], tour_slug: null });
  }
  return { partners, perks };
}

module.exports = { demoAllowed, demoFor };
