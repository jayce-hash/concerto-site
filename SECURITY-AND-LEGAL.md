# Concerto security and legal checklist (Sep 21, 2026)

## Done in code (this release)
- Public functions that spend money or write data share one guard (`netlify/functions/lib/guard.js`):
  foreign origins refused (lookalike domains included), CORS limited to our own origins (was `*`),
  per-IP rate limits, input validation and body-size caps. Applied to venue-photo (Google Places),
  report, and partner-claim. The Ticketmaster proxy already checks its referer hostname exactly.
- venue-photo success responses cached at Netlify's edge for a day: fewer paid Places calls.
- Security headers on every page: HSTS, Permissions-Policy, Cross-Origin-Opener-Policy, with the
  existing X-Frame-Options, nosniff, and Referrer-Policy. Console, account, settings, plan: no-store.
- Content-Security-Policy ships in Report-Only mode. After a week with no violations in the browser
  console on the live site, rename the header in `_headers` to `Content-Security-Policy` to enforce it.
- Privacy Policy section 8 names every service provider and the Google Analytics cookies.
- No secret keys in either codebase. The app ships only public-by-design keys (RevenueCat SDK key,
  Supabase URL and anon key). Every table in `supabase/*.sql` has row-level security.
- App: Apple privacy manifest present; every permission has a plain-language usage string;
  account deletion in the app; no ad tracking, so no App Tracking Transparency prompt is needed.
- Removed a watermarked Getty image (Madison-Square-Garden.webp) from the site. Never reuse it.

## Accounts only you can secure (an afternoon)
1. Two-factor authentication on Apple Developer, App Store Connect, GitHub, Netlify, Supabase,
   Google Cloud, RevenueCat, Anthropic, Ticketmaster developer, your email, and the domain registrar.
   Turn on registrar lock for concertocity.com.
2. Google Cloud: restrict the Places server key to the Places API only; restrict the iOS Maps key to
   the bundle ID com.v8ef92dbd0a8.www; set a monthly budget with alerts and a daily quota cap.
3. Anthropic console: set a monthly spend limit and an alert.
4. Supabase dashboard → Advisors → Security: confirm row-level security on tables created before
   these migrations (profiles, saved shows); turn on leaked-password protection; confirm backups.
5. Email for concertocity.com: SPF, DKIM, and DMARC records, so magic links arrive and nobody can
   send mail pretending to be you.

## Legal: have a lawyer review before or shortly after launch
- Privacy Policy and Terms, including section 8. Ask specifically about: a state privacy rights
  section (California and other states), whether any analytics counts as "sharing," data retention
  periods, and how AI Bag Check photos are handled. Update the effective date when approved.
- Photo rights. You need permission for every photo on the site and in the app. Confirm in writing
  where the venue exteriors in `img/cityguides/*/<Venue>.webp` (Kia Forum, Bridgestone Arena, Moody
  Center, TD Garden) came from; if you cannot, replace them with your own or licensed photos. The same
  goes for restaurant photos taken from partners' Instagram posts.
- Copyright safe harbor: register a DMCA designated agent with the US Copyright Office (about $6,
  renewed every 3 years) and add a takedown contact to the Terms.
- Trademark: keep "®" on "From the Concert to the City" only if the federal registration is issued;
  if it is still pending, use "™".
- Third-party terms: Google Places photos must keep their author credit (the site shows it);
  Ticketmaster data must keep the link to buy on Ticketmaster (the site keeps a Tickets link).
- App Store Connect privacy "nutrition label" must match the Privacy Policy: contact info (email),
  identifiers (user ID), purchases, usage data, and location if collected. Calendar matching happens
  on the phone and is not collected.
