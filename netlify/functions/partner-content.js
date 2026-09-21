// netlify/functions/partner-content.js
// The single read model for everything partners publish. The app and the website
// call this (never the tables) and merge it over the static JSON they already have:
//   GET /.netlify/functions/partner-content?venue=<slug>         one venue: overrides, stage times, perks
//   GET /.netlify/functions/partner-content?tour=<slug>          perks tied to a tour
//   GET /.netlify/functions/partner-content?all=1                everything live (site build / cache warm)
// Public, cached 5 minutes at the edge. Only status='live' perks and current stage times leave here.
const { createClient } = require('@supabase/supabase-js');
const { livePerks } = require('./lib/perk-rules');
const H = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*', 'Cache-Control': 'public, max-age=300' };

exports.handler = async (event) => {
  const q = event.queryStringParameters || {};
  const today = new Date().toISOString().slice(0, 10);
  try {
    const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const out = { venue: null, overrides: {}, stageTimes: [], perks: [], claimed: false };
    if (q.venue) {
      const slug = String(q.venue).slice(0, 120);
      const [o, s, p, org] = await Promise.all([
        sb.from('venue_overrides').select('section,content,verified_at').eq('venue_slug', slug),
        sb.from('stage_times').select('event_date,tm_event_id,doors,opener,headliner,note,source').eq('venue_slug', slug).gte('event_date', today).order('event_date').limit(30),
        sb.from('perks').select('id,kind,partner_name,offer,details,url,address,lat,lng,venue_slugs,tour_slug,starts_on,ends_on').eq('status', 'live').contains('venue_slugs', [slug]),
        sb.from('partner_orgs').select('id,name').eq('kind', 'venue').eq('venue_slug', slug).in('plan', ['founding', 'paid', 'trial']).maybeSingle(),
      ]);
      if ([o, s, p, org].some(r => r.error)) throw new Error('Partner query failed');
      out.venue = slug; out.claimed = Boolean(org.data);
      for (const r of o.data || []) out.overrides[r.section] = { ...r.content, verified: r.verified_at, verifiedBy: 'venue' };
      out.stageTimes = s.data || [];
      out.perks = livePerks(p.data, today);
    } else if (q.tour) {
      const p = await sb.from('perks').select('id,kind,partner_name,offer,details,url,address,lat,lng,venue_slugs,tour_slug,starts_on,ends_on').eq('status', 'live').eq('tour_slug', String(q.tour).slice(0, 160));
      if (p.error) throw new Error('Partner query failed');
      out.perks = livePerks(p.data, today);
    } else if (q.all) {
      const [o, p, orgs] = await Promise.all([
        sb.from('venue_overrides').select('venue_slug,section,content,verified_at'),
        sb.from('perks').select('id,kind,partner_name,offer,details,url,address,lat,lng,venue_slugs,tour_slug,starts_on,ends_on').eq('status', 'live'),
        sb.from('partner_orgs').select('venue_slug').eq('kind', 'venue').in('plan', ['founding', 'paid', 'trial']),
      ]);
      if ([o, p, orgs].some(r => r.error)) throw new Error('Partner query failed');
      out.overrides = {}; for (const r of o.data || []) (out.overrides[r.venue_slug] ||= {})[r.section] = { ...r.content, verified: r.verified_at, verifiedBy: 'venue' };
      out.perks = livePerks(p.data, today); out.claimedVenues = (orgs.data || []).map(x => x.venue_slug);
    }
    return { statusCode: 200, headers: H, body: JSON.stringify(out) };
  } catch (e) {
    return { statusCode: 503, headers: { ...H, 'Cache-Control': 'no-store' }, body: JSON.stringify({ venue: q.venue || null, overrides: {}, stageTimes: [], perks: [], claimed: false, error: 'unavailable' }) };
  }
};
