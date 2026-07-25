# The Show Night homepage

## Concept: two acts
ACT I -- THE CONCERT. The page opens inside the venue: deep navy,
three slowly sweeping stage-light beams (pure CSS), a drifting field
of gold crowd lights, and a floating, glowing iPhone running the app
with a LIVE, TICKING countdown (a real target date, persisted per
visitor, so returning visitors watch it genuinely fall). The
headline's "City." shimmers in animated gold. A venue-name marquee
(MSG - The O2 - Red Rocks - Sphere...) glides along the bottom like
an arena ribbon board. On desktop the phone parallax-tilts with the
pointer.

ACT II -- THE CITY. A tall gradient ("daybreak") steps out of the
venue into snow-white daylight for the practical sections: the three
signature features, The Library (346/74 as giant serif numbers -- the
SEO engine reframed as the app's moat, all internal links intact),
and the Concerto+ band. Sections rise in as you scroll.

That transition IS the brand: from the concert to the city, enacted
by the page.

## Weight, honestly
The new page is LIGHTER than the old one (39KB vs 54KB) with zero
libraries, zero images beyond the QR and your logo, zero video.
All the motion is CSS + ~60 lines of vanilla JS.
prefers-reduced-motion disables every animation.

## Files
- index.html  -> replace at repo root
- app-shell.js -> replace at repo root (one-line fix: the "Get the
  App" nav pill now finds your .nav-cta container)

## Repo cleanup
Delete now: img/test/ (unused).
Delete ONLY AFTER the native app ships: all mobile-*.html pages,
livemode.html, mobile-livemode.html -- the live App Store app still
renders those today; removing them early breaks it. (~700KB.)
Keep: img/cityguides (59MB) -- that's the venue photography your
SEO pages serve; it IS the site's value, not bloat.

## SEO: unchanged where it counts
Same title/description/canonical/schema.org/OG block, one h1, full
crawler nav on every page, all venue/tour/hub internal links present
in the Library section, sitemaps untouched.
