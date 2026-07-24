// netlify/functions/delete-account.js
// In-app account deletion (App Store Guideline 5.1.1(v) requirement).
// POST with the user's Supabase Bearer token. Verifies the session,
// deletes the profile row, then deletes the auth user.

const { createClient } = require('@supabase/supabase-js');

exports.handler = async function (event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ error: 'Method Not Allowed' }) };
  }
  const authHeader = event.headers.authorization || event.headers.Authorization || '';
  const token = authHeader.replace(/^Bearer\s+/i, '').trim();
  if (!token) {
    return { statusCode: 401, body: JSON.stringify({ error: 'Authentication required' }) };
  }
  try {
    const supabase = createClient(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_SERVICE_ROLE_KEY,
    );
    const { data: { user }, error } = await supabase.auth.getUser(token);
    if (error || !user) {
      return { statusCode: 401, body: JSON.stringify({ error: 'Invalid session' }) };
    }
    await supabase.from('profiles').delete().eq('id', user.id);
    const { error: delErr } = await supabase.auth.admin.deleteUser(user.id);
    if (delErr) throw delErr;
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deleted: true }),
    };
  } catch (err) {
    console.error('delete-account error:', err);
    return { statusCode: 500, body: JSON.stringify({ error: 'Deletion failed' }) };
  }
};
