# Concerto Partners: how it works (Oct 5, 2026)

## The offer
A restaurant or hotel pays $99/month or $999/year and gets:
1. Its card on its venue's page (app + concertocity.com) and in Your Night for
   every show there: photo, name, one-line description, Reserve, Directions,
   labeled Concerto Partner. Several partners at a venue rotate daily.
2. Its Perk on that card (optional), also on the Concerto Perks page.
3. A monthly report: card views and Reserve/Directions taps.

Nothing is free. A partner (or a venue) is public only while Stripe says they're paid.

## One-time setup
1. Stripe Dashboard > Product catalog > Add product "Concerto Partner" with two
   recurring prices: $99 per month and $999 per year. Copy each price ID (price_...).
2. Netlify > Site configuration > Environment variables, add:
   STRIPE_PRICE_PARTNER_MONTHLY = the $99 price ID
   STRIPE_PRICE_PARTNER_ANNUAL  = the $999 price ID
   (STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET already exist for Concerto+.)
3. Stripe > Developers > Webhooks > your existing concertocity.com endpoint: make
   sure it sends checkout.session.completed, customer.subscription.updated and
   customer.subscription.deleted (Concerto+ already uses these three).
4. Supabase SQL editor: apply supabase/migration-perk-review-2026-09-21.sql (if not
   yet), then supabase/migration-partners-paid-2026-10-05.sql.
   Do this BEFORE deploying the site: the new partner-content reads the new columns.
5. Run the two commented queries at the bottom of that migration: list existing
   partners, then end any free (founding/trial) plans.
6. Deploy the site, then ship the app.
7. Optional, no code: Stripe > Settings > Billing > Customer portal > turn on the
   login link. Partners can update their card or cancel there with just their email.

## Adding a partner (they said yes)
1. Supabase SQL editor, edit and run:

    insert into public.partner_orgs (kind, name, venue_slugs, address, url, blurb, lat, lng)
    values ('restaurant', 'Te Deseo', array['american-airlines-center'],
            '2700 Olive St, Dallas, TX 75201', 'https://www.tedeseo.com/',
            'Latin kitchen with a rooftop, a short walk from the arena',
            32.7884, -96.8058)
    returning id;

   - venue_slugs: from the venue page URL, concertocity.com/venue/<slug>
   - lat/lng: right-click the restaurant in Google Maps to copy them (for the photo)
   - url: their reservation link, or their website
   - It starts as plan 'pending': nothing is public yet.
2. Send them their payment link (use the id it returned):
   Monthly: https://concertocity.com/.netlify/functions/partner-checkout?org=<id>&plan=monthly
   Annual:  https://concertocity.com/.netlify/functions/partner-checkout?org=<id>&plan=annual
3. When they pay, Stripe marks them paid and their card is live within 5 minutes.
   They land on a "Welcome to Concerto Partners" page. Email them their venue page link.

Renewals, failed payments and cancellations update on their own. A card stays up
3 days past each paid period so a late renewal never blinks it off; a cancelled or
unpaid subscription takes it down.

Cancelling with 30 days' notice: in Stripe, open their subscription > Cancel >
"At end of current period". Monthly ends within a month; annual runs to its end.

## Their Perk
They submit it in the Partner Console (/console/) or you add it. If you add it, set
org_id on the perks row to their partner_orgs.id so it shows on their card. Review,
then status = 'live'. Perks from unpaid partners never show.

## Demo partner (for screenshots)
    insert into public.partner_orgs (kind, name, plan, listed, venue_slugs, blurb, listed_until)
    values ('restaurant', 'Your Restaurant Here', 'paid', true,
            array['american-airlines-center','dos-equis-pavilion','dickies-arena'],
            'Your photo, your description, and your Perk, right here', current_date + 30);
Remove: delete from public.partner_orgs where name = 'Your Restaurant Here';

## Monthly report
Count partner_impression and partner_tap events by partner_id for the month:
analytics_events (app) and GA (website).

## What changed in this release
- App (concerto-native-partners.zip, unchanged): PartnerSection cards on venue pages
  and in Your Night; Perks page lists Perks, then partners without one.
- Website (concerto-site-partners.zip):
  - partner-content: paid only. Partner cards, Perks from partner orgs, and a venue's
    own edits/stage times/"Verified by the venue" require plan 'paid' in period.
  - partner-checkout (new): one payment link per partner, opens Stripe Checkout.
  - stripe-webhook: handles partner subscriptions (separate from Concerto+); also
    reads the period end from where newer Stripe API versions put it, which fixes
    Concerto+ expiry dates being saved empty.
  - partner-claim: new Console signups start 'pending', no free founding period.
  - Venue pages: partner cards under the header. /partners/restaurants rewritten.
    /partners-thank-you has a payment-received version.
