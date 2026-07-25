# concertocity.com IS the app -- Layer 1: shell + homepage

## The principle (agreed)
Airbnb's site works because it's their app on a bigger screen. This
is Concerto's version of that. The homepage is the app's Home tab,
rebuilt for the web from the app's ACTUAL design tokens
(src/theme/tokens.ts ported line-for-line into css/concerto.css):
same navy/gold/snow, same Playfair + DM Sans, same 12/18px radii,
same spacing scale, same card grammar.

What renders:
- The app's masthead: time-aware greeting, CONCERTO lockup, tagline
- The app's search pill ("Find your next show") -> /venues
- The app's Next Show card, navy with gold eyebrow, with a LIVE
  ticking countdown and "Find tonight -- in the app"
- "Your Venues & Nearby": REAL venue cards -- your actual photography
  (MSG, Moody Center, TD Garden, Kia Forum, Bridgestone) in the
  app's exact image/scrim/two-line card style, + a "346" navy card
- "Featured Tours": eight tour tiles in the app's designed fallback
  (gold Playfair initial on navy, ON TOUR badge)
- The app's Concerto+ upsell card
- A quiet SEO library block keeping every hub link crawlable
- MOBILE: a bottom tab bar (Home / Venues / Tours / Near Me / Get
  App) -- on a phone, the site literally navigates like the app
- Night mode: follows the OS with the app's exact dark palette

## Files (3 new/changed -- index.html is the only replaced file)
- index.html        -> replace at repo root
- css/concerto.css  -> NEW folder+file
- js/concerto-shell.js -> NEW folder+file

## SEO
Same head block verbatim (title/desc/canonical/schema/OG) + smart
banner. One h1. Footer with full link set untouched. Venue/tour
cards link to their real pages (internal linking preserved).

## Layers 2-3 (next sessions, per the agreed blueprint)
2: rework build_static.py templates so all 346+74 pages render in
   this same design system; one regeneration, same URLs.
3: the deletion pass with 301s (mobile-*.html etc. AFTER native
   app ships).
