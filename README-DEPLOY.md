# Concerto V2 — the app IS the website

## Deploy (two commands, from the site repo root)
    cp -R ~/Downloads/concerto-web-app/. ~/Downloads/concerto-site/
    python3 retrofit_chrome.py
    git add -A && git commit -m "V2" && git push

Use `cp -R`, never Finder drag: cp MERGES, Finder REPLACES folders and
would wipe venues/, tours/, data/ and img/.

## retrofit_chrome.py
Swaps ONLY the nav and footer on about / faq / premium / privacy /
terms, and injects one shared stylesheet that locks all five to the
same type scale, colours and light mode. Page BODIES are untouched, so
no legal or marketing wording is altered.

It is VERSION-AWARE (chrome v2.1): pages carrying older chrome are
UPGRADED in place rather than skipped, and the old blocks are stripped
first so nothing is duplicated. Safe to re-run after every export.

It also creates premium.html from concertoplus.html on first run --
Concerto+ is a FEATURE (the night planner); the paid tier is Premium.
_redirects sends /concertoplus -> /premium.

## Light mode
The site always renders light. Dark is opt-in via Settings, for
signed-in users -- a guest arriving from Google has no saved
preference, and following their desktop OS made the site look like a
different product than the app on their phone.

## SEO
- 346 venue + 76 tour static pages: untouched, served first
- App routes: title, description, canonical, OG, smart app banner
- Legacy content pages: original titles kept, smart banner added
