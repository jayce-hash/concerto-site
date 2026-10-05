// netlify/functions/partner-content.js
// The single read model for everything partners publish. The app and the website
// call this (never the tables) and merge it over the static JSON they already have:
//   GET /.netlify/functions/partner-content?venue=<slug>         one venue: overrides, stage times, perks, partners
//   GET /.netlify/functions/partner-content?tour=<slug>          perks tied to a tour
//   GET /.netlify/functions/partner-content?all=1                everything live (site build / cache warm)
// Public, cached 5 minutes at the edge.
//
// Paid only (Oct 5, 2026). Nothing a partner org publishes reaches fans unless the
// org is plan = 'paid' and inside its paid period (listed_until, set by Stripe):
//   - partner cards (restaurants/hotels)
//   - Perks from an org (Perks with no org_id were created by Concerto directly)
//   - a venue's own section edits, stage times, and the "Verified by the venue" mark
const { createClient } = require('@supabase/supabase-js');
const { livePerks } = require('./lib/perk-rules');
const H = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*', 'Cache-Control': 'public, max-age=300' };
const PERK_COLS = 'id,org_id,kind,partner_name,offer,details,url,address,lat,lng,venue_slugs,tour_slug,starts_on,ends_on';
const ORG_COLS = 'id,kind,name,venue_slug,venue_slugs,address,url,blurb,lat,lng,listed,listed_until';

function paidNow(o, today) { return o && o.plan === 'paid' && (!o.listed_until || o.listed_until >= today); }
function httpsOrNull(v) { try { const u = new URL(v); return u.protocol === 'https:' && !u.username && !u.password ? u.href : null; } catch (_) { return null; } }
function card(o) {
  return { id: o.id, kind: o.kind, name: o.name, venue_slugs: o.venue_slugs || [], address: o.address, url: httpsOrNull(o.url), blurb: o.blurb, lat: o.lat, lng: o.lng };
}

exports.handler = async (event) => {
  const q = event.queryStringParameters || {};
  const today = new Date().toISOString().slice(0, 10);
  try {
    const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const out = { venue: null, overrides: {}, stageTimes: [], perks: [], partners: [], claimed: false };
    // Every currently paid org, once. Small table; one query keeps the rules in one place.
    const orgsR = await sb.from('partner_orgs').select(ORG_COLS + ',plan').eq('plan', 'paid');
    if (orgsR.error) throw new Error('Partner query failed');
    const paid = (orgsR.data || []).filter(o => paidNow(o, today));
    const paidIds = new Set(paid.map(o => o.id));
    const perkOK = p => !p.org_id || paidIds.has(p.org_id);
    const listings = (slug) => paid.filter(o => (o.kind === 'restaurant' || o.kind === 'hotel') && o.listed
      && Array.isArray(o.venue_slugs) && o.venue_slugs.length && (!slug || o.venue_slugs.includes(slug))).map(card);

    if (q.venue) {
      const slug = String(q.venue).slice(0, 120);
      const venueOrg = paid.find(o => o.kind === 'venue' && o.venue_slug === slug);
      const [o, s, p] = await Promise.all([
        sb.from('venue_overrides').select('section,content,verified_at').eq('venue_slug', slug),
        sb.from('stage_times').select('event_date,tm_event_id,doors,opener,headliner,note,source').eq('venue_slug', slug).gte('event_date', today).order('event_date').limit(30),
        sb.from('perks').select(PERK_COLS).eq('status', 'live').contains('venue_slugs', [slug]),
      ]);
      if ([o, s, p].some(r => r.error)) throw new Error('Partner query failed');
      out.venue = slug; out.claimed = Boolean(venueOrg);
      if (venueOrg) {
        for (const r of o.data || []) out.overrides[r.section] = { ...r.content, verified: r.verified_at, verifiedBy: 'venue' };
        out.stageTimes = (s.data || []).filter(r => r.source !== 'venue' || venueOrg);
      } else {
        out.stageTimes = (s.data || []).filter(r => r.source !== 'venue');
      }
      out.perks = livePerks((p.data || []).filter(perkOK), today);
      out.partners = listings(slug);
    } else if (q.tour) {
      const p = await sb.from('perks').select(PERK_COLS).eq('status', 'live').eq('tour_slug', String(q.tour).slice(0, 160));
      if (p.error) throw new Error('Partner query failed');
      out.perks = livePerks((p.data || []).filter(perkOK), today);
    } else if (q.all) {
      const [o, p] = await Promise.all([
        sb.from('venue_overrides').select('venue_slug,section,content,verified_at'),
        sb.from('perks').select(PERK_COLS).eq('status', 'live'),
      ]);
      if ([o, p].some(r => r.error)) throw new Error('Partner query failed');
      const claimed = new Set(paid.filter(x => x.kind === 'venue' && x.venue_slug).map(x => x.venue_slug));
      out.overrides = {};
      for (const r of o.data || []) if (claimed.has(r.venue_slug)) (out.overrides[r.venue_slug] ||= {})[r.section] = { ...r.content, verified: r.verified_at, verifiedBy: 'venue' };
      out.perks = livePerks((p.data || []).filter(perkOK), today);
      out.partners = listings();
      out.claimedVenues = [...claimed];
    }
    return { statusCode: 200, headers: H, body: JSON.stringify(out) };
  } catch (e) {
    return { statusCode: 503, headers: { ...H, 'Cache-Control': 'no-store' }, body: JSON.stringify({ venue: q.venue || null, overrides: {}, stageTimes: [], perks: [], partners: [], claimed: false, error: 'unavailable' }) };
  }
};
