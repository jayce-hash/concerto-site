# Partner Console setup and offer review

1. If the partner tables do not exist, apply `migration-partners-2026-09-18.sql` in Supabase. Do not rerun the original migration on an existing setup: its policy creation is not idempotent.
2. Apply `migration-perk-review-2026-09-21.sql` before accepting offers. It keeps existing data and limits members to submitting/revising drafts. Publication requires a trusted administrator or service role. Until applied, the original broad policy still allows members to publish directly.
3. Confirm `https://concertocity.com/console/` is an allowed Supabase Authentication redirect.
4. Confirm Netlify has `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. Never put the service key into a public page or the app.
5. Check form notifications for the four existing Netlify partnership forms and the contact form. A thank-you page is not proof of email delivery.

## Operating the program

An inquiry starts a conversation. Confirm the organization and authorized representative, venue/tour fit, benefit, dates, redemption instructions, restrictions, placements, responsibilities, fees if applicable, and reporting before launch. Do not promise an audience size, bookings, sales, ticket access, or a review deadline.

The Console submits offers as `draft`. In Supabase, review the `perks` row and verify the link and terms with the partner. Set `status=live` only after approval; set `paused` to withdraw it. Changing a draft to live does not notify a partner automatically. An admin must handle communication separately. There is no new automatic partner billing in this release; commercial terms are agreed directly. Existing billing integration is unchanged.

Every Perk must have a specific benefit, redemption terms, applicable venues or a tour, and valid dates. An editorial recommendation or paid placement alone is not a Perk. Use the details field for membership requirements, purchase requirements, exclusions, and eligible show dates. For artist offers, select the exact tour. For venues hosting multiple events on one day, include the Ticketmaster event ID with confirmed stage times.

Venue claims retain the existing email-domain verification flow. Venue guidance publishes directly after that verification. Review unusual changes; do not describe historical estimates as venue-confirmed times.

## Data and reporting

Console writes go to Supabase under row-level security. App and website read `/.netlify/functions/partner-content`, cached for up to five minutes, then merge venue guidance over the static researched baseline. All offer routes filter future/expired offers, missing benefits, and missing terms. Invalid external offer links are removed. Failures return a retryable error rather than a false empty result.

The dashboard shows recorded activity for the latest recorded month, not guaranteed reach or conversions. The existing reporting view groups by partner name; keep names distinct. Offer-load events are not verified human views. For paid campaigns or conversion guarantees, arrange appropriate attribution before agreeing on deliverables. No live database changes or email deliveries were performed while preparing these ZIPs.
