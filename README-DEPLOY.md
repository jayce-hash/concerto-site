# Concerto V2 — the app IS the website

## Deploy (one command, from anywhere)
    cp -R ~/Downloads/concerto-web-app/. ~/Downloads/concerto-site/

Then commit and push. Use `cp -R`, never a Finder drag: cp MERGES,
Finder REPLACES folders and would wipe venues/, tours/, data/, img/.

No script to run this time. The five content pages ship as finished
HTML.

## What's here
1. The Expo web export of the actual app: index, venues, tours,
   near-me, account, settings, search, plan, bagcheck, plus
   venue/[slug] and tour/[slug].
2. about.html, faq.html, premium.html, privacy.html, terms.html —
   rebuilt on ONE design system that matches the app: same tokens
   (navy #121E36, gold #C9A84C, Snow #F8F9F9), same Playfair Display +
   DM Sans, same nav, same footer, same 780px editorial column, same
   title scale and prose leading. Every word is carried over verbatim
   from the originals; only presentation changed.
3. _redirects, including /concertoplus -> /premium.

## Uniformity
Before: About and FAQ used a 4.8rem title with 1.05rem prose; Privacy
and Terms 4rem and 1rem; Premium had its own marketing scale. Now all
five share one stylesheet. Layout still differs by purpose — a pricing
page is not a legal page — but type, scale and colour do not.

## Light mode
Every page renders light, always. Dark is opt-in in the app's Settings
for signed-in users; a guest arriving from Google has no saved
preference, and following their desktop OS made the site look like a
different product than the app on their phone.

## SEO
- 346 venue + 76 tour static pages: untouched, served first
- App routes: title, description, canonical, OG, smart app banner
- Content pages: original titles and descriptions kept exactly, plus
  canonical, OG and the smart app banner
