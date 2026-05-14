// ─────────────────────────────────────────
// STRIPE WEBHOOK HANDLER
// Deploy as a Supabase Edge Function or Vercel/Netlify serverless function
// File: /api/stripe-webhook.js
// ─────────────────────────────────────────

import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // service role — bypasses RLS
);

export default async function handler(req, res) {
  const sig = req.headers['stripe-signature'];
  let event;

  try {
    event = stripe.webhooks.constructEvent(
      req.body, sig, process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    return res.status(400).send(`Webhook error: ${err.message}`);
  }

  switch (event.type) {

    case 'checkout.session.completed': {
      const session = event.data.object;
      const customerId = session.customer;
      const subscriptionId = session.subscription;
      // client_reference_id is the Supabase user ID passed from startCheckout()
      const userId = session.client_reference_id || session.metadata?.supabase_user_id;

      if (!userId) {
        console.error('No user ID in checkout session — cannot upgrade profile');
        break;
      }

      // Fetch subscription to get tier
      const sub = await stripe.subscriptions.retrieve(subscriptionId);
      const priceId = sub.items.data[0].price.id;
      const tier = priceId === process.env.STRIPE_PRICE_ANNUAL ? 'annual' : 'monthly';
      const expiresAt = new Date(sub.current_period_end * 1000).toISOString();

      await supabase.from('profiles').update({
        is_premium: true,
        premium_tier: tier,
        premium_expires_at: expiresAt,
        stripe_customer_id: customerId,
        stripe_subscription_id: subscriptionId,
      }).eq('id', userId);
      break;
    }

    case 'customer.subscription.updated': {
      const sub = event.data.object;
      const expiresAt = new Date(sub.current_period_end * 1000).toISOString();
      const isActive = ['active', 'trialing'].includes(sub.status);
      const priceId = sub.items.data[0].price.id;
      const tier = priceId === process.env.STRIPE_PRICE_ANNUAL ? 'annual' : priceId === process.env.STRIPE_PRICE_MONTHLY ? 'monthly' : 'monthly';

      await supabase.from('profiles').update({
        is_premium: isActive,
        premium_tier: isActive ? tier : null,
        premium_expires_at: expiresAt,
      }).eq('stripe_subscription_id', sub.id);
      break;
    }

    case 'customer.subscription.deleted': {
      const sub = event.data.object;
      await supabase.from('profiles').update({
        is_premium: false,
        premium_tier: null,
        stripe_subscription_id: null,
      }).eq('stripe_subscription_id', sub.id);
      break;
    }
  }

  res.json({ received: true });
}
