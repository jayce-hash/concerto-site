// Staff scan the fan's live code with any phone camera, which opens this page.
// GET ?t=<scan token>: shows the Perk and asks for the partner's 4-digit code.
// POST t=<claim token>&code=1234: redeems (once per fan, per Perk, per day).
const guard = require('./lib/guard');
const { createClient } = require('@supabase/supabase-js');
const { verify, claimToken, hashCode, today } = require('./lib/perk-codes');
const { livePerk } = require('./perk-token');

const esc = (s) => String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function page(kind, title, body) {
  const tone = { ok: '#1F7A4D', bad: '#A42237', info: '#121E36' }[kind];
  return { statusCode: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' }, body:
`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)} | Concerto Perk</title>
<style>body{margin:0;font-family:-apple-system,system-ui,"DM Sans",sans-serif;background:#F8F9F9;color:#121E36}main{max-width:520px;margin:0 auto;padding:28px 22px 40px}
.brand{font-family:Georgia,serif;letter-spacing:.2em;font-size:15px;color:#121E36;margin:0 0 26px}.mark{width:64px;height:64px;border-radius:32px;display:flex;align-items:center;justify-content:center;font-size:34px;color:#fff;background:${tone};margin-bottom:16px}
h1{font-family:Georgia,serif;font-weight:500;font-size:34px;line-height:1.15;margin:0 0 8px;color:${tone}}.offer{font-size:24px;font-weight:700;margin:14px 0 4px}.sub{font-size:17px;color:#3B4458;line-height:1.5;margin:0 0 6px}
.box{background:#fff;border:1px solid rgba(18,30,54,.1);border-radius:18px;padding:18px;margin-top:18px}label{display:block;font-weight:600;font-size:15px;margin-bottom:8px}
input{box-sizing:border-box;width:100%;height:64px;font-size:32px;letter-spacing:.4em;text-align:center;border:1px solid rgba(18,30,54,.25);border-radius:14px}
button{margin-top:14px;width:100%;height:58px;border:0;border-radius:999px;background:#121E36;color:#fff;font-size:18px;font-weight:700}.small{font-size:13px;color:#5B6478;margin-top:16px}</style></head>
<body><main><p class="brand">CONCERTO</p><div class="mark">${kind === 'ok' ? '&#10003;' : kind === 'bad' ? '&#10005;' : '&#9733;'}</div><h1>${esc(title)}</h1>${body}</main></body></html>` };
}

exports.handler = async (event) => {
  const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } });
  const form = event.httpMethod === 'POST'
    ? Object.fromEntries(new URLSearchParams(event.isBase64Encoded ? Buffer.from(event.body || '', 'base64').toString() : (event.body || ''))) : null;
  const t = verify(form ? form.t : (event.queryStringParameters || {}).t);
  if (!t || !t.p || !t.f) return page('bad', 'Not a valid code', '<p class="sub">Ask the guest to open the Perk again in the Concerto app and scan the new code.</p>');
  if (Date.now() > t.e) return page('bad', 'Code expired', '<p class="sub">This code is no longer live. Screenshots don’t work. Ask the guest to open the Perk in the Concerto app and scan the code on their screen.</p>');
  const perk = await livePerk(sb, t.p);
  if (!perk) return page('bad', 'Perk not available', '<p class="sub">This Perk has ended or isn’t active.</p>');
  const { data: org } = await sb.from('partner_orgs').select('id,name,redeem_code_hash').eq('id', perk.org_id).maybeSingle();
  const { data: used } = await sb.from('perk_redemptions').select('redeemed_at').eq('perk_id', t.p).eq('fan_key', t.f).eq('redeemed_day', today()).maybeSingle();
  if (used) return page('bad', 'Already used today', `<p class="offer">${esc(perk.offer)}</p><p class="sub">This guest already redeemed this Perk today.</p>`);
  const head = `<p class="offer">${esc(perk.offer)}</p><p class="sub">${esc(org ? org.name : '')}</p>`;

  if (!form) {
    if (t.k !== 'scan') return page('bad', 'Not a valid code', '<p class="sub">Scan the code on the guest’s screen.</p>');
    return page('info', 'Valid Perk', head + `<form class="box" method="POST"><input type="hidden" name="t" value="${esc(claimToken(t))}">
      <label for="code">Enter your 4-digit staff code</label><input id="code" name="code" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" autocomplete="one-time-code" required autofocus>
      <button type="submit">Redeem</button></form><p class="small">One use per guest, per day.</p>`);
  }
  if (t.k !== 'claim') return page('bad', 'Not a valid code', '<p class="sub">Scan the code on the guest’s screen.</p>');
  if (guard.limited(event, 5, 10 * 60000)) return page('bad', 'Too many tries', '<p class="sub">Wait a few minutes, then scan the guest’s code again.</p>');
  if (!org || !org.redeem_code_hash) return page('bad', 'Staff code not set', '<p class="sub">This partner hasn’t set a staff code yet. Email jayce@concertocity.com.</p>');
  if (!/^\d{4}$/.test(String(form.code || '')) || hashCode(org.id, form.code) !== org.redeem_code_hash)
    return page('bad', 'Wrong staff code', head + `<form class="box" method="POST"><input type="hidden" name="t" value="${esc(form.t)}">
      <label for="code">Try your 4-digit staff code again</label><input id="code" name="code" inputmode="numeric" maxlength="4" required autofocus><button type="submit">Redeem</button></form>`);
  const { error } = await sb.from('perk_redemptions').insert({ perk_id: t.p, org_id: org.id, fan_key: t.f, redeemed_day: today() });
  if (error) return page('bad', 'Already used today', head + '<p class="sub">This guest already redeemed this Perk today.</p>');
  const at = new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/Chicago' });
  return page('ok', 'Redeemed', head + `<p class="sub">Redeemed at ${esc(at)}. Enjoy the show!</p>`);
};
