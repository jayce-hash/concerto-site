# Concerto V2 — the app IS the website

## What's here
The Expo web export of the actual app (index, venues, tours, near-me,
account, settings, search, plan, bagcheck, venue/[slug], tour/[slug])
plus _redirects and one script.

## Deploy (from the site repo root)
1.  cp -R ~/Downloads/concerto-web-app/. ~/Downloads/concerto-site/
    (cp MERGES; never drag folders in Finder -- that REPLACES and
    would wipe venues/, tours/, data/ and img/)
2.  python3 retrofit_chrome.py
3.  git add -A && git commit -m "V2" && git push

## What retrofit_chrome.py does
About, FAQ, Premium, Privacy and Terms keep their existing editorial
design -- the fonts, spacing and rhythm are already right. The script
swaps ONLY their nav and footer for markup matching the app-on-web
chrome (lockup, Home/Venues/Tours/Near Me, search + account icons,
gold Get the App; lean footer). Page bodies are untouched, so no legal
or marketing wording changes.

It also creates premium.html from concertoplus.html the first time it
runs, because Concerto+ is a FEATURE (the night planner) while the
paid tier is Premium. _redirects sends /concertoplus -> /premium.

The script is idempotent: pages already carrying the V2 chrome are
skipped, so it's safe to re-run after every export.

## SEO
- 346 venue + 76 tour static pages: untouched, still served first
- App routes: title, description, canonical, OG, smart app banner
- Legacy content pages: keep their original titles and descriptions,
  and gain the smart app banner
