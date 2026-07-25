# Venue photos: how this works now

## What changed and why
The original bulk-download approach (a Python script fetching Google
Places photos and saving them as your own .webp files) was flagged,
correctly. Google's Maps Platform Terms (Section 3.2.3, "No Caching")
prohibit pre-fetching, caching, or storing Places content beyond two
narrow exceptions: place_id (indefinite) and lat/lng (30 days).
Photos are not on that list. Permanently rehosting them would have
been a real terms violation, not a gray area.

The Wikimedia-photo attempt that replaced it is still in
data/nearby (unrelated) but its photo output didn't cover enough
venues well, so a new approach was needed.

## The compliant fix: live lookup, nothing stored
netlify/functions/venue-photo.js is a serverless function that looks
up a venue's photo on Google FRESH, every time the app asks for one,
and never writes anything to disk. This is the pattern Google's own
documentation describes as correct: a photo's reference "can expire"
and you're expected to fetch it live from a search response, not
cache it.

The app already calls this per-venue, only for venues on screen
(same pattern it already used for Ticketmaster photos), so it stays
cheap: a handful of live calls per session, not 346 upfront.

## Setup (one-time, ~5 minutes)
1. Google Cloud Console -> APIs & Credentials -> Create Credentials
   -> API key. This is a NEW key, separate from the browser key
   maps-key.js already serves. Do not reuse that one.
2. Click the new key -> API restrictions -> restrict to "Places API
   (New)" only. Leave application restrictions as None: this key
   only ever lives in your server environment, never sent to a
   browser, app, or committed to the repo.
3. In Netlify: Site settings -> Environment variables -> add
   GOOGLE_PLACES_SERVER_KEY with that key's value.
4. Deploy netlify/functions/venue-photo.js (already in this zip).
   That's it. No script to run, nothing to commit for images.

## What you'll see
Venue cards and venue detail heroes now try, in order: your own
cityguide photos (if you've shot one) -> a live, coordinate-verified
Google Places photo with attribution shown on the detail page ->
Ticketmaster's venue photo -> the navy monogram. Coverage grows
automatically as Google's data does; there's no batch job to
re-run.
