# Concerto Picks — deploy notes

Two files. Both drop into your existing repo, no build step, no new dependencies.

## 1. picks.html  → repo root
The fan-facing discovery page. Same nav, tokens, and fonts as index.html.

- Pulls live data from `/.netlify/functions/top-picks`, falls back to `/data/top_picks.json`,
  then to a small embedded set so it never renders empty. (The embedded block is clearly
  commented and safe to delete once your static JSON is reliably reachable.)
- Groups each venue's picks by the night: Before the show / Quick bite / After the encore / Stay.
  A pick's moment is read from an optional `moment` field, and inferred from its notes if absent,
  so it works on your current data today with zero edits.
- "Open the full guide" deep-links into your existing city-guide engine (`/cityguide/<slugnodash>`)
  for the map and walking directions, so this page is the browse layer and the guide stays the map layer.
- Reuses your existing tap tracking: outbound taps fire to `/.netlify/functions/track` with the
  pick's `trackingId` (event `picks-maps`), so engagement on this surface lands in `placement_taps`
  alongside the city guide.

## 2. add_picks_links.py  → run from repo root
Wires Picks into the rest of the site. Idempotent.

    python3 add_picks_links.py          # preview (dry run)
    python3 add_picks_links.py --apply  # write changes

It adds Picks to the desktop nav and mobile menu on the 26 marketing pages, and to the footer
Tools column on 425 pages (every tour, venue, and setlist page). The footer link is the part that
routes your real setlist/tour traffic into Picks. Re-running it does nothing once applied.

## Turning a pick into a paid partner (no code, tier-ready)
In the Google Sheet that feeds top-picks, set a row's `tier` to `partner`, give it a `partnerId`,
and optionally a `badge`. The page automatically elevates it (navy + gold card, partner badge) and
keeps counting its taps. Pricing stays flat at $1,000 for now; the data model already carries
`partnerId` and `term`, so scope tiers ($1,500 / $2,000 across multiple venues) only need a small
partners registry keyed by `partnerId` later, not a rebuild.

## Optional next step
A prominent in-body CTA on individual tour pages ("Headed to this venue? Plan your night →")
would convert better than the footer link. It's a heavier edit across 77 varied pages, so it's
left out of this pass. Easy to add once you've seen Picks live.
