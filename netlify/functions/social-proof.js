// netlify/functions/social-proof.js
//
// Tier 3 social proof: "N fans saved this show", aggregated from your
// own first-party analytics (show_saved events, last 90 days). Reads
// with the service key server-side, so the insert-only RLS on
// analytics_events stays intact. Results cached at the edge for an
// hour; counts under the threshold are omitted entirely, because
// "1 fan saved this" is worse than silence.
//
// GET /.netlify/functions/social-proof?names=Event%20One|Event%20Two
// -> { "event one": 14, "event two": 6 }   (keys lowercased)

const { createClient } = require('@supabase/supabase-js');
const THRESHOLD = 3;

exports.handler = async function (event) {
  const namesParam = (event.queryStringParameters || {}).names || '';
  const names = namesParam.split('|').map((n) => n.trim()).filter(Boolean).slice(0, 40);
  if (!names.length) return { statusCode: 400, body: JSON.stringify({ error: 'names required' }) };

  try {
    const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const since = new Date(Date.now() - 90 * 86400000).toISOString();
    const { data, error } = await supabase
      .from('analytics_events')
      .select('props')
      .eq('event', 'show_saved')
      .gte('created_at', since)
      .limit(20000);
    if (error) throw error;

    const wanted = new Set(names.map((n) => n.toLowerCase()));
    const counts = {};
    for (const row of data || []) {
      const name = String(row.props?.event || '').toLowerCase();
      if (wanted.has(name)) counts[name] = (counts[name] || 0) + 1;
    }
    for (const k of Object.keys(counts)) if (counts[k] < THRESHOLD) delete counts[k];

    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=3600',
      },
      body: JSON.stringify(counts),
    };
  } catch (err) {
    console.error('social-proof error:', err);
    return { statusCode: 500, body: JSON.stringify({ error: 'aggregation failed' }) };
  }
};
