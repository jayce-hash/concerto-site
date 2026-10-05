// One-click removal from the new-partner alert email: takes the card down, cancels the
// subscription, refunds the latest payment. GET shows a confirm button (email apps open
// links in previews, so a GET alone never removes anything); POST does it.
const { createClient } = require('@supabase/supabase-js');
const Stripe = require('stripe');
const { tokenOk } = require('./lib/partner-self-serve');

const page = (title, body) => ({ statusCode: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' },
  body: `<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><body style="font-family:-apple-system,system-ui,sans-serif;max-width:560px;margin:60px auto;padding:0 20px;color:#121E36"><h1 style="font-family:Georgia,serif;font-weight:500">${title}</h1>${body}</body>` });
const esc = (s) => String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

exports.handler = async (event) => {
  const p = event.httpMethod === 'POST' ? Object.fromEntries(new URLSearchParams(event.isBase64Encoded ? Buffer.from(event.body || '', 'base64').toString() : (event.body || ''))) : (event.queryStringParameters || {});
  const org = String(p.org || ''), t = String(p.t || '');
  if (!org || !tokenOk(org, t)) return page('Link not valid', '<p>This removal link is not valid.</p>');
  const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } });
  const { data: o } = await sb.from('partner_orgs').select('id,name,plan,listed,stripe_subscription_id,stripe_customer_id').eq('id', org).maybeSingle();
  if (!o) return page('Not found', '<p>That partner no longer exists.</p>');
  if (event.httpMethod !== 'POST') {
    return page(`Remove ${esc(o.name)}?`, `<p>This takes their card down right away, cancels their subscription, and refunds their latest payment.</p>
      <form method="POST"><input type="hidden" name="org" value="${esc(org)}"><input type="hidden" name="t" value="${esc(t)}">
      <button style="background:#121E36;color:#fff;border:0;border-radius:999px;padding:12px 22px;font-size:16px;cursor:pointer">Remove and refund</button></form>`);
  }
  await sb.from('partner_orgs').update({ listed: false, plan: 'cancelled' }).eq('id', org);
  const notes = [];
  try {
    const stripe = Stripe(process.env.STRIPE_SECRET_KEY);
    if (o.stripe_subscription_id) { try { await stripe.subscriptions.cancel(o.stripe_subscription_id); notes.push('Subscription cancelled.'); } catch { notes.push('Subscription was already cancelled.'); } }
    if (o.stripe_customer_id) {
      const ch = await stripe.charges.list({ customer: o.stripe_customer_id, limit: 1 });
      const c = ch.data[0];
      if (c && c.paid && !c.refunded) { await stripe.refunds.create({ charge: c.id }); notes.push(`Refunded $${(c.amount / 100).toFixed(2)}.`); }
      else notes.push('No unrefunded payment found.');
    }
  } catch (e) { notes.push('Stripe step failed; check their subscription and payment in Stripe.'); }
  return page(`${esc(o.name)} removed`, `<p>Their card is down.</p><p>${notes.map(esc).join(' ')}</p>`);
};
