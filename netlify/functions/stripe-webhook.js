// Stripe web checkout -> Supabase entitlement synchronization.
// Netlify Lambda-compatible handler; event.body is passed raw to Stripe so
// signature verification is performed against the exact webhook payload.

const Stripe = require('stripe');
const { createClient } = require('@supabase/supabase-js');

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

function tierFor(priceId) {
  return priceId === process.env.STRIPE_PRICE_ANNUAL ? 'annual' : 'monthly';
}
// Newer Stripe API versions moved current_period_end from the subscription onto
// its items; read either so expiry dates are never silently null.
function periodEnd(sub) {
  const t = sub.current_period_end || sub.items?.data?.[0]?.current_period_end;
  return t ? new Date(t * 1000) : null;
}

// ---------- Concerto Partners (restaurants/hotels) ----------
// A partner's card is public while plan = 'paid' and today <= listed_until.
// listed_until = end of the paid period + 3 days, so a renewal that lands a
// little late never blinks the card off. Stripe drives every change.
function partnerOrgId(obj) {
  const ref = obj.client_reference_id || '';
  return obj.metadata?.partner_org_id || (ref.startsWith('partner:') ? ref.slice(8) : '');
}
function graceDate(sub) {
  const end = periodEnd(sub); if (!end) return null;
  return new Date(end.getTime() + 3 * 86400000).toISOString().slice(0, 10);
}
async function syncPartner(sub, orgId) {
  const active = activeStatus(sub.status);
  const interval = sub.items?.data?.[0]?.price?.recurring?.interval || null;
  const patch = active
    ? { plan: 'paid', listed: true, listed_until: graceDate(sub), stripe_subscription_id: sub.id, billing_interval: interval, stripe_customer_id: sub.customer || null }
    : { plan: 'cancelled', listed: false, stripe_subscription_id: sub.id };
  let q = supabase.from('partner_orgs').update(patch);
  q = orgId ? q.eq('id', orgId) : q.eq('stripe_subscription_id', sub.id);
  const { error } = await q;
  if (error) throw error;
  if (active && orgId) {
    // First payment: start date, only if not already set.
    await supabase.from('partner_orgs').update({ listed_from: new Date().toISOString().slice(0, 10) }).eq('id', orgId).is('listed_from', null);
  }
}

function activeStatus(status) {
  // past_due can still be in Stripe's retry/recovery flow. Do not remove paid
  // access until Stripe moves the subscription to unpaid/canceled/deleted.
  return ['active', 'trialing', 'past_due'].includes(status);
}

exports.handler = async function (event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method Not Allowed' };

  const sig = event.headers['stripe-signature'] || event.headers['Stripe-Signature'];
  let stripeEvent;
  try {
    stripeEvent = stripe.webhooks.constructEvent(
      event.body || '',
      sig,
      process.env.STRIPE_WEBHOOK_SECRET,
    );
  } catch (err) {
    console.error('stripe signature error:', err.message);
    return { statusCode: 400, body: `Webhook error: ${err.message}` };
  }

  try {
    // Partner subscriptions first; they never touch profiles.
    {
      const obj = stripeEvent.data.object || {};
      const orgId = partnerOrgId(obj);
      if (stripeEvent.type === 'checkout.session.completed' && orgId) {
        if (obj.subscription) await syncPartner(await stripe.subscriptions.retrieve(obj.subscription), orgId);
        return { statusCode: 200, body: JSON.stringify({ received: true, partner: true }) };
      }
      if ((stripeEvent.type === 'customer.subscription.updated' || stripeEvent.type === 'customer.subscription.deleted') && orgId) {
        await syncPartner(stripeEvent.type === 'customer.subscription.deleted' ? { ...obj, status: 'canceled' } : obj, orgId);
        return { statusCode: 200, body: JSON.stringify({ received: true, partner: true }) };
      }
    }

    if (stripeEvent.type === 'checkout.session.completed') {
      const session = stripeEvent.data.object;
      const userId = session.client_reference_id || session.metadata?.supabase_user_id;
      if (!userId || !session.subscription) return { statusCode: 200, body: 'ignored' };

      const sub = await stripe.subscriptions.retrieve(session.subscription);
      const priceId = sub.items.data[0]?.price?.id;
      const { error } = await supabase.from('profiles').update({
        is_premium: activeStatus(sub.status),
        premium_tier: activeStatus(sub.status) ? tierFor(priceId) : null,
        premium_expires_at: periodEnd(sub) ? periodEnd(sub).toISOString() : null,
        stripe_customer_id: session.customer || null,
        stripe_subscription_id: sub.id,
      }).eq('id', userId);
      if (error) throw error;
    }

    if (stripeEvent.type === 'customer.subscription.updated') {
      const sub = stripeEvent.data.object;
      const isActive = activeStatus(sub.status);
      const priceId = sub.items.data[0]?.price?.id;
      const { error } = await supabase.from('profiles').update({
        is_premium: isActive,
        premium_tier: isActive ? tierFor(priceId) : null,
        premium_expires_at: periodEnd(sub) ? periodEnd(sub).toISOString() : null,
      }).eq('stripe_subscription_id', sub.id);
      if (error) throw error;
    }

    if (stripeEvent.type === 'customer.subscription.deleted') {
      const sub = stripeEvent.data.object;
      const { error } = await supabase.from('profiles').update({
        is_premium: false,
        premium_tier: null,
        premium_expires_at: null,
        stripe_subscription_id: null,
      }).eq('stripe_subscription_id', sub.id);
      if (error) throw error;
    }

    return { statusCode: 200, body: JSON.stringify({ received: true }) };
  } catch (err) {
    console.error('stripe-webhook error:', err);
    return { statusCode: 500, body: 'Webhook processing failed' };
  }
};
