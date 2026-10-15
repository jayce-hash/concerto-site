'use strict';
// Paid restaurant and hotel partners for one venue, with their Perk if they have one.
// Same rules as partner-content.js: only orgs on the paid plan, inside their paid period,
// listed, and tied to the venue. Used by Concerto AI (ask.js) so partners are suggested first.
// Cached in memory for 5 minutes per venue. Fails open to an empty list.
const { createClient } = require('@supabase/supabase-js');
const { livePerks } = require('./perk-rules');

const TTL = 5 * 60 * 1000;
const cache = new Map();

function https(v) { try { const u = new URL(v); return u.protocol === 'https:' && !u.username && !u.password ? u.href : null; } catch (_) { return null; } }
function miles(a, b) {
  if (!a || !b || a.lat == null || b.lat == null || a.lng == null || b.lng == null) return null;
  const R = 3958.8, r = (d) => d * Math.PI / 180;
  const x = Math.sin(r(b.lat - a.lat) / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(r(b.lng - a.lng) / 2) ** 2;
  return Math.round(2 * R * Math.asin(Math.sqrt(x)) * 10) / 10;
}
// The same daily turn as the app and the website (sorted by id, then rotated by a hash of the
// day, venue and row), so a fan sees the same partner first everywhere on a given day.
function rotateDaily(items, seed, today) {
  if (items.length < 2) return items;
  let h = 2166136261;
  for (const ch of `${today}|${seed}`) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
  const off = (h >>> 0) % items.length;
  return [...items.slice(off), ...items.slice(0, off)];
}
function daily(list, today, slug) {
  const byId = (k) => list.filter((p) => p.kind === k).sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  return [...rotateDaily(byId('restaurant'), `${slug}:restaurants`, today), ...rotateDaily(byId('hotel'), `${slug}:hotels`, today)];
}

async function load(slug, venue) {
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) return [];
  const today = new Date().toISOString().slice(0, 10);
  const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  const [o, p] = await Promise.all([
    sb.from('partner_orgs').select('id,kind,name,venue_slugs,address,url,blurb,lat,lng,listed,listed_until,plan').eq('plan', 'paid').contains('venue_slugs', [slug]),
    sb.from('perks').select('id,org_id,kind,partner_name,offer,details,url,address,lat,lng,venue_slugs,tour_slug,starts_on,ends_on').eq('status', 'live').contains('venue_slugs', [slug]),
  ]);
  if (o.error || p.error) return [];
  const paid = (o.data || []).filter((x) => (!x.listed_until || x.listed_until >= today));
  const paidIds = new Set(paid.map((x) => x.id));
  const out = new Map();
  for (const x of paid) {
    if (!x.listed || (x.kind !== 'restaurant' && x.kind !== 'hotel')) continue;
    out.set(x.id, { id: x.id, kind: x.kind, name: x.name, address: x.address || '', url: https(x.url), blurb: x.blurb || '', miles: miles(venue, x), perk: null });
  }
  for (const k of livePerks((p.data || []).filter((x) => !x.tour_slug && (!x.org_id || paidIds.has(x.org_id))), today)) {
    const kind = k.kind || 'restaurant';
    if (kind !== 'restaurant' && kind !== 'hotel') continue;
    const key = k.org_id && out.has(k.org_id) ? k.org_id : `perk:${k.org_id || String(k.partner_name).toLowerCase()}`;
    const card = out.get(key) || { id: key, kind, name: k.partner_name, address: k.address || '', url: null, blurb: '', miles: miles(venue, k), perk: null };
    if (!card.perk) card.perk = { offer: k.offer, details: k.details, url: k.url };
    out.set(key, card);
  }
  return daily([...out.values()], today, slug);
}

async function venuePartners(slug, venue) {
  if (!slug) return [];
  const hit = cache.get(slug);
  if (hit && Date.now() - hit.t < TTL) return hit.list;
  let list = [];
  try { list = await load(slug, venue); } catch (_) { list = []; }
  cache.set(slug, { t: Date.now(), list });
  return list;
}

// Demo partners in this module's shape (see lib/demo-partners.js).
async function demoVenuePartners(slug, venue) {
  const { demoFor } = require('./demo-partners');
  const d = await demoFor(slug);
  return d.partners.map((p) => {
    const k = d.perks.find((x) => x.org_id === p.id);
    return { id: p.id, kind: p.kind, name: p.name, address: p.address, url: p.url, blurb: p.blurb, miles: miles(venue, p), perk: k ? { offer: k.offer, details: k.details, url: k.url } : null };
  });
}

module.exports = { venuePartners, demoVenuePartners, miles };
