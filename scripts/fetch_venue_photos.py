#!/usr/bin/env python3
"""
fetch_venue_photos.py: venue exterior photos for all 346 venues.

Run from the site repo root:
    GOOGLE_MAPS_API_KEY=xxxx python3 scripts/fetch_venue_photos.py

For each venue in data/venues.json:
  1. Google Places Text Search: "<name> <city>"
  2. First photo reference -> Place Photo API (maxwidth 1200)
  3. Saved to img/venues/<slug>.webp (skipped if it already exists,
     so the run is resumable and hand-replaced photos survive)
  4. data/venue_photos.json written as { slug: "/img/venues/<slug>.webp" }

The app reads data/venue_photos.json and prefers these over
Ticketmaster's photos. Replace any file by hand with a better shot
(same filename) and the app updates on next fetch: your top 50
venues deserve hand-picked exteriors over time.

Costs: ~2 Places API calls per venue (~700 total). Text Search and
Photos are billed per Google's current rates: expect a few dollars,
covered by the monthly free credit for most accounts. Requires:
pip install requests pillow
"""
import json
import os
import sys
import time
from io import BytesIO

import requests
from PIL import Image

KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
if not KEY:
    sys.exit('Set GOOGLE_MAPS_API_KEY first.')

VENUES = json.load(open('data/venues.json'))
OUT_DIR = 'img/venues'
MANIFEST = 'data/venue_photos.json'
os.makedirs(OUT_DIR, exist_ok=True)

manifest = {}
if os.path.exists(MANIFEST):
    manifest = json.load(open(MANIFEST))

ok = skipped = failed = 0
for v in VENUES:
    slug, name, city = v['id'], v['name'], v['city']
    out_path = f'{OUT_DIR}/{slug}.webp'
    if os.path.exists(out_path):
        manifest[slug] = f'/{out_path}'
        skipped += 1
        continue
    try:
        search = requests.get(
            'https://maps.googleapis.com/maps/api/place/textsearch/json',
            params={'query': f'{name} {city}', 'key': KEY},
            timeout=15,
        ).json()
        results = search.get('results') or []
        photos = (results[0].get('photos') or []) if results else []
        if not photos:
            print(f'  no photo: {name}')
            failed += 1
            continue
        ref = photos[0]['photo_reference']
        img_res = requests.get(
            'https://maps.googleapis.com/maps/api/place/photo',
            params={'photo_reference': ref, 'maxwidth': 1200, 'key': KEY},
            timeout=30,
        )
        img = Image.open(BytesIO(img_res.content)).convert('RGB')
        img.save(out_path, 'WEBP', quality=82)
        manifest[slug] = f'/{out_path}'
        ok += 1
        print(f'  saved: {name}')
        time.sleep(0.15)  # be polite
    except Exception as e:
        failed += 1
        print(f'  failed: {name}: {e}')

json.dump(manifest, open(MANIFEST, 'w'), indent=1, sort_keys=True)
print(f'\nDone. {ok} fetched, {skipped} already present, {failed} without photos.')
print(f'Manifest: {MANIFEST} ({len(manifest)} entries). Commit img/venues/ and the manifest, deploy, and the app goes image-forward.')
