# The Show Night homepage -- CINEMATIC CUT (GSAP)

## What changed from the first cut
This is the awwwards-tier pass. GSAP + ScrollTrigger (CDN, deferred)
now direct the page like a film:
- CURTAIN: a once-per-session house-lights opening -- navy curtain,
  gold CONCERTO lockup breathing in, then it lifts.
- ENTRANCE: headline lines rise out of masks, sub/CTAs/phone arrive
  in a choreographed timeline; the phone swings in from a deeper
  angle.
- SCROLL SCRUB (the Fable move): scrolling through the hero is
  scrubbed -- the phone straightens to face you and drifts upward,
  the headline halves part, the beams fan wider, the crowd dims.
  You are literally walking out of the venue.
- MARQUEE VELOCITY: scroll faster and the venue ribbon spins faster,
  easing back when you stop.
- MAGNETIC App Store badge (pulls toward the cursor), pointer-tilt
  phone via GSAP quickTo, and a soft gold cursor glow.
- Section reveals now run on ScrollTrigger with batch stagger.

## Engineering honesty
- Progressive enhancement: if the CDN fails or JS is off, every word
  and link renders normally; a fallback (IntersectionObserver + CSS)
  still gives simple reveals. The countdown ticks with or without
  GSAP.
- prefers-reduced-motion disables the entire choreography.
- Weight: two deferred CDN scripts (~60KB gz total, cached across
  half the web); page HTML still ~46KB, no images, no video.
- One h1 with a full aria-label (the visual split never leaks into
  the accessibility tree as fragments).

## Verify-in-Chrome loop
Deploy, then tell Claude -- with the Claude in Chrome extension it
can open the live page, screenshot it, and iterate on the real
render with you.


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
