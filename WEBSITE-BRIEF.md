# Concerto website brief (Sep 21, 2026)

Adopted from the external website audit. The site is the front door to the app, not a
second version of it: explain Concerto immediately, convert to a saved show or a
download, and use venue/tour/setlist pages as the SEO acquisition engine.

## Done tonight (Priority 0)
- Homepage description was an unrendered template; fixed, reworded honestly, and a validator now rejects unresolved tokens.
- Deploy validator compares tokens, not whitespace; the full suite is green.
- "Near you this week" queries a real seven-day window and says so when nothing is on.
- Country comes from geolocation; venue pages pass their own country; venue events must match the venue name before they show as "tonight."
- Event cards open the show in Concerto; the ticket provider is a secondary link.
- Setlists are labeled by source: "Official tour playlist (Apple Music)" vs "Confirmed setlist from <show>". "What they have actually been playing" copy removed.
- Legal pages: no closing tags on void elements; web-app pages have real titles and one robots directive.
- Partner claims: ownership only from data/venue_domains.json (exact domain), never inferred from citations; duplicate venue orgs prevented; partner orgs created only after the email proves itself; founding date configurable.
- Ticketmaster proxy parses the referer hostname; partner URLs are https-only before reaching an href.
- Report wrong info confirms only on a successful response.
- Social proof carries an "as of" date; the homepage example never shows "0 days".

## Next (Priority 0/1, in order)
1. Rate limiting and daily ceilings on public functions; move public reads off the service-role key.
2. Privacy Policy and Terms rewritten for the current product (professional review).
3. Content-Security-Policy, HSTS, Permissions-Policy.
4. Homepage hierarchy: promise, one real product visual, App Store button, QR, then "Near you".
5. Individual show pages (only when data is complete) and read-only shared Your Night pages.
6. One App Store link helper with placement tracking (hero, header, venue, tour, setlist, QR).
7. Precomputed venue-photo manifest with a per-session request ceiling.
8. Dynamic Open Graph images; MusicEvent structured data on show pages.
9. Heading structure (H3 for cards), skip link, directory accessibility.
10. Exclude unused originals and repo-only material from the deploy.

## Definition of done
Every validator passes; a visitor understands Concerto in five seconds; an event becomes a
saved show instead of a link away; "this week" means this week; setlists and playlists are
labeled honestly; venue events match the venue; public functions have abuse protection;
partner claims cannot be approved by inference; legal pages describe the current product.
