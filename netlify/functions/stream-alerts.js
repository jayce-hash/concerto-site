// netlify/functions/stream-alerts.js
//
// One alert, free for everyone: a fan stream has been listed in Medley for a tour or an artist
// you favorited in Concerto. It goes to Concerto, because that is where the favorite lives and
// where the alert switch is (Settings, Notifications, Fan Streams).
//
// A stream is listed when you approve it in the medley_streams table. This runs twice a day
// (netlify.toml) and looks only at approved streams starting in the next 18 hours, so a fan
// hears on the day and never days ahead. medley_stream_alerts holds one row per stream and
// fan, so nobody is ever told about the same stream twice, however often this runs.
//
// The alert names no time: the server does not know the fan's time zone, and Medley shows the
// start in the phone's own time. Tapping it opens Medley's Streams tab, or the stream itself
// when Medley is not on the phone.
//
// ALERTS_DRY_RUN: the same switch as alerts-poll. Anything but "false" sends nothing and logs
// what it would have sent, without marking anyone as told.
const fs = require('fs');
const path = require('path');

const DRY_RUN = process.env.ALERTS_DRY_RUN !== 'false';
const AHEAD_MS = 18 * 3600 * 1000;
const STARTED_MS = 60 * 60 * 1000;   // a stream that began up to an hour ago still counts
const STREAM_URL = /^https:\/\/(www\.)?(tiktok|instagram|youtube)\.com\//;

/** No accents, lower case, single spaces: how an artist is compared everywhere in the family. */
const plain = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

function readTours() {
  for (const p of [path.join(process.cwd(), 'data/tours.json'), path.join(__dirname, '../../data/tours.json')]) {
    try { const j = JSON.parse(fs.readFileSync(p, 'utf8')); return Array.isArray(j) ? j : j.tours || []; } catch {}
  }
  return [];
}

/** The plain artist names a fan has favorited, through a tour or directly. */
function favoriteArtists(profile, tourArtist) {
  const out = new Set();
  for (const a of profile.favorite_artists || []) { const k = plain(a); if (k) out.add(k); }
  for (const t of profile.favorite_tours || []) { const k = tourArtist.get(String(t).toLowerCase().trim()); if (k) out.add(k); }
  return out;
}

/** Which fans to tell about which stream. Pure, so it can be checked without a database. */
function plan(streams, profiles, tours, told, now) {
  const tourArtist = new Map();
  const named = new Map();   // the artist's name as Concerto writes it, for the alert
  for (const t of tours) {
    const k = plain(t.artist);
    if (!k) continue;
    named.set(k, t.artist);
    if (t.tourId) tourArtist.set(String(t.tourId).toLowerCase().trim(), k);
    if (t.tourName) tourArtist.set(String(t.tourName).toLowerCase().trim(), k);
  }
  const fans = profiles
    .filter((p) => p.notif_prefs?.streams !== false)
    .map((p) => ({ id: p.id, artists: favoriteArtists(p, tourArtist) }))
    .filter((p) => p.artists.size);
  const done = new Set(told.map((r) => `${r.stream_id}|${r.user_id}`));
  const out = [];
  for (const s of streams) {
    const start = Date.parse(s.starts_at);
    if (!Number.isFinite(start) || start > now + AHEAD_MS || start < now - STARTED_MS) continue;
    const k = plain(s.artist);
    // The streamer is never told about their own stream.
    const users = fans.filter((f) => f.artists.has(k) && f.id !== s.user_id && !done.has(`${s.id}|${f.id}`)).map((f) => f.id);
    if (users.length) out.push({ stream: { ...s, artist: named.get(k) || s.artist }, users });
  }
  return out;
}

function message(stream) {
  const venue = String(stream.venue || '').trim();
  return {
    title: `${stream.artist}: a fan is streaming`,
    body: `${venue ? `From ${venue}. ` : ''}See when it starts and watch from Medley.`,
    data: { url: '/tours', open: 'medley://streams', ...(STREAM_URL.test(stream.url || '') ? { fallback: stream.url } : {}) },
  };
}

async function sendPush(tokens, msg) {
  let sent = 0;
  for (let i = 0; i < tokens.length; i += 100) {
    const batch = tokens.slice(i, i + 100).map((to) => ({ to, title: msg.title, body: msg.body, sound: 'default', data: msg.data }));
    const res = await fetch('https://exp.host/--/api/v2/push/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(batch) });
    if (res.ok) sent += batch.length;
  }
  return sent;
}

exports._test = { plan, message, plain };

exports.handler = async function () {
  const summary = { dryRun: DRY_RUN, streams: 0, fans: 0, sent: 0, errors: [] };
  try {
    const { createClient } = require('@supabase/supabase-js');
    const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const now = Date.now();
    const { data: streams, error: sErr } = await supabase.from('medley_streams')
      .select('id,user_id,artist,venue,starts_at,url')
      .eq('status', 'approved')
      .gte('starts_at', new Date(now - STARTED_MS).toISOString())
      .lte('starts_at', new Date(now + AHEAD_MS).toISOString());
    if (sErr) throw new Error(sErr.message);
    if (!streams || !streams.length) { console.log('stream-alerts', JSON.stringify(summary)); return { statusCode: 200, body: JSON.stringify(summary) }; }

    const { data: profiles, error: pErr } = await supabase.from('profiles').select('id,favorite_artists,favorite_tours,notif_prefs');
    if (pErr) throw new Error(pErr.message);
    const { data: told, error: tErr } = await supabase.from('medley_stream_alerts').select('stream_id,user_id').in('stream_id', streams.map((s) => s.id));
    if (tErr) throw new Error(tErr.message);

    for (const { stream, users } of plan(streams, profiles || [], readTours(), told || [], now)) {
      summary.streams += 1;
      summary.fans += users.length;
      if (DRY_RUN) continue;
      // Mark first: if the send then fails, a fan misses one alert, which is better than two.
      const { error: logErr } = await supabase.from('medley_stream_alerts').upsert(users.map((user_id) => ({ stream_id: stream.id, user_id })), { onConflict: 'stream_id,user_id', ignoreDuplicates: true });
      if (logErr) { summary.errors.push(`log:${logErr.message.slice(0, 100)}`); continue; }
      const { data: rows } = await supabase.from('push_tokens').select('token').in('user_id', users);
      const tokens = (rows || []).map((r) => r.token).filter((t) => t && /^(ExponentPushToken|ExpoPushToken)/.test(t));
      summary.sent += await sendPush(tokens, message(stream));
    }
  } catch (e) {
    summary.errors.push(String(e && e.message || e).slice(0, 160));
  }
  console.log('stream-alerts', JSON.stringify(summary));
  return { statusCode: summary.errors.length ? 500 : 200, body: JSON.stringify(summary) };
};
