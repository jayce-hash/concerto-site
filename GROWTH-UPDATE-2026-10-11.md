# Growth update, October 11, 2026 (site)

- Sitemap: prepare-site.py now rebuilds sitemap.xml after the pages are generated, so all 673 venue pages, 175 tours and 87 setlists are listed (was 346 / 165 / 86).
- Bag policies: 150 venues re-researched from official sources (data/updates/applied/bag-policy-research-2026-10-11.json, applied to data/venue_info.json). Includes Madison Square Garden.
- Venue pages lead with the bag answer ("Bag policy: ...") instead of a generic line. Button reads "Remind me on show day". Closing line explains the free 9am show-day reminder.
- Tour and setlist pages: closing line mentions the setlist, bag rules and show-day reminder.
- Pricing copy (Your Night, Concerto+, FAQ): the 9am Show Day reminder is free; Concerto+ keeps the other alerts.
- GA4: every App Store / Open in Concerto tap sends an `app_store_tap` event with campaign (ct), page_type and page_path.

## Follow-up the same day
- Second research pass: 16 more venues (data/updates/applied/bag-policy-research-2-2026-10-11.json), including Synovus Bank Amphitheater, MGM Grand Garden Arena, Fontainebleau, Radio City, ESSENCE, and "not scheduled for 2026" entries for Music Midtown, Hangout, Pitchfork, Made in America, Life Is Beautiful, Moonrise and When We Were Young.
- MSG bag source now points to a January 2027 MSG event page (lasts longer than the November one).
- Renamed: NRG Stadium to Reliant Stadium, SSE Arena Belfast to The O2 Belfast, Paris La Défense Arena to Plenitude Arena. Slugs unchanged; old names kept in page titles.
- Merged duplicates: pnc-arena into lenovo-center, xl-center into peoplesbank-arena (301s in _redirects). Venue count is now 671 (validate-release.js updated).
- Fixed Lenovo Center (Raleigh, correct coordinates) and Huntington Bank Field (Cleveland, correct coordinates).
- setlists.json: 28 new setlists from ChatGPT (115 total). Its file had broken characters (curly apostrophes and accents garbled) in 64 places; repaired, so existing setlists are unchanged. Setlists taken from setlist.fm get a structured source and show as "Reported setlist from <venue>, <date> (setlist.fm)".

## Pages that answer first (second update, Oct 11)
- Quick answers were built and then removed (Jayce's call): revisit with a smart search bar. scripts/venue_glance.py stays only for the bag sentence at the top of each venue page.
- Venue pages: Directions (Apple Maps on Apple devices), upcoming shows with doors, show time, opening acts, Save in Concerto and Tickets, and nearby venues by real distance.
- Tour pages: tour dates (only dates where the artist is billed) with opening acts, venue guide links, Save and Tickets; varied "More tours"; Listen on Apple Music.
- Setlist pages: Listen on Apple Music, link to tour dates.
- Near Me: real shows this week near the visitor (IP location, city search), each linked to its venue guide.
- Around the Venue stays off.

## Ask Concerto (Concerto AI)
- netlify/functions/ask.js: one answer service for the website and the app. Finds the venue (name, short name like MSG, or former name) and/or tour (artist) and the topic, then:
  1. Guide answer, free: quotes Concerto's own guide lines, setlists and Ticketmaster dates, with the checked date and a link. Most questions end here.
  2. AI answer (Claude Haiku), only when a question needs reasoning (sizes to compare, "what should I know"), using only Concerto's data for that venue or tour.
- Cost caps (Netlify Blobs, store "concerto-ask"): 3 AI answers a day signed out, 5 signed in, 30 with Concerto+; whole site ASK_DAILY_CAP (default 100) and ASK_MONTHLY_CAP (default 1500); identical questions reuse a saved answer for 14 days; fails closed. The question text is never stored or logged.
- Website: Ask bar with a gold ring on the homepage hero and the search page (/search?q=...&ask=1 asks right away). Concerto+ lists more Concerto AI answers.
- Tested: 48 hand-written fan questions plus 85 generated ones, independently reviewed against the data (setlists 15 of 15 correct; venue answer patterns that were weak or wrong were fixed).
