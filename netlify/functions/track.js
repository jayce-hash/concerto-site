// netlify/functions/track.js
// Logs a placement tap (Top Pick engagement) to Supabase. Fire-and-forget from the City Guide.
import { createClient } from '@supabase/supabase-js';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function handler(event) {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: CORS, body: '' };
  if (event.httpMethod !== 'POST')   return { statusCode: 405, headers: CORS, body: 'Method Not Allowed' };
  try {
    const { trackingId, event: ev } = JSON.parse(event.body || '{}');
    if (trackingId) {
      const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
      await supabase.from('placement_taps').insert({
        tracking_id: String(trackingId).slice(0, 200),
        event: String(ev || 'open').slice(0, 40),
      });
    }
  } catch (e) { /* analytics must never error the client */ }
  return { statusCode: 204, headers: CORS, body: '' };
}
