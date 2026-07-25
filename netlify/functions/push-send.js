// netlify/functions/push-send.js
//
// Tier 1 sender: pushes a notification to every registered device (or
// a filtered set) through Expo's push API. Protected by a shared
// secret so only you can trigger it.
//
// SETUP: Netlify env vars ->
//   PUSH_SEND_SECRET   any long random string you invent
//   SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (already set for other fns)
//
// USE (from your terminal, e.g. after a bag-policy verification pass):
//   curl -X POST https://concertocity.com/.netlify/functions/push-send \
//     -H "Authorization: Bearer YOUR_SECRET" \
//     -H "Content-Type: application/json" \
//     -d '{"title":"Bag policy updated","body":"Madison Square Garden re-verified its bag rules today.","url":"/venue/madison-square-garden"}'
//
// Optional body fields:
//   userIds: ["uuid", ...]  -> only those signed-in users' devices
//   dryRun: true            -> counts recipients without sending

const { createClient } = require('@supabase/supabase-js');

exports.handler = async function (event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method Not Allowed' };
  const auth = (event.headers.authorization || '').replace(/^Bearer\s+/i, '');
  if (!process.env.PUSH_SEND_SECRET || auth !== process.env.PUSH_SEND_SECRET) {
    return { statusCode: 401, body: 'Unauthorized' };
  }
  let body;
  try { body = JSON.parse(event.body); } catch { return { statusCode: 400, body: 'Bad JSON' }; }
  const { title, body: message, url, userIds, dryRun } = body || {};
  if (!title || !message) return { statusCode: 400, body: 'title and body required' };

  try {
    const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    let q = supabase.from('push_tokens').select('token');
    if (Array.isArray(userIds) && userIds.length) q = q.in('user_id', userIds);
    const { data: rows, error } = await q;
    if (error) throw error;
    const tokens = (rows || []).map((r) => r.token).filter((t) => t.startsWith('ExponentPushToken'));
    if (dryRun) return { statusCode: 200, body: JSON.stringify({ recipients: tokens.length, dryRun: true }) };

    // Expo accepts batches of up to 100 messages per request.
    let sent = 0;
    for (let i = 0; i < tokens.length; i += 100) {
      const batch = tokens.slice(i, i + 100).map((to) => ({
        to, title, body: message, sound: 'default', data: url ? { url } : {},
      }));
      const res = await fetch('https://exp.host/--/api/v2/push/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batch),
      });
      if (res.ok) sent += batch.length;
    }
    return { statusCode: 200, body: JSON.stringify({ recipients: tokens.length, sent }) };
  } catch (err) {
    console.error('push-send error:', err);
    return { statusCode: 500, body: 'send failed' };
  }
};
