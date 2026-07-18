# Concerto Static Build, July 18, 2026

Run `python3 build_static.py` from the site root any time data/*.json changes.
The script is idempotent. It regenerates everything and skips what's current.

## What changed

1. VENUE PAGES (346): Bag policy, parking, concessions, and rideshare content
   is now baked into the HTML from data/*.json. Same markup the JS widget drew,
   so nothing looks different, but Google can now read all of it. The widget
   (venue-info.js) skips divs marked data-static="1", which also removes 4 to 5
   JSON fetches per page load.

2. SCHEMA: Every venue page now has typed venue schema (StadiumOrArena /
   PerformingArtsTheater / MusicVenue) with address and geo, BreadcrumbList,
   and FAQPage markup on 329 venues (bag policy, parking, food Q&As). Titles
   and meta descriptions now include the city.

3. NEARBY VENUES: Each venue page links to its 4 closest venues with distance
   (miles in the US, km elsewhere). Styles live in venue-info/venue-info.css.

4. IMAGES: All 39 city guide JPGs converted to WebP, max 1600px, quality 80.
   Total img/cityguides went from ~45MB to 5.7MB. The 13MB El Chile photo is
   now 174KB. data/top_picks.json photo paths updated to .webp.

5. STATIC CITY GUIDES: 8 real pages at /cityguide/{slug} for the venues with
   curated data (Moody Center, TD Garden, MSG, Bridgestone, Kia Forum, Sphere,
   Mercedes-Benz Stadium, Dickies Arena). Netlify serves real files before
   _redirects rules, so these shadow the SPA rewrite automatically. All other
   /cityguide/* URLs still hit the SPA. Added to sitemap.xml.

6. ANALYTICS: Every indexable page loads /analytics.js. To activate, create a
   GA4 property at analytics.google.com and replace G-XXXXXXXXXX in that ONE
   file. Until then it does nothing.

7. FIXES: Lazy loading + async decoding on all below-fold images. Skip-to-content
   links site-wide. Fixed the og:url mismatch on /cityguide/. Repaired
   bagcheck.html and mobile-bags.html, which contained two concatenated HTML
   documents with a stray JS constant between them (pre-existing, now valid
   HTML with auth.js and app-shell.js preserved).

## After deploying

- Resubmit sitemap.xml in Search Console and request indexing on a few venue
  pages to speed up recrawl.
- Rich results won't show instantly. FAQ and breadcrumb eligibility usually
  takes a few weeks after recrawl.
- If you edit data/*.json, run build_static.py before deploying or the static
  content goes stale.
