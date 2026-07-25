# WEBSITE.md: the site's new job (Phase G, track 1)

The app is the product now; the site is the funnel. SEO stays the
moat: every venue/tour page keeps ranking, but every ranking page's
job becomes "get the download."

## Do now (minutes, in this zip's spirit)
1. Smart App Banner, site-wide. Add to the shared <head> (all pages
   via build_static.py's head template):
     <meta name="apple-itunes-app" content="app-id=YOUR_APPSTORE_ID">
   Safari then shows the native "open in app" banner on every venue
   page you already rank for. (Get the numeric ID from the App Store
   listing URL after release.)
2. Deploy .well-known/apple-app-site-association (in this zip, edit
   TEAMID first): shared links open the app for people who have it.

## The homepage rebuild (one dedicated session, spec ready)
- Above the fold: lockup, one line ("The app you open after you buy
  the ticket"), App Store badge + QR, and one live phone mockup
  showing the countdown card.
- Section 2: the three signature demos as looping clips (Bag Check,
  Plan My Night, the countdown): reuse the LAUNCH.md captures.
- Section 3: "346 venues, verified" -> the existing venue search (the
  SEO engine, one scroll down instead of front and center).
- Footer: everything current.
- Venue/tour pages: add one persistent "Open in the Concerto app"
  pill above the fold; content unchanged (SEO untouched).

## What NOT to change
URLs, structured data, sitemaps, the data files: the app reads them
and Google ranks them. The funnel changes; the moat doesn't.
