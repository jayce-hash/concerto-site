# Concerto: the app IS the website

This folder is the OUTPUT of building your actual app for the web:

    npx expo export --platform web --output-dir dist
    node scripts/inject-web-seo.js dist

Not a rebuild. Not a port. The same `app/(tabs)/index.tsx`, the same
VenueCard, the same tokens, the same Home tab -- compiled to run in a
browser. Change the app, rebuild, the website changes with it. Drift
is now structurally impossible.

## What's in the repo change (in the app repo, concerto-native)
- react-dom / react-native-web / @expo/metro-runtime added
- app.json: web bundler metro, output static
- src/components/VenueMap.tsx + .web.tsx  -- react-native-maps has no
  web build, so web renders a quiet placeholder; the events list
  beneath it (the substance of Near Me) is identical on both.
- src/lib/supabase.ts -- SSR-safe storage so static prerender works
- src/data/api.ts -- ORIGIN is the current host on web, so branch
  previews fetch their own data; native still points at production
- scripts/inject-web-seo.js -- titles/canonicals/OG/smart-banner for
  the app's own routes after each export

## SEO: nothing was given up
- /venues/{slug} and /tours/{slug}: your 346 + 76 STATIC pages, real
  files, served first by Netlify, completely untouched.
- The app's detail screens use the SINGULAR /venue/{slug} and
  /tour/{slug}, so the two systems never collide.
- The app's own routes (/, /venues, /tours, /near-me) now carry
  title, description, canonical, OG tags and the smart app banner.

## Web-only guards that had to exist (learned the hard way)
Constants.appOwnership is 'expo' in Expo Go, NULL on web, and
undefined in a real build. Guards written as (appOwnership !== 'expo')
therefore returned TRUE on web and tried to require native-only
modules. That is what crashed the Account screen. Now excluded
explicitly by Platform.OS:
  - react-native-purchases (IAP)  -> native only
  - App Group widget storage      -> iOS only
  - expo-notifications            -> native only (web no-ops so
    saving a show still works everywhere)
  - ErrorBoundary "Try again"      -> real window.location.reload()
    on web (Updates.reloadAsync left the router mid-navigation,
    which is why it landed on Bag Check)

## How to deploy into the site repo
1. Copy EVERYTHING from this folder into the site repo root
   (index.html, _expo/, assets/, the route .html files, _redirects).
2. Do NOT delete: venues/, tours/, data/, img/, netlify/, sitemaps,
   robots.txt, or the cityguide folder. They stay.
3. Commit and push the v2-redesign branch.

## Rebuilding later (the loop from now on)
In the APP repo:
    npx expo export --platform web --output-dir dist
    node scripts/inject-web-seo.js dist
then copy dist/* into the site repo. That's the whole workflow.
