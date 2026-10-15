// RevenueCat -> Supabase entitlement synchronization.
// profiles.is_premium remains the shared entitlement read used by app + web.
// IMPORTANT: cancellation and billing-issue events do NOT mean access expired.
// RevenueCat sends EXPIRATION when entitlement access should be removed.

const { createClient } = require('@supabase/supabase-js');

const GRANT_EVENTS = new Set([
  'INITIAL_PURCHASE',
  'RENEWAL',
  'UNCANCELLATION',
  'SUBSCRIPTION_EXTENDED',
  'REFUND_REVERSED',
  'TEMPORARY_ENTITLEMENT_GRANT',
]);
const KEEP_EVENTS = new Set([
  'CANCELLATION',
  'BILLING_ISSUE',
  'SUBSCRIPTION_PAUSED',
  'PRODUCT_CHANGE',
]);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function tierFor(productId) {
  const p = String(productId || '').toLowerCase();
  return p.includes('annual') || p.includes('year') ? 'annual' : 'monthly';
}
function iso(ms) {
  return Number(ms) > 0 ? new Date(Number(ms)).toISOString() : null;
}
function premiumEvent(e) {
  // Older/sample events may omit entitlement_ids. When present, never let an
  // unrelated RevenueCat product alter Concerto+.
  return !Array.isArray(e.entitlement_ids) || e.entitlement_ids.length === 0 || e.entitlement_ids.includes('premium');
}

exports.handler = async function (event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method Not Allowed' };

  const auth = event.headers.authorization || event.headers.Authorization || '';
  const expected = process.env.REVENUECAT_WEBHOOK_SECRET || '';
  if (!expected || (auth !== `Bearer ${expected}` && auth !== expected)) {
    return { statusCode: 401, body: 'Unauthorized' };
  }

  let payload;
  try { payload = JSON.parse(event.body || '{}').event; }
  catch { return { statusCode: 400, body: 'Bad payload' }; }
  if (!payload || !payload.type) return { statusCode: 400, body: 'Bad payload' };
  if (!premiumEvent(payload)) return { statusCode: 200, body: 'ignored' };

  const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  const type = payload.type;

  try {
    // A transfer removes entitlement from the old Concerto account and moves it
    // to the destination account. Copy known tier/expiry before revoking source.
    if (type === 'TRANSFER') {
      const from = (payload.transferred_from || []).filter((id) => UUID.test(id));
      const to = (payload.transferred_to || []).filter((id) => UUID.test(id));
      let prior = null;
      if (from.length) {
        const { data } = await supabase
          .from('profiles')
          .select('premium_tier,premium_expires_at')
          .in('id', from)
          .eq('is_premium', true)
          .limit(1);
        prior = data && data[0];
        const { error } = await supabase.from('profiles').update({
          is_premium: false,
          premium_tier: null,
          premium_expires_at: null,
        }).in('id', from);
        if (error) throw error;
      }
      if (to.length) {
        const { error } = await supabase.from('profiles').update({
          is_premium: true,
          ...(prior?.premium_tier ? { premium_tier: prior.premium_tier } : {}),
          ...(prior?.premium_expires_at ? { premium_expires_at: prior.premium_expires_at } : {}),
        }).in('id', to);
        if (error) throw error;
      }
      return { statusCode: 200, body: 'ok' };
    }

    const userId = payload.app_user_id;
    if (!userId || !UUID.test(userId)) return { statusCode: 200, body: 'ignored' };

    if (type === 'EXPIRATION') {
      const { error } = await supabase.from('profiles').update({
        is_premium: false,
        premium_tier: null,
        premium_expires_at: iso(payload.expiration_at_ms),
      }).eq('id', userId);
      if (error) throw error;
      return { statusCode: 200, body: 'ok' };
    }

    if (GRANT_EVENTS.has(type)) {
      const expiresAt = iso(payload.grace_period_expiration_at_ms) || iso(payload.expiration_at_ms);
      const { error } = await supabase.from('profiles').update({
        is_premium: true,
        premium_tier: tierFor(payload.product_id),
        premium_expires_at: expiresAt,
      }).eq('id', userId);
      if (error) throw error;
      return { statusCode: 200, body: 'ok' };
    }

    if (KEEP_EVENTS.has(type)) {
      // Preserve current access. Cancellation means auto-renew is off;
      // billing issue can still be in grace; product change can be deferred.
      // We may safely refresh the known end/grace date without flipping access.
      const expiresAt = iso(payload.grace_period_expiration_at_ms) || iso(payload.expiration_at_ms);
      if (expiresAt) {
        const { error } = await supabase.from('profiles')
          .update({ premium_expires_at: expiresAt })
          .eq('id', userId);
        if (error) throw error;
      }
      return { statusCode: 200, body: 'ok' };
    }

    return { statusCode: 200, body: 'ignored' };
  } catch (err) {
    console.error('revenuecat-webhook error:', err);
    return { statusCode: 500, body: 'db update failed' };
  }
};
