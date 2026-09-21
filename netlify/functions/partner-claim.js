// netlify/functions/partner-claim.js
// POST { kind, name, venueSlug?, email } → files a claim, sends a Supabase magic link.
// Venues must claim with a work email (free-mail domains are refused). On first login the
// console calls partner-claim?approve=1 with the session token: if the email domain matches
// the venue's official website domain in venues.json, the org is created and the page is theirs.
const { createClient } = require('@supabase/supabase-js');
const fs = require('fs'); const path = require('path');
const H = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type, Authorization', 'Access-Control-Allow-Methods': 'POST, OPTIONS' };
const FREE = new Set(['gmail.com','yahoo.com','outlook.com','hotmail.com','icloud.com','aol.com','me.com','live.com','proton.me','protonmail.com']);
const SITE = 'https://concertocity.com';
function domainOf(email) { return String(email || '').toLowerCase().split('@')[1] || ''; }
function venueDomain(slug) {
  // The venue's official domain is whatever its verified sections cite as officialLink.
  try {
    const info = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'data', 'venue_info.json'), 'utf8'))[slug] || {};
    const counts = {};
    for (const k of ['bagPolicy','parking','rideshare','concessions','accessibility','reEntry','ticketPickup','gates']) {
      const link = info[k] && info[k].officialLink; if (!link) continue;
      try { const h = new URL(link).hostname.replace(/^www\./, ''); counts[h] = (counts[h] || 0) + 1; } catch {}
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).map(x => x[0])[0] || '';
  } catch { return ''; }
}
exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: H, body: '' };
  const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  const q = event.queryStringParameters || {};
  try {
    if (q.approve) {
      const token = (event.headers.authorization || '').replace(/^Bearer /i, '');
      const { data: { user } } = await sb.auth.getUser(token);
      if (!user) return { statusCode: 401, headers: H, body: '{"error":"sign in first"}' };
      const { data: claims } = await sb.from('venue_claims').select('*').eq('email', user.email).eq('status', 'pending');
      const made = [];
      for (const c of claims || []) {
        const vd = venueDomain(c.venue_slug), ed = domainOf(user.email);
        const ok = vd && (ed === vd || ed.endsWith('.' + vd) || vd.endsWith('.' + ed));
        if (!ok) continue;
        const { data: org } = await sb.from('partner_orgs').insert({ kind: 'venue', name: c.venue_slug, venue_slug: c.venue_slug, email_domain: ed, plan: 'founding', plan_until: '2026-12-31' }).select().single();
        await sb.from('partner_members').insert({ org_id: org.id, user_id: user.id, role: 'owner' });
        await sb.from('venue_claims').update({ status: 'approved' }).eq('id', c.id);
        made.push(c.venue_slug);
      }
      return { statusCode: 200, headers: H, body: JSON.stringify({ approved: made }) };
    }
    if (event.httpMethod !== 'POST') return { statusCode: 405, headers: H, body: '' };
    const { kind, name, venueSlug, email } = JSON.parse(event.body || '{}');
    const em = String(email || '').trim().toLowerCase();
    if (!em.includes('@')) return { statusCode: 400, headers: H, body: '{"error":"email required"}' };
    if (kind === 'venue') {
      if (!venueSlug) return { statusCode: 400, headers: H, body: '{"error":"venue required"}' };
      if (FREE.has(domainOf(em))) return { statusCode: 400, headers: H, body: '{"error":"Use your venue work email so we can confirm you represent it."}' };
      await sb.from('venue_claims').insert({ venue_slug: venueSlug, email: em });
    } else {
      // Restaurants, hotels, artists: org is created immediately; Concerto reviews Perks before they go live.
      const { data: org } = await sb.from('partner_orgs').insert({ kind, name: String(name || em).slice(0, 120), email_domain: domainOf(em), plan: 'founding', plan_until: '2026-12-31' }).select().single();
      const { data: u } = await sb.auth.admin.listUsers({ perPage: 1000 });
      const existing = (u && u.users || []).find(x => (x.email || '').toLowerCase() === em);
      if (existing) await sb.from('partner_members').insert({ org_id: org.id, user_id: existing.id, role: 'owner' });
      else await sb.from('partner_members').insert({ org_id: org.id, user_id: '00000000-0000-0000-0000-000000000000', role: 'pending:' + em }).catch(() => {});
    }
    await sb.auth.signInWithOtp({ email: em, options: { emailRedirectTo: SITE + '/console/' } });
    return { statusCode: 200, headers: H, body: JSON.stringify({ ok: true }) };
  } catch (e) {
    return { statusCode: 500, headers: H, body: JSON.stringify({ error: 'try again' }) };
  }
};
