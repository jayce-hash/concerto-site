# Concerto 2.2 -- Ship It

Everything built this round, in the order it actually has to deploy.
Database first, then the website (the alerts server lives there),
then the app. Each step depends on the one before it.

---

## 1. Run the migration

Open Supabase's SQL editor (not the terminal -- this runs against
your live database) and run `migrations-2.2.sql` in full. It's
idempotent: `ADD COLUMN IF NOT EXISTS` and `CREATE TABLE IF NOT
EXISTS` throughout, so running it twice by accident does nothing
harmful.

**What it adds:**
- `profiles.favorite_artists` -- the column the app's types already
  expected but never had
- `profiles.notif_prefs` -- the server-readable mirror of the alert
  toggles, defaults everything on
- `tm_seen_events` -- the "have we ever seen this event" ledger
- `onsale_alert_log` -- the "exactly one alert per event, ever" ledger

Confirm it worked:

```sql
select column_name from information_schema.columns
where table_name = 'profiles' and column_name in ('favorite_artists','notif_prefs');

select table_name from information_schema.tables
where table_name in ('tm_seen_events','onsale_alert_log');
```

Want two rows back from each.

---

## 2. Deploy the website

```bash
cd ~/Downloads/concerto-website
git pull origin main
```

Copy in this round's changes: `top-picks.html` (search, the corrected
headline, the meta-tag fixes), `netlify.toml` (the alerts-poll
schedule and the `included_files` fix), and
`netlify/functions/alerts-poll.js` (new file).

```bash
git add -A
git commit -m "2.2: Top Picks search, corrected headline, Onsale alerts server

Top Picks gets client-side search (venue, pick, or city) and the
headline now reads 'Where to Go Before the Show' to match the app,
replacing the earlier 'Doors at eight' direction. Caught and fixed a
meta description that still had pre-honesty-pass deal language.

New: netlify/functions/alerts-poll.js, scheduled every 6 hours,
polls Ticketmaster for new tour dates on followed artists and presale
timing on saved shows. Concerto+ only, exactly-once via a database
constraint, defaults to a dry run until ALERTS_DRY_RUN is explicitly
set to false."
git push origin main
```

**Before this actually works, set two things in Netlify's dashboard**
(Site settings > Environment variables):

- `ALERTS_DRY_RUN` -- leave unset for now. Unset or anything other
  than the literal string `false` means dry run. Don't set it to
  `false` until you've watched a few real scheduled runs.
- Confirm `TICKETMASTER_API_KEY` (or `TM_API_KEY`) and
  `SUPABASE_SERVICE_ROLE_KEY` are already set -- they should be, since
  other functions already use them, but worth a glance.

**After it deploys**, check the function actually exists:
Netlify dashboard > Functions > look for `alerts-poll`. It won't have
run yet (next scheduled slot, every 6 hours). You can also trigger it
manually once from the Functions tab to see the dry-run response
immediately rather than waiting.

**Spot-check the site changes:** open `/top-picks`, confirm the
headline reads "Where to Go Before the Show," type a venue name into
the new search box, confirm it filters.

---

## 3. Build and submit the app

```bash
cd ~/Projects/concerto-native
rm -rf ~/Projects/concerto-native
unzip -q ~/Downloads/concerto-native-21.zip -d ~/Projects/concerto-native
cd ~/Projects/concerto-native
git init
git add -A
git commit -m "Concerto 2.2: Favorite Artist, full alerts system, Near Me fix

Near Me's map now recenters when the city filter changes -- it was
frozen on first load and never followed a filter change since
initialRegion and the fit-to-coordinates call both only ever ran
once.

Favorite Artist: follow an artist independent of any tour, with a
real section on Account. The prerequisite the alerts system needed.

Full alerts system, Concerto+ only: Doors (existing, now gated),
Day Of, End of Show, all local and scheduled at save time. Purchase
and restore both retroactively schedule alerts for shows already
saved, so upgrading specifically for alerts actually delivers on the
first show already in the list.

Top Picks screen gets search and the corrected headline line break,
matching the website."
python3 -c "import json;d=json.load(open('app.json'))['expo'];print('version:',d['version'],'| build:',d['ios'].get('buildNumber'))"
```

Want `2.2.0`. Build number is managed by EAS's remote counter now
(confirmed during 2.1 -- the `buildNumber` field in `app.json` is
ignored and safe to leave alone).

```bash
npm ci
npx tsc --noEmit
eas build --platform ios --profile production
```

`tsc` should print nothing. Once the build finishes:

```bash
eas submit --platform ios
```

Pick the build you just finished.

---

## 4. QA before submitting for review

Website has to be live before testing Near Me or the Top Picks
in-app screen, since both depend on it.

1. **Near Me** -- change the city filter, confirm the map actually
   moves this time, not just the event list.
2. **Top Picks card on Home** -- opens the native screen, not a
   browser wrapper. Search box filters. Back button works (it didn't
   before this round).
3. **Follow an artist** -- from any tour page, tap Follow. Confirm it
   shows under Favorite Artists on Account, and tapping it lands on
   Tours with that name in the search box.
4. **Alerts are Concerto+ only** -- on a free account, Settings shows
   the upgrade card, not toggles. On a premium account, all four
   toggles appear and Onsale is included even though it does nothing
   client-side yet (that's expected -- it's a server-side alert).
5. **Purchase retroactively schedules alerts** -- save a show while
   free (no alert scheduled, correct), then upgrade, then check that
   a Doors/Day Of/End of Show notification actually got scheduled for
   that already-saved show without needing to unsave and resave it.
6. Everything from 2.1's list still holds: cold launch, Dynamic Type,
   Near Me → tickets, weather card, Show History, share.

If anything fails, stop and send a screenshot before submitting.

---

## 5. After it's live

- Watch `alerts-poll`'s scheduled runs in Netlify's function logs for
  a few cycles before setting `ALERTS_DRY_RUN=false`. The response
  body reports `newTourDates`, `presaleAlerts`, and `staleArtists`
  counts each run -- a few dry runs with sane-looking numbers is the
  signal to actually flip it on.
- Once flipped live, the first real send is genuinely live to real
  users. Worth doing that switch consciously, not as part of a
  routine deploy.
- No sitemap changes this round -- Top Picks' URL didn't change, only
  its content and headline.

---

## What's deliberately not in 2.2

Manual add-to-history (the Momento gap), Add to Calendar rebuilt with
real device testing, the Icon Composer rebuild, and the corner-radius
pass are all real, scoped, and sitting in `WHATS-NEXT.md`. None of
them are half-built or blocking anything here -- they're just next,
not now. Same for Sports mode and Festivals, both of which need a
real scoping conversation before any code gets written.
