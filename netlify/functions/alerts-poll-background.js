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

exports.handler = async function () {
  const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  const summary = { dryRun: DRY_RUN, newTourDates: 0, presaleAlerts: 0, staleArtists: [], errors: [] };

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
      if (events.length) {
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

        const { error: logErr } = await supabase
          .from('onsale_alert_log')
          .insert({ event_id: id, alert_type: 'new_tour_date' });
        if (logErr) continue; // already alerted (or a race lost), skip silently

        const targetUsers = artistToUsers.get(artist) ?? [];
        const { data: tokenRows } = await supabase
          .from('push_tokens')
          .select('token')
          .in('user_id', targetUsers);
        const tokens = (tokenRows ?? [])
          .map((r) => r.token)
          .filter((t) => t && t.startsWith('ExponentPushToken'));

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
      (e) => e?.date && new Date(e.date).getTime() > Date.now(),
    );
    for (const event of saved) {
      if (seenEventIdsThisRun.has(event.id)) continue; // one TM lookup per event per run, even if many users saved it
      seenEventIdsThisRun.add(event.id);

      try {
        const { error: logErr } = await supabase
          .from('onsale_alert_log')
          .insert({ event_id: event.id, alert_type: 'presale_timing' });
        if (logErr) continue; // already alerted

        const tmEvent = await tmGetEvent(event.id);
        const presale = tmEvent?.sales?.presales?.[0]?.startDateTime;
        const onsale = tmEvent?.sales?.public?.startDateTime;
        const saleDate = presale || onsale;
        if (!saleDate || new Date(saleDate).getTime() <= Date.now()) {
          // Nothing to report, or it already started. Remove the log
          // row so a real future onsale for this event can still
          // alert later -- inserting it above was optimistic locking
          // against a concurrent run, not a claim that we found one.
          await supabase.from('onsale_alert_log')
            .delete()
            .match({ event_id: event.id, alert_type: 'presale_timing' });
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
          .filter((t) => t && t.startsWith('ExponentPushToken'));

        const when = new Date(saleDate).toLocaleString('en-US', {
          weekday: 'short', month: 'short', day: 'numeric',
          hour: 'numeric', minute: '2-digit',
        });
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
