// netlify/functions/partner-checkout.js
// One payment link per partner. Jayce sends:
//   https://concertocity.com/.netlify/functions/partner-checkout?org=<partner_orgs.id>&plan=monthly
//   https://concertocity.com/.netlify/functions/partner-checkout?org=<partner_orgs.id>&plan=annual
// It opens Stripe Checkout for that partner's subscription ($99/month or $999/year).
// On payment, stripe-webhook.js marks the org paid and their card goes live.
//
// Env: STRIPE_SECRET_KEY, STRIPE_PRICE_PARTNER_MONTHLY, STRIPE_PRICE_PARTNER_ANNUAL, STRIPE_PRICE_HOTEL_MONTHLY, STRIPE_PRICE_HOTEL_ANNUAL,
//      SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
const Stripe = require('stripe');
const { createClient } = require('@supabase/supabase-js');
const SITE = 'https://concertocity.com';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function page(status, title, body) {
  return {
    statusCode: status,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' },
    body: `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title} | Concerto</title><body style="font-family:system-ui,sans-serif;background:#F8F9F9;color:#121E36;display:grid;place-items:center;min-height:100vh;margin:0"><main style="max-width:440px;padding:32px;text-align:center"><h1 style="font-size:24px">${title}</h1><p>${body}</p><p><a href="${SITE}/partners/restaurants" style="color:#121E36">Concerto Partners</a></p></main>`,
  };
}

exports.handler = async (event) => {
  const q = event.queryStringParameters || {};
  const org = String(q.org || '');
  const plan = q.plan === 'annual' ? 'annual' : 'monthly';
  if (!UUID.test(org)) return page(400, 'Link not recognized', 'Please use the payment link from your Concerto email, or reply to it for a new one.');
  try {
    const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const { data: o, error } = await sb.from('partner_orgs').select('id,kind,name,plan,listed_until,stripe_customer_id,venue_slugs').eq('id', org).maybeSingle();
    if (error) throw error;
    if (!o || !['restaurant', 'hotel'].includes(o.kind)) return page(404, 'Link not recognized', 'Please reply to your Concerto email for a new payment link.');
    const today = new Date().toISOString().slice(0, 10);
    if (o.plan === 'paid' && (!o.listed_until || o.listed_until >= today)) return page(200, 'You are all set', `${o.name} is already an active Concerto Partner. Thank you.`);
    // Hotels: $299/month or $2,990/year. Restaurants: $99/month or $999/year.
    const hotel = o.kind === 'hotel';
    const price = hotel
      ? (plan === 'annual' ? process.env.STRIPE_PRICE_HOTEL_ANNUAL : process.env.STRIPE_PRICE_HOTEL_MONTHLY)
      : (plan === 'annual' ? process.env.STRIPE_PRICE_PARTNER_ANNUAL : process.env.STRIPE_PRICE_PARTNER_MONTHLY);
    if (!price) throw new Error('missing price env');
    const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      line_items: [{ price, quantity: 1 }],
      client_reference_id: `partner:${o.id}`,
      metadata: { partner_org_id: o.id, partner_name: o.name },
      subscription_data: { metadata: { partner_org_id: o.id, partner_name: o.name }, description: `Concerto Partner: ${o.name}` },
      ...(o.stripe_customer_id ? { customer: o.stripe_customer_id } : {}),
      success_url: `${SITE}/partners-thank-you?paid=1&venue=${encodeURIComponent(((o.venue_slugs || [])[0]) || '')}`,
      cancel_url: `${SITE}/partners/restaurants`,
    });
    return { statusCode: 303, headers: { Location: session.url, 'Cache-Control': 'no-store' }, body: '' };
  } catch (e) {
    console.error('partner-checkout:', e.message);
    return page(500, 'Something went wrong', 'Please try the link again in a minute, or reply to your Concerto email and we will sort it out.');
  }
};
