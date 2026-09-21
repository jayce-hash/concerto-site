// netlify/functions/report.js
// POST { venue, tour, event, field, message, surface } → one row in info_reports.
// This is the accuracy network: a fan who sees a wrong bag rule at the gate tells us in one
// tap, and that venue moves to the front of the re-verification queue.
const { createClient } = require('@supabase/supabase-js');
const H = { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'POST, OPTIONS' };
const FIELDS = new Set(['bagPolicy','parking','rideshare','concessions','accessibility','reEntry','ticketPickup','gates','showTime','doors','headliner','setlist','distance','weather','other']);
exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: H, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: H, body: '' };
  try {
    const b = JSON.parse(event.body || '{}');
    const field = FIELDS.has(b.field) ? b.field : 'other';
    const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    await sb.from('info_reports').insert({
      venue_slug: String(b.venue || '').slice(0, 120) || null, tour_slug: String(b.tour || '').slice(0, 160) || null, tm_event_id: String(b.event || '').slice(0, 80) || null,
      field, message: String(b.message || '').slice(0, 240) || null, surface: ['app', 'web', 'console'].includes(b.surface) ? b.surface : 'app', device_hash: String(b.device || '').slice(0, 64) || null,
    });
    return { statusCode: 200, headers: H, body: '{"ok":true}' };
  } catch { return { statusCode: 200, headers: H, body: '{"ok":false}' }; }
};
