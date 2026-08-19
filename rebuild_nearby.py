#!/usr/bin/env python3
"""
Regenerate data/nearby.json with more results per venue and real,
granular place types.

WHY THIS EXISTS
The previous nearby.json (whatever generated it is not in this repo)
capped every venue at exactly 8 restaurants, 6 hotels, and 6 things to
do. 319 of 346 venues sat exactly at the restaurant cap, which is not
what real data looks like -- it is an artificial limit. It also stored
only generic types ('restaurant', 'food', 'bar'), so filtering by
cuisine was impossible: Keens Steakhouse carried no 'steakhouse' tag
at all.

WHAT CHANGED
1. More results. Google's Nearby Search (New) caps maxResultCount at
   20 per request and has NO pagination (pagetoken is explicitly
   unsupported in the new API). So depth comes from multiple requests
   with different includedTypes, merged and deduped by place_id,
   rather than one bigger request.
2. Real types. Requesting specific types like 'italian_restaurant'
   and 'steak_house' means Google returns those granular primary
   types, which is what makes cuisine filtering possible at all.

COST AWARENESS
Roughly 4,500 Nearby Search requests for all 346 venues (13 per
venue). The field mask deliberately excludes rating and review count,
which keeps every request in the Pro SKU rather than Enterprise.
That matters more than it sounds: Pro includes 5,000 free calls per
month, Enterprise only 1,000, and Google retired the old $200 monthly
credit in March 2025. With rating fields included this run would cost
roughly $120; without them it should land inside the free Pro
allowance. Verify against current Google pricing before running, and
use --dry-run and --limit to check the plan first.

USAGE
  export GOOGLE_PLACES_SERVER_KEY=...
  python3 rebuild_nearby.py --limit 3          # test on 3 venues
  python3 rebuild_nearby.py --dry-run          # show plan, call nothing
  python3 rebuild_nearby.py                    # full run
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent
VENUES_PATH = ROOT / "data" / "venues.json"
NEARBY_PATH = ROOT / "data" / "nearby.json"
NEARBY_DIR = ROOT / "data" / "nearby"

ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"

# Only what's actually used downstream, and deliberately NOT
# `rating` or `userRatingCount`. Google bills at the highest tier of
# any requested field: adding rating alone moves a request from Pro
# ($32/1,000) to Enterprise ($35/1,000), and Pro includes 5,000 free
# calls per month against Enterprise's 1,000. Since the cards stopped
# showing star ratings entirely (they read like a Yelp panel, not
# Concerto), paying the Enterprise rate for data nothing displays
# would be pure waste. Dropping those two fields is the difference
# between this run costing real money and landing inside the free
# allowance.
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.priceLevel",
    "places.types",
    "places.primaryType",
])

# Each tab is several requests, not one. Google caps a single request
# at 20 results with no pagination, so breadth comes from asking for
# different specific types and merging. The cuisine-level types are
# the whole point of the rewrite: asking for 'italian_restaurant'
# directly is what gets that type back in the response.
TAB_QUERIES = {
    "restaurants": [
        ["restaurant"],
        ["italian_restaurant", "pizza_restaurant", "mexican_restaurant",
         "chinese_restaurant", "japanese_restaurant", "thai_restaurant"],
        ["steak_house", "seafood_restaurant", "barbecue_restaurant",
         "american_restaurant", "french_restaurant", "indian_restaurant"],
        ["bar", "pub", "wine_bar", "bar_and_grill"],
        ["cafe", "coffee_shop", "bakery", "breakfast_restaurant"],
        ["ramen_restaurant", "sushi_restaurant", "vegan_restaurant",
         "vegetarian_restaurant", "sandwich_shop", "fast_food_restaurant"],
    ],
    "hotels": [
        ["hotel", "lodging"],
        ["resort_hotel", "extended_stay_hotel", "bed_and_breakfast",
         "motel", "inn", "hostel"],
    ],
    "more": [
        ["tourist_attraction", "museum", "art_gallery"],
        ["park", "zoo", "aquarium", "amusement_park"],
        ["shopping_mall", "clothing_store", "book_store", "department_store"],
        ["movie_theater", "bowling_alley", "casino", "night_club"],
        ["spa", "gym", "library", "performing_arts_theater"],
    ],
}

# Radius per tab, in meters. Restaurants and things to do should be
# genuinely walkable before a show; hotels can be slightly further
# since people will drive or ride to a hotel but not to dinner.
TAB_RADIUS = {"restaurants": 1200, "hotels": 2000, "more": 2000}

# How many to keep per tab after merging and ranking. Well above the
# 6 the app displays, so the type filters have real depth to work
# with instead of filtering an already-truncated list.
TAB_KEEP = {"restaurants": 24, "hotels": 16, "more": 24}

PRICE_MAP = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}


def miles_between(lat1, lng1, lat2, lng2):
    from math import radians, sin, cos, asin, sqrt
    r = 3958.8
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return round(2 * r * asin(sqrt(a)), 2)


def search_nearby(key, lat, lng, radius, included_types):
    """
    Retries once without any type Google rejects.

    Google returns 400 INVALID_ARGUMENT naming the exact unsupported
    type ("Unsupported types: cocktail_lounge."). Rather than lose a
    whole batch to one bad name, drop the named type and retry. This
    also means the type lists above can include plausible-but-
    unverified names safely: a wrong one costs one extra request, not
    a silently missing category.
    """
    attempted = list(included_types)

    for _ in range(2):
        body = json.dumps({
            "includedTypes": attempted,
            "maxResultCount": 20,
            "rankPreference": "POPULARITY",
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius),
                }
            },
        }).encode()

        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read()).get("places", [])
        except urllib.error.HTTPError as e:
            detail = e.read().decode()
            if e.code == 400 and "Unsupported types:" in detail:
                bad = detail.split("Unsupported types:")[1].split(".")[0].strip()
                bad_names = {b.strip() for b in bad.split(",")}
                remaining = [t for t in attempted if t not in bad_names]
                if remaining and remaining != attempted:
                    print(f"    dropping unsupported type(s): {', '.join(sorted(bad_names))}")
                    attempted = remaining
                    continue
            print(f"    HTTP {e.code}: {detail[:200]}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"    request failed: {e}", file=sys.stderr)
            return []
    return []


def build_item(place, venue_lat, venue_lng):
    loc = place.get("location") or {}
    lat, lng = loc.get("latitude"), loc.get("longitude")
    if lat is None or lng is None:
        return None
    name = (place.get("displayName") or {}).get("text")
    if not name:
        return None

    # primaryType first so the most specific, most useful type for
    # filtering leads the list rather than getting buried behind
    # generic 'food' / 'point_of_interest' entries.
    types = place.get("types") or []
    primary = place.get("primaryType")
    if primary and primary in types:
        types = [primary] + [t for t in types if t != primary]
    elif primary:
        types = [primary] + types

    return {
        "name": name,
        "address": place.get("formattedAddress"),
        # rating/reviews deliberately absent: not fetched (see
        # FIELD_MASK), not displayed, and the reason this run is
        # cheap. Old values are preserved on merge below rather than
        # overwritten with nulls, so nothing already stored is lost.
        "price": PRICE_MAP.get(place.get("priceLevel")),
        "lat": lat,
        "lng": lng,
        "distance_mi": miles_between(venue_lat, venue_lng, lat, lng),
        "place_id": place.get("id"),
        "types": types,
        # Preserved so existing partner/editorial data shape stays
        # intact; this script never invents either.
        "sponsored": False,
        "partnerId": None,
        "notes": None,
    }


def build_tab(key, venue, tab_key, dry_run=False):
    lat, lng = venue["lat"], venue["lng"]
    radius = TAB_RADIUS[tab_key]
    seen = {}
    calls = 0

    for included in TAB_QUERIES[tab_key]:
        if dry_run:
            calls += 1
            continue
        for place in search_nearby(key, lat, lng, radius, included):
            pid = place.get("id")
            if not pid or pid in seen:
                continue
            item = build_item(place, lat, lng)
            if item:
                seen[pid] = item
        calls += 1
        time.sleep(0.12)  # gentle on the rate limit

    items = list(seen.values())
    # Pure distance sort. "Near the venue" is the entire promise, and
    # rating is no longer fetched to keep this run inside the cheaper
    # Pro tier, so there's nothing to break ties with -- which is
    # fine, since distance is the honest ranking for a show night
    # anyway.
    items.sort(key=lambda i: i["distance_mi"])
    return items[: TAB_KEEP[tab_key]], calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only process N venues (for testing)")
    ap.add_argument("--dry-run", action="store_true", help="count requests, call nothing")
    ap.add_argument("--only", help="single venue slug, for spot checks")
    args = ap.parse_args()

    key = os.environ.get("GOOGLE_PLACES_SERVER_KEY")
    if not key and not args.dry_run:
        sys.exit("GOOGLE_PLACES_SERVER_KEY not set")

    venues = json.loads(VENUES_PATH.read_text())
    existing = json.loads(NEARBY_PATH.read_text()) if NEARBY_PATH.exists() else {}

    targets = [v for v in venues if v.get("lat") is not None and v.get("lng") is not None]
    if args.only:
        targets = [v for v in targets if v.get("id") == args.only or v.get("slug") == args.only]
    if args.limit:
        targets = targets[: args.limit]

    print(f"venues to process: {len(targets)}")
    total_calls = 0
    processed = []  # slugs that actually got real data this run
    out = dict(existing)

    for n, venue in enumerate(targets, 1):
        slug = venue.get("id") or venue.get("slug")
        name = venue.get("name", slug)
        print(f"[{n}/{len(targets)}] {name}")

        tabs = {}
        failed = False
        for tab_key, label in [("restaurants", "Restaurants"), ("hotels", "Hotels"), ("more", "More")]:
            items, calls = build_tab(key, venue, tab_key, args.dry_run)
            total_calls += calls
            tabs[tab_key] = {"label": label, "items": items}
            if not args.dry_run:
                print(f"    {tab_key}: {len(items)}")

        if args.dry_run:
            continue

        # Never overwrite real data with an empty result. A venue that
        # comes back completely empty means the requests failed (bad
        # key, blocked API, network), not that there is genuinely
        # nothing near an arena. Writing that would destroy working
        # data, which is exactly what happened on the first real run
        # when the API key lacked SearchNearby permission.
        if not any(len(t["items"]) for t in tabs.values()):
            print("    all tabs empty, skipping (keeping existing data)")
            failed = True

        if failed:
            continue

        # Preserve any human-set fields from the old data rather than
        # overwrite curation with fresh API output. Editorial notes
        # and partner flags are the whole reason Top Picks exists.
        prev = existing.get(slug, {})
        for tab_key, tab in tabs.items():
            prev_items = {i["name"]: i for i in prev.get("tabs", {}).get(tab_key, {}).get("items", [])}
            for item in tab["items"]:
                old = prev_items.get(item["name"])
                if not old:
                    continue
                if old.get("notes"):
                    item["notes"] = old["notes"]
                if old.get("sponsored"):
                    item["sponsored"] = True
                if old.get("partnerId"):
                    item["partnerId"] = old["partnerId"]
                # Carry forward previously-fetched ratings rather than
                # drop them: they're already paid for and stored, and
                # re-fetching them would cost Enterprise-tier pricing
                # for data the UI doesn't even show.
                if old.get("rating") is not None:
                    item["rating"] = old["rating"]
                if old.get("reviews") is not None:
                    item["reviews"] = old["reviews"]

        out[slug] = {
            "venueName": venue.get("name"),
            "city": venue.get("city"),
            "updated": time.strftime("%Y-%m-%d"),
            "tabs": tabs,
        }
        processed.append(slug)

    if args.dry_run:
        print(f"\nDRY RUN: would make ~{total_calls} Nearby Search requests")
        print("Check current Places API pricing and your remaining free credit")
        print("before running this for real.")
        return

    if not processed:
        print("\nNothing was successfully processed. Existing data left untouched.")
        print("If you saw 403 errors above, the API key does not have Places API")
        print("(New) enabled, or has API restrictions blocking SearchNearby.")
        print("Fix that in Google Cloud Console under Credentials, then re-run.")
        return

    NEARBY_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {NEARBY_PATH} ({len(out)} venues)")

    # Per-venue split the native app fetches. Only rewrite the files
    # actually processed this run -- rewriting all 346 every time
    # churns the whole directory in git for no reason and makes it
    # impossible to see what a partial run actually changed.
    NEARBY_DIR.mkdir(parents=True, exist_ok=True)
    for slug in processed:
        (NEARBY_DIR / f"{slug}.json").write_text(json.dumps(out[slug]))
    print(f"wrote {len(processed)} files to {NEARBY_DIR}")
    print(f"total requests made: {total_calls}")


if __name__ == "__main__":
    main()
