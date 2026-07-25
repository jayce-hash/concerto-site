# Concerto site additions (one companion zip for the website repo)

Everything in here goes into the concerto-site repo root and deploys
with the site. The native app consumes it all.

1. netlify/functions/delete-account.js: in-app account deletion
   (required for App Store review). Uses the existing SUPABASE_URL /
   SUPABASE_SERVICE_ROLE_KEY env vars.
2. data/nearby/: the 3.7 MB nearby.json split into 346 per-venue
   files. Powers "Near the venue" on every venue page in the app.
   (See README-NEARBY-SPLIT.md for keeping build_static.py in sync.)
3. scripts/fetch_venue_photos.py: one command to give all 346 venues
   an exterior photo (Google Places, ~$few, resumable, hand-replace
   friendly). Writes img/venues/*.webp + data/venue_photos.json,
   which the app prefers over Ticketmaster imagery.

tools/fetch_venue_photos.py: one-time venue exterior photo fetch from
Google Places (run in the site repo root with GOOGLE_MAPS_API_KEY).
Outputs img/venues/*.webp + data/venue_photos.json + attribution
file. Commit and deploy; the app picks photos up automatically.

build_static.py: your existing build script with one addition: right
after nearby.json is loaded, it regenerates the data/nearby/ split
(346 per-venue files) on every build, so the app's city data can
never drift from the site's. Replace your build_static.py with this
one (it is your file from the zip, plus that block; nothing else
touched).

.well-known/apple-app-site-association: universal links (edit TEAMID,
deploy with the site). WEBSITE.md: the site's Phase G repositioning:
do-now steps + the homepage rebuild spec.

supabase/analytics_setup.sql: run once in the Supabase SQL Editor to
create the analytics_events table the app writes to. Insert-only by
RLS, so the public anon key cannot read your data. The file also
contains ready-made queries for daily actives, activation rate,
retention, top venues, and premium feature usage.
