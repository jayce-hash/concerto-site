// netlify/functions/revenuecat-webhook.js
//
// RevenueCat is the source of truth for subscription state; this
// endpoint keeps Supabase profiles.is_premium (and premium_tier /
// premium_expires_at) in lockstep, mirroring how stripe-webhook.js
// already syncs web signups. The app's existing profile-read code
// (useProfile, the Account screen, Bag Check / planner gating) needs
// zero changes: it just reads is_premium like it always has.
//
// SETUP (one time):
//   1. RevenueCat dashboard -> Project -> Integrations -> Webhooks
//      -> add this function's deployed URL.
//   2. In that same screen, set an "Authorization header value" --
//      any long random string you generate. Put the SAME string in
//      Netlify as REVENUECAT_WEBHOOK_SECRET.
//   3. Netlify also needs SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
//      (the same ones delete-account.js already uses).
//   4. app_user_id must equal the Supabase user's UUID: the app
//      calls Purchases.logIn(supabaseUserId) at Account mount
//      (src/lib/purchases.ts), so this is already wired correctly.

const { createClient } = require('@supabase/supabase-js');

const ACTIVE_EVENTS = new Set(['INITIAL_PURCHASE', 'RENEWAL', 'UNCANCELLATION', 'PRODUCT_CHANGE']);
const INACTIVE_EVENTS = new Set(['CANCELLATION', 'EXPIRATION', 'BILLING_ISSUE']);

exports.handler = async function (event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  const auth = event.headers.authorization || event.headers.Authorization || '';
  const expected = process.env.REVENUECAT_WEBHOOK_SECRET || '';
  if (!expected || (auth !== `Bearer ${expected}` && auth !== expected)) {
    return { statusCode: 401, body: 'Unauthorized' };
  }

  let payload;
  try {
    payload = JSON.parse(event.body).event;
  } catch {
    return { statusCode: 400, body: 'Bad payload' };
  }

  const userId = payload && payload.app_user_id;
  const type = payload && payload.type;
  if (!userId || (!ACTIVE_EVENTS.has(type) && !INACTIVE_EVENTS.has(type))) {
    // Other event types (TEST, TRANSFER, NON_RENEWING_PURCHASE, etc.)
    // are safely ignored: acknowledge so RevenueCat doesn't retry.
    return { statusCode: 200, body: 'ignored' };
  }

  try {
    const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const isActive = ACTIVE_EVENTS.has(type);
    const tier = String(payload.product_id || '').toLowerCase().includes('annual') ? 'annual' : 'monthly';
    const expiresAt = payload.expiration_at_ms ? new Date(payload.expiration_at_ms).toISOString() : null;

    const { error } = await supabase
      .from('profiles')
      .update({
        is_premium: isActive,
        premium_tier: isActive ? tier : null,
        premium_expires_at: expiresAt,
      })
      .eq('id', userId);

    if (error) throw error;
    return { statusCode: 200, body: 'ok' };
  } catch (err) {
    console.error('revenuecat-webhook error:', err);
    return { statusCode: 500, body: 'db update failed' };
  }
};
