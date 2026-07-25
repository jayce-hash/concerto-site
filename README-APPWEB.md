# concertocity.com IS the app — Layer 1, faithful port

Built by reading the app's actual source (concerto-native), not by
approximating it. css/concerto.css ports src/theme/tokens.ts and the
Home tab's real components value-for-value:

- Masthead: greeting eyebrow (11px/1.5 gold, time-aware) + the REAL
  lockup asset (assets/lockup.png, 250x52, auto-inverts in dark)
- SearchPill: exact paddings, 34px goldSoft icon circle, 15/12 type
- NextShowCard EMPTY STATE, exactly as shipped: navy radius-24 card,
  "Save a show and the countdown starts here.", the GHOST dashed
  countdown (-- DAYS : -- HRS : -- MIN) and the gold "Find tonight"
  pill -> App Store. (The earlier invented live ticker is gone; the
  app shows the ghost, so the web shows the ghost.)
- VenueCard: the app's real grammar -- 200px card, 150px image on
  top, name (Playfair 16) + city (12.5 muted) BELOW, gold verified
  shield. Real photography for MSG/Moody/TD Garden/Kia Forum/
  Bridgestone; navy monogram fallback (52px gold initial) for the
  rest, exactly like the app.
- TourTile: 168x224, navy, 56px gold Playfair initial, scrim,
  artist 17 / tour 11.5 over the image.
- SectionHeaders: Playfair 22 + gold 13 action, app spacing.
- NightCard, full port: Concerto+ header row, "Your Whole Night,
  Planned", the 5:45/7:10/11:15 preview rows with the gold middle
  dot, "$7.99/mo · first plan free to preview", gold "Try it".
- Mobile: bottom tab bar (Home/Venues/Tours/Near Me/Get App).
- Night mode: OS-following, using the app's exact dark palette.

FILES: index.html (replace), css/concerto.css (new), 
js/concerto-shell.js (new), img/lockup.png (new — the app's own
masthead asset).

SEO: head verbatim + smart banner, one h1 (the lockup image with
full alt), all hub/venue/tour internal links present, footer + all
existing page scripts untouched.
