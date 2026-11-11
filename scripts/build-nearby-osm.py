#!/usr/bin/env python3
"""Fill data/nearby/<venue-id>.json from OpenStreetMap, free, for venues Concerto has no places for.

  python3 scripts/build-nearby-osm.py --dry-run --limit 5     look at five venues, write nothing
  python3 scripts/build-nearby-osm.py                         every venue whose nearby file is empty or missing
  python3 scripts/build-nearby-osm.py the-fillmore-sf         just these venues
  python3 scripts/build-nearby-osm.py --limit 100             the first 100 empty venues (run again for the next 100)

No key and no fee: it asks the public Overpass API (OpenStreetMap's query service) for named
restaurants, bars, cafes and hotels within about a mile of each venue. It is polite about it:
one request per venue, a pause between venues, and it backs off when the service is busy.

What it writes matches the files the app and site already read (three tabs: Restaurants, Hotels,
More), with three differences:
  - no ratings, prices or photos (OpenStreetMap doesn't have them),
  - "cuisine" and "hours" where the place lists them, which the Google files never had,
  - "source": "osm" on the file and each place, so the app shows the required credit
    ("Places (c) OpenStreetMap contributors") and skips the Google photo lookup.

It never touches a file that already has places in it (those came from Google) unless --force.
Places are kept if they have a name and aren't a chain Concerto wouldn't suggest for a night out;
the ones with the most detail (cuisine, hours, a website, an address) come first, then the closest.
"""
import json, math, sys, time, datetime, urllib.request, urllib.parse, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
AGENT = 'ConcertoNearby/1.0 (concertocity.com; partners@concertocity.com)'
RADIUS_M = 1600          # about a mile, the same reach as the Google builder
KEEP = 12
PAUSE = 2.0              # seconds between venues
CHAIN_WORDS = ['7-eleven', 'starbucks', 'mcdonald', 'subway', 'taco bell', 'burger king', 'wendy', 'dunkin', 'domino',
               'pizza hut', 'kfc', 'jack in the box', 'sonic drive', 'circle k', 'vons', 'walgreens', 'cvs', 'tim hortons',
               'chick-fil-a', 'popeyes', 'arby', 'little caesars', 'papa john', 'panda express', 'chipotle', 'five guys',
               'costa coffee', 'greggs', 'pret a manger', 'ibis budget', 'motel 6', 'super 8', 'travelodge']
# OpenStreetMap tag -> (tab, the Google-style types the app already understands)
KINDS = {
    ('amenity', 'restaurant'): ('restaurants', ['restaurant', 'food']),
    ('amenity', 'bar'): ('more', ['bar']),
    ('amenity', 'pub'): ('more', ['pub', 'bar']),
    ('amenity', 'biergarten'): ('more', ['bar']),
    ('amenity', 'cafe'): ('more', ['cafe']),
    ('tourism', 'hotel'): ('hotels', ['hotel', 'lodging']),
}
LABELS = {'restaurants': 'Restaurants', 'hotels': 'Hotels', 'more': 'More'}
ONE = {'restaurants': 'Restaurant', 'hotels': 'Hotel', 'more': 'Bar or cafe'}


def miles(a, b, c, d):
    r = 3958.8; p1, p2 = math.radians(a), math.radians(c); dp, dl = math.radians(c - a), math.radians(d - b)
    return 2 * r * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def query(lat, lng):
    around = f'(around:{RADIUS_M},{lat},{lng})'
    return ('[out:json][timeout:40];('
            f'nwr{around}[amenity~"^(restaurant|bar|pub|biergarten|cafe)$"][name];'
            f'nwr{around}[tourism=hotel][name];'
            ');out center tags 400;')


def fetch(lat, lng, tries=4):
    """One Overpass request, trying the mirror and backing off when the service is busy."""
    body = urllib.parse.urlencode({'data': query(lat, lng)}).encode()
    wait = 5
    for attempt in range(tries):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(url, data=body, method='POST', headers={'User-Agent': AGENT, 'Content-Type': 'application/x-www-form-urlencoded'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r).get('elements', [])
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504): raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        time.sleep(wait); wait *= 2
    raise RuntimeError('OpenStreetMap is busy; try again later')


def address(tags):
    street = ' '.join(x for x in (tags.get('addr:housenumber'), tags.get('addr:street')) if x)
    parts = [street, tags.get('addr:city'), ' '.join(x for x in (tags.get('addr:state') or tags.get('addr:province'), tags.get('addr:postcode')) if x)]
    return ', '.join(p for p in parts if p)


def to_item(el, vlat, vlng):
    """One OpenStreetMap element as a Concerto nearby item, or None when it isn't one to suggest."""
    tags = el.get('tags') or {}
    name = (tags.get('name:en') or tags.get('name') or '').strip()
    kind = next((KINDS[k] for k in (('amenity', tags.get('amenity')), ('tourism', tags.get('tourism'))) if k in KINDS), None)
    lat = el.get('lat', (el.get('center') or {}).get('lat')); lng = el.get('lon', (el.get('center') or {}).get('lon'))
    if not name or not kind or lat is None or lng is None: return None
    if any(w in name.lower() for w in CHAIN_WORDS): return None
    if tags.get('disused') == 'yes' or tags.get('abandoned') == 'yes' or any(k.startswith(('disused:', 'abandoned:', 'was:')) for k in tags): return None
    if tags.get('access') == 'private': return None
    tab, types = kind
    cuisine = [c.strip().replace('_', ' ') for c in (tags.get('cuisine') or '').split(';') if c.strip()][:3]
    site = tags.get('website') or tags.get('contact:website') or ''
    item = {'name': name, 'address': address(tags), 'lat': round(float(lat), 6), 'lng': round(float(lng), 6),
            'distance_mi': round(miles(vlat, vlng, float(lat), float(lng)), 2),
            'types': types + [c.replace(' ', '_') + '_restaurant' for c in cuisine if tab == 'restaurants'],
            'sponsored': False, 'partnerId': None, 'notes': None, 'source': 'osm'}
    if cuisine: item['cuisine'] = cuisine
    if tags.get('opening_hours'): item['hours'] = tags['opening_hours'][:120]
    if site.startswith(('http://', 'https://')): item['website'] = site[:200]
    # How filled-in the listing is. A place with hours, a cuisine and a website is a real, current
    # business far more often than a bare name.
    item['_detail'] = sum(1 for k in ('cuisine', 'hours', 'website') if k in item) + (1 if item['address'] else 0)
    return tab, item


def build(elements, vlat, vlng):
    tabs = {k: [] for k in LABELS}
    seen = set()
    for el in elements:
        made = to_item(el, vlat, vlng)
        if not made: continue
        tab, item = made
        key = (tab, item['name'].lower())
        if key in seen: continue  # the same place mapped as both a point and a building
        seen.add(key); tabs[tab].append(item)
    out = {}
    for tab, items in tabs.items():
        items.sort(key=lambda i: (i['_detail'] == 0, i['distance_mi']))  # bare names last, then closest first
        for i in items: i.pop('_detail', None)
        out[tab] = {'label': LABELS[tab], 'items': items[:KEEP]}
    return out


def is_empty(path):
    if not path.exists(): return True
    try: d = json.loads(path.read_text())
    except Exception: return True
    return not any((t or {}).get('items') for t in (d.get('tabs') or {}).values())


def main(argv):
    flags = {a for a in argv if a.startswith('--') and a != '--limit'}
    limit = int(argv[argv.index('--limit') + 1]) if '--limit' in argv else None
    ids = [a for i, a in enumerate(argv) if not a.startswith('--') and (i == 0 or argv[i - 1] != '--limit')]
    dry, force = '--dry-run' in flags, '--force' in flags
    venues = json.loads((ROOT / 'data' / 'venues.json').read_text())
    by_id = {v['id']: v for v in venues}
    unknown = [i for i in ids if i not in by_id]
    if unknown: sys.exit('Not a Concerto venue id: ' + ', '.join(unknown))
    todo = [by_id[i] for i in ids] if ids else venues
    todo = [v for v in todo if v.get('lat') is not None and v.get('lng') is not None
            and (force or is_empty(ROOT / 'data' / 'nearby' / f"{v['id']}.json"))]
    if limit: todo = todo[:limit]
    if not todo: print('Nothing to do: every venue asked for already has places.'); return
    print(f"{'Looking at' if dry else 'Filling'} {len(todo)} venue(s) from OpenStreetMap{' (dry run, nothing is written)' if dry else ''}")
    wrote = thin = failed = 0
    today = datetime.date.today().isoformat()
    for n, v in enumerate(todo, 1):
        try: tabs = build(fetch(v['lat'], v['lng']), v['lat'], v['lng'])
        except Exception as e:
            failed += 1; print(f"  {n}/{len(todo)} {v['id']}: skipped ({e})"); time.sleep(PAUSE); continue
        counts = {k: len(t['items']) for k, t in tabs.items()}
        total = sum(counts.values())
        note = '' if total else '  (nothing mapped nearby: left as it was)'
        print(f"  {n}/{len(todo)} {v['id']}: {counts['restaurants']} restaurants, {counts['hotels']} hotels, {counts['more']} bars and cafes{note}")
        if dry:
            for k in LABELS:
                for i in tabs[k]['items'][:3]:
                    print(f"      {ONE[k]}: {i['name']} · {i['distance_mi']} mi" + (f" · {', '.join(i['cuisine'])}" if i.get('cuisine') else '') + (f" · {i['hours']}" if i.get('hours') else ''))
        elif total:
            path = ROOT / 'data' / 'nearby' / f"{v['id']}.json"
            path.write_text(json.dumps({'venueName': v.get('name', ''), 'city': v.get('city', ''), 'updated': today, 'source': 'osm',
                                        'attribution': '© OpenStreetMap contributors', 'tabs': tabs}, ensure_ascii=False, indent=1) + '\n')
            wrote += 1
        if not total: thin += 1
        time.sleep(PAUSE)
    print(f"Done. {'Would write' if dry else 'Wrote'} {len(todo) - thin - failed if dry else wrote} file(s); {thin} venue(s) had nothing mapped nearby; {failed} skipped (run again to retry).")


if __name__ == '__main__':
    main(sys.argv[1:])
