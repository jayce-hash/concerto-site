# Concerto 2.1 — Ship It

Two zips. Website first (independent, no review), then the app build.

---

## 1. Deploy the website

```bash
ls -la ~/Downloads/concerto-site-21.zip
unzip -t ~/Downloads/concerto-site-21.zip | tail -1
rm -rf ~/Downloads/concerto-21
unzip -q ~/Downloads/concerto-site-21.zip -d ~/Downloads/concerto-21
cd ~/Downloads/concerto-website
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
cp -R ~/Downloads/concerto-21/. .
```

**IMPORTANT — restore the setlists file before committing.** The zip
deliberately does not carry setlists.json (your repo's new 78-key
version is the source of truth and must not be overwritten):

```bash
git restore setlists.json
```

Then verify, commit, push:

```bash
ls venue/*.html | wc -l     # want 347
ls tour/*.html | wc -l      # want 79
python3 build_data.py       # reconciles names into setlists, ends "All checks passed"
python3 build_sitemap.py    # want 440 URLs, 78 tour guides
git add -A
git commit -m "2.1: weather, home cards, 78 tours, page retirements

Full re-export with all 78 tours at their singular URLs, names
verified against official sources. features, how-it-works and
setlists retired with 301s. Partners and Top Picks aligned to the
About design language. New weather Netlify function (server-side
Open Meteo proxy, keyless). tours.json is now the single source of
truth for names; setlists.json inherits via build_data.py, and
lastShowDate is retired in favor of Ticketmaster's live dates."
git push origin main
```

The GitHub Action re-runs build_data on the push and commits any
reconciliation to setlists.json automatically.

---

## 2. Build and submit the app

Unzip concerto-native-21.zip somewhere permanent. **This folder gets
git init** (for real this time):

```bash
cd path/to/concerto-native
git init
git add -A
git commit -m "Concerto 2.1"
npm ci
npx tsc --noEmit        # should print nothing
```

Version bump in app.json: set expo.version to "2.1.0" and increment
ios.buildNumber past your last build. The splash config change means
this MUST be a full EAS build (not an OTA update):

```bash
eas build --platform ios --profile production
eas submit --platform ios
```

---

## 3. QA before hitting submit — the ten-minute pass

On a TestFlight build or simulator:

1. **Cold launch** — navy splash only. No white flash. (The whole
   point of the splash fix; verify it first.)
2. **Icons** — browse every tab. SF Symbols render on iOS; any icon
   that looks missing means a mapping gap (fallback should prevent
   this, but look).
3. **Dynamic Type** — Settings > Accessibility > Display & Text Size >
   Larger Text, drag near max. App text grows, layouts hold.
4. **Purchase (sandbox)** — buy Concerto+ with a sandbox Apple ID.
   MEMBER state appears IMMEDIATELY on completion, not after a delay.
5. **Near Me** — tap an event. Ticketmaster opens (not the venue page).
6. **Calendar** — save a show, tap Add to Calendar on the countdown
   card. Permission prompt shows the doors-themed message; event lands
   in Calendar with the venue guide link in notes.
7. **Weather** — save a show within 16 days at an outdoor venue; the
   forecast card appears on Home under the Concerto+ card, and a
   one-line strip shows above Upcoming Here on that venue's page.
   (Requires the website deploy from step 1 to be live first.)
8. **History** — if your test account has a past-dated saved show, the
   history card shows a count; Settings > Privacy shows Clear Show
   History with a confirm dialog.
9. **Share** — share button on a tour page opens the sheet with the
   concertocity.com link.
10. **Hero crop** — open the 5SOS tour page; heads visible.

If anything fails, stop and send me a screenshot before submitting.

---

## 4. Release notes for App Store Connect

```
What's new in Concerto 2.1

- Show Day Forecast: see the weather for your next saved show, right
  on Home and on the venue's guide
- Show History: shows you've been to now live on your Home screen,
  automatically
- Add to Calendar: one tap puts your next show on your calendar
- Share any tour or venue guide with the people you're going with
- Native iOS icons, Dynamic Type support, and larger touch targets
  throughout
- Membership now activates instantly after purchase
- Launch is smoother, with a splash screen that matches the app
- Tapping an event in Near Me now goes straight to tickets
- Dozens of tour listings refreshed and verified
```

---

## 5. After approval

- Release, then delete old TestFlight builds you don't need.
- Search Console: resubmit the sitemap (440 URLs now).
- Weather needs no key, no env vars, nothing to configure. It works
  the moment Netlify deploys.
- Clear Show History exists but only appears once a user has at least
  one past show; don't be surprised it's invisible on a fresh install.
- When the Dallas partner pilot signs: their entry goes into that
  venue's data/nearby/{slug}.json with "sponsored": true and a
  "partnerId" — the Home partner card and its PARTNER disclosure label
  light up on their own from the data. No app update needed.
