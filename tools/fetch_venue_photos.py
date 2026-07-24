#!/usr/bin/env python3
"""
Concerto venue photo pipeline.
Fetches one exterior photo per venue from Google Places into the site
repo, so the app (and site) get consistent, licensed venue imagery.

Run from the site repo root:
    GOOGLE_MAPS_API_KEY=xxx python3 tools/fetch_venue_photos.py

What it does:
  1. Reads data/venues.json (346 venues).
  2. Places Text Search: "<name> <city>" -> best place match.
  3. Downloads the first place photo at 1200px wide.
  4. Saves img/venues/<slug>.webp (JPEG fallback if Pillow missing).
  5. Writes data/venue_photos.json  { slug: "/img/venues/<slug>.webp" }
     and data/venue_photo_credits.json (required Google attributions).

Resumable: already-downloaded slugs are skipped, so re-run freely.
Cost: Text Search + Photo for 346 venues lands around $15 total at
current Places pricing. Photos may be used in your app/site with the
attributions kept (that's what the credits file is for).

After running: commit img/venues/ and both JSON files, deploy. The
app picks up data/venue_photos.json automatically; no app changes
needed. Hand-replace any photo by overwriting its webp: your curation
always wins.
"""
import json, os, sys, time, urllib.parse, urllib.request

KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
if not KEY:
    sys.exit('Set GOOGLE_MAPS_API_KEY (same key maps-key.js serves).')

BASE = 'https://maps.googleapis.com/maps/api/place'
OUT_DIR = 'img/venues'
os.makedirs(OUT_DIR, exist_ok=True)

venues = json.load(open('data/venues.json'))
photo_map = {}
credits = {}
if os.path.exists('data/venue_photos.json'):
    photo_map = json.load(open('data/venue_photos.json'))
if os.path.exists('data/venue_photo_credits.json'):
    credits = json.load(open('data/venue_photo_credits.json'))

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print('Pillow not installed: saving JPEG instead of WebP (pip install Pillow to fix).')

def get_json(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())

done = skipped = failed = 0
for v in venues:
    slug = v['id']
    if slug in photo_map and os.path.exists(photo_map[slug].lstrip('/')):
        skipped += 1
        continue
    query = urllib.parse.quote(f"{v['name']} {v['city']}")
    try:
        search = get_json(f'{BASE}/textsearch/json?query={query}&key={KEY}')
        result = (search.get('results') or [None])[0]
        photos = (result or {}).get('photos') or []
        if not photos:
            print(f'  no photo: {slug}')
            failed += 1
            continue
        ref = photos[0]['photo_reference']
        credits[slug] = photos[0].get('html_attributions', [])
        photo_url = f'{BASE}/photo?maxwidth=1200&photo_reference={ref}&key={KEY}'
        jpg_path = os.path.join(OUT_DIR, f'{slug}.jpg')
        urllib.request.urlretrieve(photo_url, jpg_path)
        if HAS_PIL:
            webp_path = os.path.join(OUT_DIR, f'{slug}.webp')
            Image.open(jpg_path).convert('RGB').save(webp_path, 'WEBP', quality=82)
            os.remove(jpg_path)
            photo_map[slug] = f'/{webp_path}'
        else:
            photo_map[slug] = f'/{jpg_path}'
        done += 1
        if done % 10 == 0:
            print(f'  {done} fetched...')
        time.sleep(0.15)
    except Exception as e:
        print(f'  error {slug}: {e}')
        failed += 1

json.dump(photo_map, open('data/venue_photos.json', 'w'), indent=1)
json.dump(credits, open('data/venue_photo_credits.json', 'w'), indent=1)
print(f'Done. fetched={done} skipped={skipped} failed={failed}')
print('Commit img/venues/, data/venue_photos.json, data/venue_photo_credits.json and deploy.')
