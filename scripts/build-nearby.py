#!/usr/bin/env python3
"""Build data/nearby/<venue-id>.json from Google Places (New), in the format the site and app read.

  GOOGLE_PLACES_SERVER_KEY=... python3 scripts/build-nearby.py <venue-id> [<venue-id> ...]
  GOOGLE_PLACES_SERVER_KEY=... python3 scripts/build-nearby.py --top     (the venues with Exit Plan data, plus Intuit Dome)

Three tabs, like the existing files: Restaurants, Hotels, More (bars and cafes).

What a fan would actually pick, not just what's closest: Google ranks by popularity within about
a mile, then Concerto drops convenience stores, grocery stores, gas stations and other places
that aren't somewhere you'd plan a night around, and anything with too few or too low reviews.
The best of what's left comes first, with closer places breaking ties. Plan Your Night reads
these lists, so their quality is the planner's quality.

Google's terms allow keeping place IDs indefinitely but other Places content only temporarily,
so rerun this for all venues at least every 30 days (the `updated` date in each file says when).
"""
import json, math, os, sys, time, urllib.request, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
KEY = os.environ.get('GOOGLE_PLACES_SERVER_KEY', '').strip()

# (tab key, label, included types, minimum rating, minimum reviews)
TABS = [('restaurants', 'Restaurants', ['restaurant'], 4.0, 80),
        ('hotels', 'Hotels', ['hotel'], 3.8, 80),
        ('more', 'More', ['bar', 'wine_bar', 'pub', 'cafe', 'coffee_shop'], 4.0, 50)]
# Never a planned stop on a night out.
# EXCLUDE goes to Google (long-standing type names only, so the request never fails on one);
# NOT_A_STOP is checked here too, against each place's primary type.
EXCLUDE = ['convenience_store', 'grocery_store', 'supermarket', 'gas_station', 'liquor_store', 'pharmacy',
           'drugstore', 'department_store', 'gym', 'motel', 'campground', 'rv_park', 'hostel']
NOT_A_STOP = set(EXCLUDE) | {'discount_store', 'warehouse_store', 'food_store', 'market', 'fitness_center', 'parking'}
# Chains a planner shouldn't suggest for dinner; still fine to find on your own in Maps.
CHAIN_WORDS = ['7-eleven', 'starbucks', "mcdonald", 'subway', 'taco bell', 'burger king', 'wendy',
               'dunkin', 'domino', 'pizza hut', 'kfc', 'jack in the box', 'sonic drive', 'circle k', 'vons', 'walgreens', 'cvs']
# A place's main category must be food, drink or a place to stay.
PLAN_WORDS = ('restaurant', 'bar', 'pub', 'cafe', 'coffee', 'diner', 'steak', 'grill', 'bakery', 'brewery', 'winery', 'food', 'hotel', 'inn', 'lodging', 'bed_and_breakfast')
PRICE = {'PRICE_LEVEL_FREE': 0, 'PRICE_LEVEL_INEXPENSIVE': 1, 'PRICE_LEVEL_MODERATE': 2, 'PRICE_LEVEL_EXPENSIVE': 3, 'PRICE_LEVEL_VERY_EXPENSIVE': 4}
KEEP = 12

def miles(a, b, c, d):
    r = 3958.8; p1, p2 = math.radians(a), math.radians(c); dp, dl = math.radians(c - a), math.radians(d - b)
    return 2 * r * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))

def nearby(lat, lng, types):
    body = json.dumps({'includedTypes': types, 'excludedPrimaryTypes': EXCLUDE, 'maxResultCount': 20, 'rankPreference': 'POPULARITY',
                       'locationRestriction': {'circle': {'center': {'latitude': lat, 'longitude': lng}, 'radius': 1600.0}}}).encode()
    req = urllib.request.Request('https://places.googleapis.com/v1/places:searchNearby', data=body, method='POST', headers={
        'Content-Type': 'application/json', 'X-Goog-Api-Key': KEY,
        'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location,places.priceLevel,places.types,places.primaryType,places.rating,places.userRatingCount,places.businessStatus'})
    with urllib.request.urlopen(req, timeout=20) as r: return json.load(r).get('places', [])

def worth_planning(p, min_rating, min_reviews):
    name = p.get('displayName', {}).get('text', '').lower()
    if p.get('businessStatus') not in (None, 'OPERATIONAL'): return False
    if p.get('primaryType') in NOT_A_STOP: return False
    pt = p.get('primaryType') or ''
    if pt and not any(w in pt for w in PLAN_WORDS): return False  # a cinema or stadium that sells food is not dinner
    if any(w in name for w in CHAIN_WORDS): return False
    return (p.get('rating') or 0) >= min_rating and (p.get('userRatingCount') or 0) >= min_reviews

def score(item):
    # Rating counts most, review volume adds confidence, distance breaks ties (about a 0.1 point
    # penalty per extra half mile).
    return item['rating'] + 0.15 * math.log10(max(item['reviews'], 1)) - 0.2 * item['distance_mi']

def main():
    if not KEY: sys.exit('Set GOOGLE_PLACES_SERVER_KEY first.')
    ids = sys.argv[1:]
    if ids == ['--top']:
        ids = sorted(set(json.loads((ROOT / 'data/exit_plan.json').read_text())) | {'intuit-dome'})
    if not ids: sys.exit(__doc__)
    venues = {v['id']: v for v in json.loads((ROOT / 'data/venues.json').read_text())}
    out = ROOT / 'data/nearby'; out.mkdir(exist_ok=True)
    for vid in ids:
        v = venues.get(vid)
        if not v: print(f'skip {vid}: not in data/venues.json'); continue
        path = out / f'{vid}.json'
        old = json.loads(path.read_text()) if path.exists() else {}
        tabs = {}
        for key, label, types, min_rating, min_reviews in TABS:
            items = []
            try: found = nearby(v['lat'], v['lng'], types)
            except Exception as err: print(f'  {vid} {key}: {err}'); found = []
            for p in found:
                if not worth_planning(p, min_rating, min_reviews): continue
                loc = p.get('location', {})
                items.append({'name': p.get('displayName', {}).get('text', ''), 'address': p.get('formattedAddress', ''),
                              'price': PRICE.get(p.get('priceLevel')), 'lat': loc.get('latitude'), 'lng': loc.get('longitude'),
                              'distance_mi': round(miles(v['lat'], v['lng'], loc.get('latitude', v['lat']), loc.get('longitude', v['lng'])), 2),
                              'place_id': p.get('id'), 'types': p.get('types', []), 'primaryType': p.get('primaryType'),
                              'rating': p.get('rating'), 'reviews': p.get('userRatingCount'),
                              'sponsored': False, 'partnerId': None, 'notes': None})
            items.sort(key=score, reverse=True)
            if not items and old.get('tabs', {}).get(key, {}).get('items'):
                print(f'  {vid} {key}: nothing passed the filter, kept the previous list')
                tabs[key] = old['tabs'][key]
            else:
                tabs[key] = {'label': label, 'items': items[:KEEP]}
            time.sleep(0.2)
        path.write_text(json.dumps({'venueName': v['name'], 'city': v['city'], 'updated': datetime.date.today().isoformat(), 'tabs': tabs}, indent=2, ensure_ascii=False) + '\n')
        print(f'{vid}: ' + ', '.join(f"{len(t['items'])} {k}" for k, t in tabs.items()))

if __name__ == '__main__':
    main()
