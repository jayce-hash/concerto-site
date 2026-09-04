# Concerto 2.5 Release Status

## Release identity

- Native version: 2.5.0
- Native iOS build baseline: 16
- Bundle ID: com.v8ef92dbd0a8.www
- App Store ID: 6744903414
- Brand promise: From the Concert to the City®

## Product changes locked for 2.5

- Saved-show countdown is the primary entrance to Your Night.
- Countdown card clearly says View Your Night.
- Your Night is a destination, not a second Home screen or a menu of feature links.
- Free users see the actual venue essentials, weather, setlist, nearby restaurants, hotels, things to do, getting-there guidance, and getting-home guidance.
- Concerto+ is the personalized concierge layer, not a bundle of disconnected premium buttons.
- Plan My Night uses the saved show context.
- Home no longer owns the three saved-show-specific nearby rails.
- Instagram, TikTok, and YouTube are surfaced in-app using the official site destinations.
- Company website now includes first-class About, Partners, Creators, Press & Media, Investors, Contact, FAQ, Help, Privacy, Terms, and Concerto+ destinations.
- Company pages are in the sitemap and indexable where appropriate.
- Product and company language is governed by BRAND-LANGUAGE-2.5.md and PRODUCT-2.5.md in both repos.

## iOS status

Shipping in 2.5:
- native notifications
- camera and photo-library access for AI Bag Check
- location
- native maps/rideshare handoff
- haptics
- share actions
- universal/deep links, including /show/*
- Apple IAP through RevenueCat
- offline venue/tour/setlist fallbacks

Deferred intentionally:
- Home Screen countdown widget
- show-day Live Activity / Dynamic Island

The old hand-written native extension was removed after it blocked EAS builds. 2.5 keeps the product hooks/App Group for a supported, deliberately tested implementation later. It is not being reintroduced blindly for launch.

## Validation completed on this source package

- Native release validator: PASS
- Site release validator: PASS
- 81 TS/TSX source files parsed with zero syntax failures
- 24 site JavaScript files checked with zero syntax failures
- 374 JSON files parsed with zero failures
- 30 root HTML pages parsed with zero failures
- Internal HTML href audit: zero unresolved links
- 346 offline/native venues
- 346 site venue records
- 158 tours
- 157 setlists
- 8 verified venue information sections per site venue
- AASA includes /show/*
- Duplicate auth.js loads removed from root HTML pages
- New company pages included in sitemap

## One required deployment step after uploading both repos

The site archive intentionally contains the last generated Expo web bundle because the local environment could not complete a fresh Expo dependency install/export. The source of truth is current.

After pushing native first and site second:

1. GitHub -> concerto-site -> Actions
2. Run **Sync native web**
3. The workflow checks out current native main, runs npm ci, exports Expo web, overlays the generated app into the site, validates it, writes `.native-web-sync.json`, runs deployment validation, commits the synchronized output, and lets Netlify deploy.

Do not call the website deployment final until that workflow succeeds.

## Final go/no-go checks that require real accounts/devices

- Supabase RLS confirmed on production tables
- TestFlight smoke test on a real iPhone
- RevenueCat monthly purchase, annual purchase, and Restore Purchases in sandbox
- RevenueCat webhook flips `profiles.is_premium`
- production website smoke test after native-web sync
- App Store privacy questionnaire matches production behavior
- reviewer account has Concerto+ access

See LAUNCH-2.5.md in either repo for the exact release sequence and test checklist.

## Final company-site navigation pass
- Added one global footer/navigation system to every generated/static HTML page.
- Footer groups are now consistent everywhere: Explore, Company, Work With Us, Support, plus Privacy/Terms and official Instagram/TikTok/YouTube channels.
- Rebuilt About, FAQ, Concerto+, and Investors into the same corporate visual system as Partners, Creators, Press, and Contact.
- Privacy and Terms retain a simpler legal-document layout intentionally, but now use the same global footer/navigation.
- Updated the native web `WebFooter` source so future Expo web exports preserve the same information architecture instead of reverting to the old lean footer.
