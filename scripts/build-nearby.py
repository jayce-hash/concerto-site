#!/usr/bin/env python3
"""Build data/nearby/<venue-id>.json from Google Places (New), in the format the site and app read.

  GOOGLE_PLACES_SERVER_KEY=... python3 scripts/build-nearby.py <venue-id> [<venue-id> ...]

Three tabs, like the existing files: Restaurants, Hotels, More (bars, cafes, parking). Places within
about a mile, nearest first. Google's terms allow keeping place IDs indefinitely but other Places
content only temporarily, so rerun this for all venues at least every 30 days (the `updated` date
in each file says when it last ran).
"""
import json, math, os, sys, time, urllib.request, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
KEY = os.environ.get('GOOGLE_PLACES_SERVER_KEY', '').strip()
TABS = [('restaurants', 'Restaurants', ['restaurant']), ('hotels', 'Hotels', ['lodging']), ('more', 'More', ['bar', 'cafe', 'parking'])]
PRICE = {'PRICE_LEVEL_FREE': 0, 'PRICE_LEVEL_INEXPENSIVE': 1, 'PRICE_LEVEL_MODERATE': 2, 'PRICE_LEVEL_EXPENSIVE': 3, 'PRICE_LEVEL_VERY_EXPENSIVE': 4}

def miles(a, b, c, d):
    r = 3958.8; p1, p2 = math.radians(a), math.radians(c); dp, dl = math.radians(c - a), math.radians(d - b)
    return 2 * r * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))

def nearby(lat, lng, types):
    body = json.dumps({'includedTypes': types, 'maxResultCount': 20, 'rankPreference': 'DISTANCE',
                       'locationRestriction': {'circle': {'center': {'latitude': lat, 'longitude': lng}, 'radius': 1600.0}}}).encode()
    req = urllib.request.Request('https://places.googleapis.com/v1/places:searchNearby', data=body, method='POST', headers={
        'Content-Type': 'application/json', 'X-Goog-Api-Key': KEY,
        'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location,places.priceLevel,places.types'})
    with urllib.request.urlopen(req, timeout=20) as r: return json.load(r).get('places', [])

def main():
    if not KEY: sys.exit('Set GOOGLE_PLACES_SERVER_KEY first.')
    ids = sys.argv[1:]
    if not ids: sys.exit(__doc__)
    venues = {v['id']: v for v in json.loads((ROOT / 'data/venues.json').read_text())}
    out = ROOT / 'data/nearby'; out.mkdir(exist_ok=True)
    for vid in ids:
        v = venues.get(vid)
        if not v: print(f'skip {vid}: not in data/venues.json'); continue
        tabs = {}
        for key, label, types in TABS:
            items = []
            for p in nearby(v['lat'], v['lng'], types):
                loc = p.get('location', {})
                items.append({'name': p.get('displayName', {}).get('text', ''), 'address': p.get('formattedAddress', ''),
                              'price': PRICE.get(p.get('priceLevel')), 'lat': loc.get('latitude'), 'lng': loc.get('longitude'),
                              'distance_mi': round(miles(v['lat'], v['lng'], loc.get('latitude', v['lat']), loc.get('longitude', v['lng'])), 2),
                              'place_id': p.get('id'), 'types': p.get('types', []), 'sponsored': False, 'partnerId': None, 'notes': None})
            items.sort(key=lambda x: x['distance_mi']); tabs[key] = {'label': label, 'items': items}
            time.sleep(0.2)
        (out / f'{vid}.json').write_text(json.dumps({'venueName': v['name'], 'city': v['city'], 'updated': datetime.date.today().isoformat(), 'tabs': tabs}, indent=2, ensure_ascii=False) + '\n')
        print(f'{vid}: ' + ', '.join(f"{len(t['items'])} {k}" for k, t in tabs.items()))

if __name__ == '__main__':
    main()
