# Concerto 2.5 Launch Pack

## Product promise

**Concerto** gives fans everything they need for the concert and the night around it.

**From the Concert to the City®** is the registered brand promise.

**Your Night** is the show-specific experience opened from a saved-show countdown. Venue essentials, weather, setlist, nearby restaurants, hotels, things to do, getting there, and getting home live together on that page.

**Concerto+** is the personalized concierge layer. Free Concerto tells the user what they need to know. Concerto+ helps decide what to do with it through Plan My Night, timing, AI Bag Check, and contextual alerts.

## 2.5 App Store metadata

**Name:** Concerto

**Subtitle:** From the Concert to the City

**What's New in 2.5:**

Concerto 2.5 brings your whole concert night together.

- Tap your saved-show countdown to open Your Night.
- See venue essentials, weather, setlists, nearby restaurants, hotels, things to do, getting there, and getting home in one place.
- Concerto+ now fits naturally into each saved show with personalized planning, timing, AI Bag Check, and contextual alerts.
- Manage favorite artists, tours, and venues from Account.
- Follow Concerto on Instagram, TikTok, and YouTube from the app.
- Includes major reliability, offline-data, subscription, notification, and account-sync improvements.

## Release order

1. Push the **native 2.5 source** to the native repository first.
2. Push the **site 2.5 source** to the site repository second.
3. In the site repository, run **Actions -> Sync native web -> Run workflow**.
4. Wait for the workflow to export the current native web app, overlay it into the site, validate it, commit it, and let Netlify deploy.
5. Test production `concertocity.com` before building iOS.
6. Build a real iOS development/TestFlight build and test the native-only paths.
7. Build production iOS.
8. Upload with the known-good App Store workflow used for Concerto and attach the build in App Store Connect.
9. Submit with manual release and phased release enabled.

## Production website smoke test

- Home loads and the countdown card opens the correct saved show.
- Your Night shows the correct venue, date, hero image, venue information, weather, setlist, nearby content, and getting-home guidance.
- `/about`, `/premium`, `/partners`, `/creators`, `/press`, `/investors`, `/contact`, `/faq`, `/help`, `/privacy`, and `/terms` all load.
- Company pages are indexable except pages intentionally marked noindex for auth/app-shell reasons.
- Search, Venues, Tours, Near Me, Account, sign-in, and sign-out work.
- Instagram, TikTok, and YouTube links go to the official Concerto profiles.
- `/show/*`, `/venue/*`, and `/tour/*` deep links resolve correctly.
- Mobile web navigation does not overflow.

## Native/TestFlight smoke test

- Existing account signs in and retains saved shows/favorites.
- A second account never sees the first account's saved shows.
- Save two or more shows and swipe the countdown carousel.
- Tap each countdown and confirm it opens the matching Your Night page.
- Free Your Night shows the actual information without hiding core venue facts.
- Free Concerto+ CTA routes to Account and does not promise an unimplemented free plan.
- Purchase monthly Concerto+ in sandbox.
- Purchase annual Concerto+ in sandbox.
- Restore Purchases works.
- RevenueCat webhook updates `profiles.is_premium`.
- Plan My Night opens from a saved show with show context prefilled.
- AI Bag Check uses the selected venue policy and reports a clear result.
- Notification switches cancel/reconcile scheduled notifications correctly.
- Sign out clears account-specific local state.
- Instagram, TikTok, and YouTube open from Account.
- Camera, photo library, location, maps, Uber/Lyft, and share actions work on a real device.

## App Store Connect

**Privacy Policy:** https://concertocity.com/privacy

**Support:** https://concertocity.com/help

**Marketing:** https://concertocity.com

Use a reviewer account with Concerto+ access so Bag Check and Plan My Night can be reviewed.

## iOS capability status for 2.5

Shipping now: native notifications, location, camera/photo access, deep/universal links, native share behavior, maps/rideshare handoff, haptics, Apple IAP through RevenueCat, and offline venue/tour/setlist fallbacks.

Not a 2.5 launch blocker: the countdown Home Screen widget and show-day Live Activity. The earlier hand-written extension was removed after blocking EAS builds. The product hooks and App Group remain so these can return through a supported, deliberately tested native path after 2.5.

## Go / no-go

Do not release until all of the following are true:

- Native release validator passes.
- Site release validator passes.
- Native web sync workflow completes after the final native commit.
- Production website smoke test passes.
- TestFlight smoke test passes.
- Supabase RLS is confirmed for `profiles`, `push_tokens`, and `analytics_events`.
- RevenueCat purchase and restore pass in sandbox.
- App Store privacy answers match the production behavior.
