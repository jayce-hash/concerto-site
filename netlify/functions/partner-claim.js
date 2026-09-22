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
// Explicit, human-maintained: data/venue_domains.json maps venue slug -> the
// venue's own email/web domain (e.g. "americanairlinescenter.com"). A claim from an
// address on that exact domain (or a subdomain) is approved; anything else waits
// for manual review in Supabase (venue_claims.status stays 'pending'). Ownership is
// never inferred from source links: a ticketing, promoter, or parent-company domain
// appearing in citations must not unlock a venue's page.
function venueDomain(slug) {
  try {
    const map = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'data', 'venue_domains.json'), 'utf8'));
    const d = map[slug]; return typeof d === 'string' ? d.toLowerCase().replace(/^www\./, '') : '';
  } catch { return ''; }
}
const FOUNDING_UNTIL = process.env.FOUNDING_PLAN_UNTIL || '2026-12-31';
exports.handler = async (event) => {
  const guard = require('./lib/guard');
  if (!guard.originOf(event).ok) return guard.refuse(event, 403, 'forbidden', 'POST, OPTIONS');
  if (event.httpMethod === 'POST' && guard.limited(event, 5, 600000)) return guard.refuse(event, 429, 'too many claims, try again later', 'POST, OPTIONS');
  if (String(event.body || '').length > 8192) return guard.refuse(event, 413, 'too large', 'POST, OPTIONS');
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
        if (String(c.venue_slug).startsWith('partner:')) {
          const [, kind, name] = c.venue_slug.split(':');
          const { data: org } = await sb.from('partner_orgs').insert({ kind, name: name || user.email, email_domain: domainOf(user.email), plan: 'founding', plan_until: FOUNDING_UNTIL }).select().single();
          await sb.from('partner_members').insert({ org_id: org.id, user_id: user.id, role: 'owner' });
          await sb.from('venue_claims').update({ status: 'approved' }).eq('id', c.id);
          made.push(c.venue_slug); continue;
        }
        const vd = venueDomain(c.venue_slug), ed = domainOf(user.email);
        const ok = Boolean(vd) && (ed === vd || ed.endsWith('.' + vd));
        if (!ok) continue;
        const { data: existing } = await sb.from('partner_orgs').select('id').eq('kind', 'venue').eq('venue_slug', c.venue_slug).maybeSingle();
        if (existing) { await sb.from('partner_members').upsert({ org_id: existing.id, user_id: user.id, role: 'owner' }); await sb.from('venue_claims').update({ status: 'approved' }).eq('id', c.id); made.push(c.venue_slug); continue; }
        const { data: org } = await sb.from('partner_orgs').insert({ kind: 'venue', name: c.venue_slug, venue_slug: c.venue_slug, email_domain: ed, plan: 'founding', plan_until: FOUNDING_UNTIL }).select().single();
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
      // Restaurants, hotels, artists: record the request; the org is created on first
      // sign-in (approve=1), once the email has proven itself through the magic link.
      await sb.from('venue_claims').insert({ venue_slug: `partner:${kind}:${String(name || em).slice(0, 80)}`, email: em });
    }
    await sb.auth.signInWithOtp({ email: em, options: { emailRedirectTo: SITE + '/console/' } });
    return { statusCode: 200, headers: H, body: JSON.stringify({ ok: true }) };
  } catch (e) {
    return { statusCode: 500, headers: H, body: JSON.stringify({ error: 'try again' }) };
  }
};
