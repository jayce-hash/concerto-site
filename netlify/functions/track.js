'use strict';
// netlify/functions/track.js
// Website partner counts. The app writes partner_impression / partner_tap straight to
// public.analytics_events; the website posts the same two events here, so each partner's
// monthly report (supabase/migration-partner-report-2026-10-15.sql) counts app and web together.
//
// Privacy (see /privacy): no account, no name, no location, no IP stored. The only id is a
// random one the browser keeps for itself, so repeat views from one browser can be told apart.
// Demo partners (ids starting "demo-") are never recorded.
const { createClient } = require('@supabase/supabase-js');
const { corsHeaders, limited } = require('./lib/guard');

const EVENTS = new Set(['partner_impression', 'partner_tap']);
const KEYS = ['venue', 'partner', 'partner_id', 'has_perk', 'surface', 'position', 'action'];
const clean = (v) => String(v == null ? '' : v).slice(0, 120);

exports.handler = async (event) => {
  const headers = corsHeaders(event, 'POST, OPTIONS');
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers, body: '' };
  // Analytics must never break the page: every path below answers 204.
  if (limited(event, 120, 60000)) return { statusCode: 204, headers, body: '' };
  try {
    const b = JSON.parse(event.body || '{}');
    const props = {};
    for (const k of KEYS) if (b.props && b.props[k] != null) props[k] = clean(b.props[k]);
    const ok = EVENTS.has(b.event) && props.partner_id && !/^demo-/.test(props.partner_id)
      && /^w_[a-z0-9]{6,40}$/.test(String(b.device_id || ''));
    if (ok && process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) {
      const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
      await sb.from('analytics_events').insert({ device_id: b.device_id, user_id: null, event: b.event, props, app_version: null, platform: 'web' });
    }
  } catch (_) { /* never surface */ }
  return { statusCode: 204, headers, body: '' };
};
