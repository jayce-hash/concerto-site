# Partner Console: setup and pricing

## One-time setup
1. Supabase, SQL editor: run `migration-partners-2026-09-18.sql`.
2. Supabase, Authentication, URL configuration: add `https://concertocity.com/console/` to Redirect URLs.
3. Supabase, Authentication, Email templates: the magic link template can say
   "Sign in to the Concerto Partner Console".
4. Netlify env already has SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY; nothing new.
5. Stripe: create two products, Venue ($299/month, id in STRIPE_PRICE_VENUE) and
   Partner ($149/month, STRIPE_PRICE_PARTNER). Checkout links come after the founding
   period; founding orgs have plan=founding and plan_until=2026-12-31.

## Review queue (you, once a day)
Perks are created as status=draft. Approve by setting status=live in Supabase
(Table editor, perks). Venue overrides publish immediately because the venue proved
its domain; spot-check bagPolicy changes.

## What flows where
Console writes: venue_overrides, stage_times, perks. App and site read
/.netlify/functions/partner-content (cached 5 min). Nothing partners publish ever
edits venue_info.json; the merge happens at read time, so the researched baseline
stays intact and a venue's words carry "Verified by the venue" with the date.
