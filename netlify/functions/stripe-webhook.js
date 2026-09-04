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
    if (stripeEvent.type === 'checkout.session.completed') {
      const session = stripeEvent.data.object;
      const userId = session.client_reference_id || session.metadata?.supabase_user_id;
      if (!userId || !session.subscription) return { statusCode: 200, body: 'ignored' };

      const sub = await stripe.subscriptions.retrieve(session.subscription);
      const priceId = sub.items.data[0]?.price?.id;
      const { error } = await supabase.from('profiles').update({
        is_premium: activeStatus(sub.status),
        premium_tier: activeStatus(sub.status) ? tierFor(priceId) : null,
        premium_expires_at: sub.current_period_end ? new Date(sub.current_period_end * 1000).toISOString() : null,
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
        premium_expires_at: sub.current_period_end ? new Date(sub.current_period_end * 1000).toISOString() : null,
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
