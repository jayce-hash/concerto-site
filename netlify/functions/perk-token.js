// The app asks for a fresh code every ~15 seconds while the Use Perk screen is open.
// POST { perkId, fan } -> { token, url, expires } or { redeemed: true, at }. GET ?perk&fan -> status only.
const guard = require('./lib/guard');
const { createClient } = require('@supabase/supabase-js');
const { scanToken, today } = require('./lib/perk-codes');
const SITE = 'https://concertocity.com';
const H = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS' };
const out = (code, body) => ({ statusCode: code, headers: H, body: JSON.stringify(body) });

async function livePerk(sb, perkId) {
  const { data: p } = await sb.from('perks').select('id,org_id,status,starts_on,ends_on,offer').eq('id', perkId).maybeSingle();
  const d = today();
  if (!p || p.status !== 'live' || (p.starts_on && p.starts_on > d) || (p.ends_on && p.ends_on < d)) return null;
  if (p.org_id) {
    const { data: o } = await sb.from('partner_orgs').select('plan,listed,listed_until').eq('id', p.org_id).maybeSingle();
    if (!o || o.plan !== 'paid' || o.listed === false || (o.listed_until && o.listed_until < d)) return null;
  }
  return p;
}

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: H, body: '' };
  if (guard.limited(event, 40, 60000)) return out(429, { error: 'Slow down for a moment.' });
  const q = event.httpMethod === 'POST' ? (() => { try { return JSON.parse(event.body || '{}'); } catch { return {}; } })() : (event.queryStringParameters || {});
  const perkId = String(q.perkId || q.perk || ''), fan = String(q.fan || '').slice(0, 80);
  if (!/^[0-9a-f-]{36}$/i.test(perkId) || fan.length < 8) return out(400, { error: 'Missing Perk or device.' });
  const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } });
  const { data: used } = await sb.from('perk_redemptions').select('redeemed_at').eq('perk_id', perkId).eq('fan_key', fan).eq('redeemed_day', today()).maybeSingle();
  if (used) return out(200, { redeemed: true, at: used.redeemed_at });
  if (event.httpMethod !== 'POST') return out(200, { redeemed: false });
  if (!(await livePerk(sb, perkId))) return out(410, { error: 'This Perk isn’t available right now.' });
  const token = scanToken(perkId, fan);
  return out(200, { token, url: `${SITE}/.netlify/functions/perk-redeem?t=${encodeURIComponent(token)}`, expires: Date.now() + 45000 });
};
module.exports.livePerk = livePerk;
