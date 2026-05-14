// netlify/functions/check-premium.js
// Verifies a Supabase JWT and returns premium status

import { createClient } from '@supabase/supabase-js';

export async function handler(event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  const authHeader = event.headers.authorization || '';
  const token = authHeader.replace('Bearer ', '').trim();

  if (!token) {
    return { statusCode: 401, body: JSON.stringify({ premium: false, reason: 'no_token' }) };
  }

  try {
    const supabase = createClient(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_SERVICE_ROLE_KEY
    );

    const { data: { user }, error } = await supabase.auth.getUser(token);
    if (error || !user) {
      return { statusCode: 401, body: JSON.stringify({ premium: false, reason: 'invalid_token' }) };
    }

    const { data: profile } = await supabase
      .from('profiles')
      .select('is_premium, premium_tier, premium_expires_at')
      .eq('id', user.id)
      .single();

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        premium: profile?.is_premium || false,
        tier: profile?.premium_tier || null,
        expires: profile?.premium_expires_at || null,
        user_id: user.id,
        email: user.email,
      })
    };
  } catch (err) {
    console.error('check-premium error:', err);
    return { statusCode: 500, body: JSON.stringify({ premium: false, reason: 'error' }) };
  }
}
