# Concerto 2.1 : Ship It

Website first (no review needed), then the app build.

---

## 1. Deploy the website

```bash
ls -la ~/Downloads/concerto-site-21-final.zip
unzip -t ~/Downloads/concerto-site-21-final.zip | tail -1
rm -rf ~/Downloads/c21final
unzip -q ~/Downloads/concerto-site-21-final.zip -d ~/Downloads/c21final
cd ~/Downloads/concerto-website
git pull origin main
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
cp -R ~/Downloads/c21final/. .
```

**The zip does not contain setlists.json on purpose** : your repo's
78-key version is the source of truth, and it survives because the
pull ran first and the file is simply absent from the zip. Confirm:

```bash
python3 -c "import json;print(len(json.load(open('setlists.json'))),'setlist keys')"
```

Want 78. Then verify and push:

```bash
ls venue/*.html | wc -l
ls tour/*.html | wc -l
ls mobile*.html 2>/dev/null || echo "mobile shell removed (correct)"
python3 build_data.py
python3 build_sitemap.py
git add -A
git commit -m "2.1: Top Picks and Partners rebuilt, mobile shell retired"
git push origin main
```

If the push is rejected over the workflow file:

```bash
git checkout origin/main -- .github/workflows/rebuild-data.yml
git commit -m "Keep workflow file as-is (web-managed)" --allow-empty
git push origin main
```

Then confirm the Actions tab goes green and Netlify finishes.

**Spot-check once live:** `/top-picks` (carousels scroll, cards open
Maps, venue names link), `/partners`, `/` (home renders, weather card
present), one venue page, one tour page.

---

## 2. Build and submit the app

Unzip `concerto-native-21.zip` somewhere permanent. **This folder gets
git init.**

```bash
cd path/to/concerto-native
git init
git add -A
git commit -m "Concerto 2.1"
npm ci
npx tsc --noEmit
```

In `app.json`: set `expo.version` to `2.1.0` and increment
`ios.buildNumber` past your last build. The splash config change means
this MUST be a full EAS build, not an OTA update.

```bash
eas build --platform ios --profile production
eas submit --platform ios
```

---

## 3. QA before submitting: the ten minute pass

1. **Cold launch** : navy splash only, no white flash. Check first.
2. **Icons** : browse every tab; SF Symbols render, nothing missing.
3. **Dynamic Type** : Settings > Accessibility > Display and Text Size, Larger Text near max. Text grows, layouts hold.
4. **Purchase (sandbox)** : buy Concerto+ with a sandbox Apple ID.
   MEMBER state appears immediately, not after a delay.
5. **Near Me** : tap an event; Ticketmaster opens, not the venue page.
6. **Calendar** : save a show, tap Add to Calendar on the countdown
   card. Permission prompt appears, event lands in Calendar with the
   venue guide link in the notes.
7. **Weather** : save a show within 16 days; forecast card appears on
   Home under Concerto+, and a one line strip shows above Upcoming
   Here on that venue page. Needs step 1 deployed.
8. **Top Picks card** : under the weather card on Home. Tapping opens
   Top Picks in the in-app browser.
9. **History** : with a past dated saved show, the history card shows a
   count; Settings > Privacy shows Clear Show History with a confirm.
10. **Share** : tour page share button opens the sheet with the
    concertocity.com link.

The calendar chip and the Top Picks browser are native only by design;
their absence on web is not a bug.

If anything fails, stop and send a screenshot before submitting.

---

## 4. Release notes for App Store Connect

```
What's new in Concerto 2.1

- Show Day Forecast: the weather for your next saved show, on Home
  and on the venue's guide
- Show History: the shows you've been to, automatically
- Add to Calendar: one tap puts your next show on your calendar
- Top Picks: where to eat and stay before the show, venue by venue
- Share any tour or venue guide with the people you're going with
- Native iOS icons, Dynamic Type support, and larger touch targets
- Membership now activates instantly after purchase
- A smoother launch, with a splash screen that matches the app
- Tapping an event in Near Me now goes straight to tickets
- Dozens of tour listings refreshed and verified
```

---

## 5. Sitemap and after

Once Netlify is green:

1. Search Console, Sitemaps, resubmit `sitemap.xml` (440 URLs).
2. Nothing to configure for weather. No key, no env vars.
3. Clear Show History only appears once a user has a past show.
4. When the Dallas partner signs: add their entry to that venue's
   `data/nearby/{slug}.json` with `"sponsored": true` and a
   `"partnerId"`. The Home card switches from the Top Picks version to
   the partner version, with its PARTNER label, on its own. No app
   update needed.

**Left alone deliberately:** `bags`, `parking`, `rideshare` and
`concessions` are still live and still in the sitemap. Retire them
only after Search Console shows the venue pages indexing, or you throw
away traffic before the replacement ranks.
