// netlify/functions/alerts-poll.js
//
// The one alert type that needs a server, because it's about
// something a fan doesn't know yet -- a new tour announcement can't
// be scheduled ahead of time the way "doors in 2 hours" can, since
// there's nothing to count down to until it exists.
//
// Two passes, both Concerto+ only, both governed by profiles.notif_prefs
// (the server-readable mirror of the local toggles -- see
// migration-onsale-alerts.sql for why that had to exist):
//
//   A. New tour dates for artists a premium user follows
//   B. Presale/onsale timing for shows a premium user already saved
//
// And one pass that is free for everyone, because it is the difference between a saved show
// being right and being wrong:
//
//   C. A saved show changed: new time, new date, postponed, or cancelled
//
// Runs on a schedule (netlify.toml, every 6 hours, not an in-file
// config export -- this function uses the classic exports.handler
// style, and Netlify's schedule-via-config only works for the newer
// ESM export-default function style). Every send is idempotent through onsale_alert_log's primary key on
// (event_id, alert_type) -- a retry, a double-trigger, or a crash
// mid-run can never produce two alerts for the same thing.
//
// This is a Netlify BACKGROUND function (the -background suffix in
// the filename is what tells Netlify's build system to treat it that
// way), not a standard one. First deploy used a standard function and
// it hit Netlify's ~30-second execution ceiling on the very first
// real run -- with no favorited artists yet, Pass A does nothing, but
// the zero-results check at the bottom was making up to 78 sequential
// Ticketmaster calls, one per tour, and that alone blew past the
// limit. Background functions get up to 15 minutes, which is what
// scheduled work with no caller waiting on a response actually needs.
//
// One real tradeoff: background functions return their HTTP response
// immediately (a bare 202, before any real work happens) rather than
// waiting for the handler to finish and sending its return value back
// -- Netlify's whole point is "acknowledge receipt, then work in the
// background." So the summary object is no longer something you'd see
// in a curl response; it's logged instead, visible in Netlify's
// function invocation logs under this function's name.
//
// Also batched the Ticketmaster calls in groups of 5 rather than
// fully sequential, which cuts wall-clock time considerably and is
// still gentle enough not to trip Ticketmaster's own rate limits.
//
// SETUP: Netlify env vars ->
//   ALERTS_DRY_RUN            "false" to actually send. Any other
//                             value, or unset, means dry run -- this
//                             defaults safe on purpose, since a
//                             scheduled function firing bad pushes to
//                             real people is a much worse failure mode
//                             than a missed alert.
//   TICKETMASTER_API_KEY (or TM_API_KEY)   already set for tm.js
//   SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY   already set for other fns

const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

const TM_BASE = 'https://app.ticketmaster.com/discovery/v2';
const DRY_RUN = process.env.ALERTS_DRY_RUN !== 'false';

function tmKey() {
  const key = process.env.TICKETMASTER_API_KEY || process.env.TM_API_KEY;
  if (!key) throw new Error('TM key not configured');
  return key;
}

async function tmSearchByArtist(artist) {
  const now = new Date();
  const end = new Date(now.getTime() + 240 * 86400000);
  const params = new URLSearchParams({
    apikey: tmKey(),
    keyword: artist,
    classificationName: 'Music',
    size: '20',
    sort: 'date,asc',
    startDateTime: now.toISOString().split('.')[0] + 'Z',
    endDateTime: end.toISOString().split('.')[0] + 'Z',
  });
  const res = await fetch(`${TM_BASE}/events.json?${params}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data._embedded?.events ?? [];
}

async function tmGetEvent(eventId) {
  const params = new URLSearchParams({ apikey: tmKey() });
  const res = await fetch(`${TM_BASE}/events/${eventId}.json?${params}`);
  if (!res.ok) return null;
  return res.json();
}

// Runs `items` through `worker` in batches of `size` concurrently,
// rather than either fully sequential (slow, exactly what timed out
// the first run) or one giant Promise.all (risks tripping
// Ticketmaster's rate limit if `items` is large, e.g. every tour with
// zero favoriters yet).
async function inBatches(items, size, worker) {
  for (let i = 0; i < items.length; i += size) {
    await Promise.all(items.slice(i, i + size).map(worker));
  }
}

function savedEventTime(raw) {
  if (!raw) return Number.NaN;
  // A date-only Ticketmaster value represents the event's calendar day, not
  // UTC midnight. Keep it eligible through that day so US time zones do not
  // make the event look expired the prior evening.
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return Date.parse(`${raw}T23:59:59Z`);
  return new Date(raw).getTime();
}

// ---- Pass C helpers: what Ticketmaster says now, against what a fan saved ----
function timeLabel(localTime) {
  if (!localTime) return '';
  const [h, m] = localTime.split(':').map(Number);
  if (!Number.isFinite(h) || !Number.isFinite(m)) return '';
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`;
}
function liveShow(tmEvent) {
  const st = tmEvent?.dates?.start || {};
  const code = String(tmEvent?.dates?.status?.code || '').toLowerCase();
  const hour = st.localTime ? Number(st.localTime.split(':')[0]) : NaN;
  // Same rule as the app: a flagged TBA, or a placeholder time before 6 AM, is no time at all.
  const noTime = Boolean(st.timeTBA || st.noSpecificTime || st.dateTBA || st.dateTBD) || !st.localTime || (Number.isFinite(hour) && hour < 6);
  return {
    status: code === 'cancelled' || code === 'canceled' ? 'cancelled' : code === 'postponed' ? 'postponed' : 'on',
    day: st.localDate || '',
    time: noTime ? '' : timeLabel(st.localTime),
    timezone: tmEvent?.dates?.timezone || '',
  };
}
function savedDay(saved, timezone) {
  const raw = String(saved?.date || '');
  if (!/[zZ]$|[+-]\d{2}:\d{2}$/.test(raw)) return raw.slice(0, 10); // already a local date
  try { return new Intl.DateTimeFormat('en-CA', { timeZone: timezone || saved.timezone || 'UTC', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(raw)); }
  catch { return raw.slice(0, 10); }
}
function dayWords(day) {
  try { return new Date(`${day}T12:00:00Z`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' }); }
  catch { return day; }
}
// Returns null when the saved copy is still right. A time that was simply announced (the saved
// copy had none) is not a change worth an alert; the app fills it in quietly.
function describeChange(saved, live) {
  if (live.status === 'cancelled') {
    if (saved.status === 'cancelled') return null;
    return { key: 'changed:cancelled', title: 'cancelled', body: () => 'Ticketmaster now lists this show as cancelled. Check with your ticket seller about refunds.' };
  }
  if (live.status === 'postponed') {
    if (saved.status === 'postponed') return null;
    return { key: 'changed:postponed', title: 'postponed', body: () => 'Ticketmaster now lists this show as postponed. Your Night updates when a new date is set.' };
  }
  const was = savedDay(saved, live.timezone);
  if (live.day && was && live.day !== was) {
    return { key: `changed:date:${live.day}`, title: 'new date', body: (venue) => `Now ${dayWords(live.day)}${live.time ? ` at ${live.time}` : ''} at ${venue}. It was ${dayWords(was)}.` };
  }
  const savedTime = saved.timeTBA ? '' : String(saved.doors || '');
  if (live.time && savedTime && live.time !== savedTime) {
    return { key: `changed:time:${live.day}:${live.time}`, title: 'new show time', body: (venue) => `Now ${live.time} at ${venue}. It was ${savedTime}. Your Night has the new times.` };
  }
  return null;
}

function eventDoorsLine(tmEvent) {
  const venue = tmEvent._embedded?.venues?.[0];
  const name = tmEvent.name || 'A show';
  const venueName = venue?.name || 'the venue';
  return `${name} at ${venueName}`;
}

// Expo accepts batches of up to 100; this mirrors push-send.js's own
// batching rather than importing it, since that function is written
// as an HTTP handler, not a reusable module.
async function sendPush(tokens, title, body, url) {
  if (DRY_RUN) return { sent: 0, dryRun: true, recipients: tokens.length };
  let sent = 0;
  for (let i = 0; i < tokens.length; i += 100) {
    const batch = tokens.slice(i, i + 100).map((to) => ({
      to, title, body, sound: 'default', data: url ? { url } : {},
    }));
    const res = await fetch('https://exp.host/--/api/v2/push/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(batch),
    });
    if (res.ok) sent += batch.length;
  }
  return { sent, dryRun: false, recipients: tokens.length };
}

exports._test = { liveShow, describeChange, savedDay };

exports.handler = async function () {
  const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  const summary = { dryRun: DRY_RUN, newTourDates: 0, presaleAlerts: 0, showChanges: 0, staleArtists: [], errors: [] };

  // Only premium users with the onsale toggle on (or unset, which
  // defaults true) count for either pass. A user who has never
  // touched the toggle has no notif_prefs row content for it yet, so
  // missing key means enabled, matching the client's own default.
  const { data: profiles, error: profErr } = await supabase
    .from('profiles')
    .select('id, favorite_artists, saved_events, notif_prefs')
    .eq('is_premium', true);
  if (profErr) {
    return { statusCode: 500, body: JSON.stringify({ error: profErr.message }) };
  }

  const onsaleEnabled = (p) => p.notif_prefs?.onsale !== false;
  const eligible = (profiles || []).filter(onsaleEnabled);

  // ---- Pass A: new tour dates for followed artists -------------------
  const artistToUsers = new Map();
  for (const p of eligible) {
    for (const artist of p.favorite_artists ?? []) {
      if (!artistToUsers.has(artist)) artistToUsers.set(artist, []);
      artistToUsers.get(artist).push(p.id);
    }
  }

  await inBatches([...artistToUsers.keys()], 5, async (artist) => {
    const userIds = artistToUsers.get(artist);
    try {
      const events = await tmSearchByArtist(artist);
      if (!events.length) {
        summary.staleArtists.push(artist);
        return;
      }

      const { data: alreadySeenRows } = await supabase
        .from('tm_seen_events')
        .select('event_id')
        .eq('artist', artist);
      const alreadySeen = new Set((alreadySeenRows ?? []).map((r) => r.event_id));
      const everPolled = alreadySeen.size > 0;

      const newIds = events.map((e) => e.id).filter((id) => !alreadySeen.has(id));

      // Record every event as seen regardless of whether this is the
      // baseline poll or a later one -- next cycle's diff depends on
      // this being complete.
      if (events.length && !DRY_RUN) {
        await supabase.from('tm_seen_events').upsert(
          events.map((e) => ({ event_id: e.id, artist })),
          { onConflict: 'event_id', ignoreDuplicates: true },
        );
      }

      // First time we've ever polled this artist: that's a baseline,
      // not a wave of new announcements. Don't alert on it.
      if (!everPolled) return;

      for (const id of newIds) {
        const tmEvent = events.find((e) => e.id === id);
        if (!tmEvent) continue;

        if (!DRY_RUN) {
          const { error: logErr } = await supabase
            .from('onsale_alert_log')
            .insert({ event_id: id, alert_type: 'new_tour_date' });
          if (logErr) continue; // already alerted (or a race lost), skip silently
        }

        const targetUsers = artistToUsers.get(artist) ?? [];
        const { data: tokenRows } = await supabase
          .from('push_tokens')
          .select('token')
          .in('user_id', targetUsers);
        const tokens = (tokenRows ?? [])
          .map((r) => r.token)
          .filter((t) => t && /^(ExponentPushToken|ExpoPushToken)/.test(t));

        await sendPush(
          tokens,
          `${artist}: new date announced`,
          eventDoorsLine(tmEvent),
          '/tours',
        );
        summary.newTourDates += 1;
      }
    } catch (e) {
      summary.errors.push(`artist:${artist}:${String(e).slice(0, 120)}`);
    }
  });

  // ---- Pass B: presale/onsale timing for already-saved shows --------
  // Still sequential, not batched like Pass A above. Fine for now --
  // this scales with "premium users' upcoming saved shows," which is
  // near zero today -- but if it ever becomes the slow part as usage
  // grows, the same inBatches() treatment applies here too.
  const seenEventIdsThisRun = new Set();
  for (const p of eligible) {
    const saved = (p.saved_events ?? []).filter(
      (e) => e?.date && savedEventTime(e.date) > Date.now(),
    );
    for (const event of saved) {
      if (seenEventIdsThisRun.has(event.id)) continue; // one TM lookup per event per run, even if many users saved it
      seenEventIdsThisRun.add(event.id);

      try {
        if (!DRY_RUN) {
          const { error: logErr } = await supabase
            .from('onsale_alert_log')
            .insert({ event_id: event.id, alert_type: 'presale_timing' });
          if (logErr) continue; // already alerted
        }

        const tmEvent = await tmGetEvent(event.id);
        const presale = tmEvent?.sales?.presales?.[0]?.startDateTime;
        const onsale = tmEvent?.sales?.public?.startDateTime;
        const saleDate = presale || onsale;
        if (!saleDate || new Date(saleDate).getTime() <= Date.now()) {
          // Nothing to report, or it already started. Remove the log
          // row so a real future onsale for this event can still
          // alert later -- inserting it above was optimistic locking
          // against a concurrent run, not a claim that we found one.
          if (!DRY_RUN) {
            await supabase.from('onsale_alert_log')
              .delete()
              .match({ event_id: event.id, alert_type: 'presale_timing' });
          }
          continue;
        }

        // Every user (across all eligible profiles) who saved this
        // specific event gets this one, not just the first we found.
        const owners = eligible
          .filter((u) => (u.saved_events ?? []).some((e) => e.id === event.id))
          .map((u) => u.id);
        const { data: tokenRows } = await supabase
          .from('push_tokens')
          .select('token')
          .in('user_id', owners);
        const tokens = (tokenRows ?? [])
          .map((r) => r.token)
          .filter((t) => t && /^(ExponentPushToken|ExpoPushToken)/.test(t));

        const timeZone = tmEvent?.dates?.timezone;
        let when;
        try {
          when = new Date(saleDate).toLocaleString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric',
            hour: 'numeric', minute: '2-digit',
            ...(timeZone ? { timeZone } : {}),
          });
        } catch {
          when = new Date(saleDate).toISOString();
        }
        await sendPush(
          tokens,
          presale ? 'Presale starts soon' : 'Tickets go on sale soon',
          `${event.name}: ${when}, per Ticketmaster.`,
          event.venueSlug ? `/venue/${event.venueSlug}` : '/',
        );
        summary.presaleAlerts += 1;
      } catch (e) {
        summary.errors.push(`event:${event.id}:${String(e).slice(0, 120)}`);
      }
    }
  }

  // ---- Pass C: a saved show changed (free, every signed-in fan) --------
  // Shows in the next 60 days are looked up once each per run and compared with the copy
  // each fan saved. A fan is told once per change: the log key carries what changed, so the
  // same new time is never announced twice, but a second change still gets through.
  try {
    const { data: everyone, error: allErr } = await supabase
      .from('profiles')
      .select('id, saved_events, notif_prefs');
    if (allErr) throw allErr;
    const watchers = (everyone || []).filter((p) => p.notif_prefs?.showDay !== false && Array.isArray(p.saved_events) && p.saved_events.length);
    const horizon = Date.now() + 60 * 86400000;
    const byEvent = new Map(); // event id -> [{ userId, saved }]
    for (const p of watchers) {
      for (const e of p.saved_events) {
        const t = savedEventTime(e?.date);
        if (!e?.id || !Number.isFinite(t) || t < Date.now() || t > horizon) continue;
        if (!byEvent.has(e.id)) byEvent.set(e.id, []);
        byEvent.get(e.id).push({ userId: p.id, saved: e });
      }
    }
    await inBatches([...byEvent.keys()], 5, async (eventId) => {
      try {
        const tmEvent = await tmGetEvent(eventId);
        if (!tmEvent) return;
        const live = liveShow(tmEvent);
        const changed = byEvent.get(eventId)
          .map((o) => ({ ...o, change: describeChange(o.saved, live) }))
          .filter((o) => o.change);
        if (!changed.length) return;
        // One announcement per distinct change, to the fans whose saved copy is out of date.
        const groups = new Map();
        for (const o of changed) {
          if (!groups.has(o.change.key)) groups.set(o.change.key, { change: o.change, users: [], saved: o.saved });
          groups.get(o.change.key).users.push(o.userId);
        }
        for (const { change, users, saved } of groups.values()) {
          if (!DRY_RUN) {
            const { error: logErr } = await supabase
              .from('show_change_log')
              .insert({ event_id: eventId, change_key: change.key });
            if (logErr) continue; // already announced (or the log table isn't there yet: stay quiet)
          }
          const { data: tokenRows } = await supabase.from('push_tokens').select('token').in('user_id', users);
          const tokens = (tokenRows ?? []).map((r) => r.token).filter((t) => t && /^(ExponentPushToken|ExpoPushToken)/.test(t));
          const who = (saved.lineup && saved.lineup[0]) || saved.name || 'Your show';
          await sendPush(tokens, `${who}: ${change.title}`, change.body(saved.venueName || 'the venue'), `/show/${encodeURIComponent(eventId)}`);
          summary.showChanges += 1;
        }
      } catch (e) {
        summary.errors.push(`change:${eventId}:${String(e).slice(0, 120)}`);
      }
    });
  } catch (e) {
    summary.errors.push(`changes:${String(e).slice(0, 120)}`);
  }

  // ---- Zero-results check: tours that have quietly ended ------------
  // Folded into this same job since it's the same TM data already
  // being pulled, per artist, on the same schedule. Purely internal
  // signal, not user-facing -- just returned in the response for you
  // to glance at, not stored anywhere.
  try {
    const toursPath = path.join(__dirname, '..', '..', 'data', 'tours.json');
    const tours = JSON.parse(fs.readFileSync(toursPath, 'utf8'));
    const polledArtists = new Set(artistToUsers.keys());
    const toCheck = tours.filter((t) => !polledArtists.has(t.artist));
    // This loop alone is what blew the 30-second ceiling on a
    // standard function with an empty database: up to 78 sequential
    // Ticketmaster calls. Batched now, and running as a background
    // function besides, so there's real headroom on both sides.
    await inBatches(toCheck, 5, async (t) => {
      const events = await tmSearchByArtist(t.artist);
      if (!events.length) summary.staleArtists.push(t.artist);
    });
  } catch (e) {
    summary.errors.push(`stale-check:${String(e).slice(0, 120)}`);
  }

  // A background function's HTTP response is acknowledged before this
  // return value is ever seen by anyone -- the real result lives here,
  // in the logs, not in a response body nobody's listening for.
  console.log('alerts-poll summary:', JSON.stringify(summary));
  return { statusCode: 200, body: JSON.stringify(summary) };
};
