#!/usr/bin/env python3
"""
Concerto venue photo pipeline, v2 (Wikimedia edition).

WHY THE CHANGE: the v1 Google Places approach was flagged correctly.
Google's Places terms prohibit bulk-downloading, permanently storing,
and rehosting place photos; a credits JSON alone doesn't satisfy
display requirements. So v2 uses Wikimedia/Wikipedia imagery instead:
freely licensed venue photos that MAY be stored and rehosted, with
attribution (which the app now displays on the venue hero). No API
key. No cost. No ToS exposure.

Run from the site repo root:
    python3 tools/fetch_venue_photos.py            # fetch
    python3 tools/fetch_venue_photos.py --review   # rebuild review page only

What it does per venue:
  1. MediaWiki geosearch AT THE VENUE'S OWN COORDINATES (500 m) to
     find its Wikipedia article: coordinates are the match check, so
     "First Avenue" the club never matches First Avenue the street.
  2. Pulls the article's lead image at 1200 px.
  3. Reads the image's license + author from Commons metadata; skips
     non-free images automatically.
  4. Saves img/venues/<slug>.webp (JPEG if Pillow missing).
  5. Appends to data/venue_photos.json:
       { slug: { "src": "/img/venues/<slug>.webp",
                  "credit": "Photo: <author>, <license>, via Wikimedia" } }
     written ATOMICALLY AFTER EVERY VENUE, so Ctrl+C loses nothing;
     re-running resumes where it stopped.
  6. Writes review.html: a gallery of every match (name, photo,
     credit). Open it, eyeball the matches, and for any wrong one:
     add its slug to data/venue_photo_excludes.json (a JSON array),
     delete its webp, re-run. Excluded slugs are never fetched again;
     hand-place your own photo instead and add it to the JSON map.

Coverage will be strong for arenas/amphitheaters/theaters with
Wikipedia articles (most of the 346) and honest about the rest: no
match means the app keeps its Ticketmaster-then-monogram fallback.
"""
import json, os, sys, time, urllib.parse, urllib.request

API = 'https://en.wikipedia.org/w/api.php'
HEADERS = {'User-Agent': 'ConcertoVenuePhotos/2.0 (concertocity.com; support@concertocity.com)'}
OUT_DIR = 'img/venues'
MAP_PATH = 'data/venue_photos.json'
EXCL_PATH = 'data/venue_photo_excludes.json'

os.makedirs(OUT_DIR, exist_ok=True)
venues = json.load(open('data/venues.json'))
photo_map = json.load(open(MAP_PATH)) if os.path.exists(MAP_PATH) else {}
excludes = set(json.load(open(EXCL_PATH))) if os.path.exists(EXCL_PATH) else set()

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print('Pillow not installed: saving JPEG instead of WebP (pip install Pillow to fix).')

def api(params):
    params = dict(params, format='json')
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def save_map():
    tmp = MAP_PATH + '.tmp'
    json.dump(photo_map, open(tmp, 'w'), indent=1)
    os.replace(tmp, MAP_PATH)

def write_review():
    rows = []
    by_slug = {v['id']: v for v in venues}
    for slug, entry in sorted(photo_map.items()):
        v = by_slug.get(slug, {})
        rows.append(
            f"<div class='card'><img src='..{entry['src']}' loading='lazy'>"
            f"<h3>{v.get('name', slug)}</h3><p>{slug}</p>"
            f"<small>{entry.get('credit', '')}</small></div>")
    html = (
        "<!doctype html><meta charset='utf-8'><title>Venue photo review</title>"
        "<style>body{font-family:sans-serif;background:#121E36;color:#F8F9F9;padding:20px}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}"
        ".card{background:#1C2B4A;border-radius:12px;padding:10px}"
        "img{width:100%;height:160px;object-fit:cover;border-radius:8px}"
        "h3{margin:8px 0 0;font-size:15px}p{margin:2px 0;color:#C9A84C;font-size:12px}"
        "small{color:#8A91A3;font-size:10px}</style>"
        f"<h1>{len(photo_map)} venue photos</h1>"
        "<p>Wrong match? Add its slug to data/venue_photo_excludes.json, delete the webp, re-run.</p>"
        "<div class='grid'>" + ''.join(rows) + '</div>')
    open('tools/review.html', 'w').write(html)
    print(f'Review gallery: tools/review.html ({len(photo_map)} photos)')

if '--review' in sys.argv:
    write_review()
    sys.exit(0)

FREE_LICENSE_HINTS = ('cc', 'public domain', 'pd', 'gfdl', 'attribution')
done = skipped = nomatch = 0
for v in venues:
    slug = v['id']
    if slug in excludes or slug in photo_map:
        skipped += 1
        continue
    try:
        geo = api({
            'action': 'query', 'list': 'geosearch',
            'gscoord': f"{v['lat']}|{v['lng']}", 'gsradius': 500, 'gslimit': 5,
        })
        pages = geo.get('query', {}).get('geosearch', [])
        # prefer a title that shares a word with the venue name
        name_words = {w.lower() for w in v['name'].split() if len(w) > 3}
        page = next(
            (p for p in pages if name_words & {w.lower() for w in p['title'].split()}),
            pages[0] if pages else None,
        )
        if not page:
            nomatch += 1
            continue
        info = api({
            'action': 'query', 'titles': page['title'],
            'prop': 'pageimages|pageprops', 'piprop': 'original|name', 'pithumbsize': 1200,
        })
        p = next(iter(info['query']['pages'].values()))
        img_url = p.get('original', {}).get('source')
        img_name = p.get('pageimage')
        if not img_url or not img_name:
            nomatch += 1
            continue
        meta = api({
            'action': 'query', 'titles': f'File:{img_name}',
            'prop': 'imageinfo', 'iiprop': 'extmetadata',
        })
        mp = next(iter(meta['query']['pages'].values()))
        ext = (mp.get('imageinfo') or [{}])[0].get('extmetadata', {})
        license_name = ext.get('LicenseShortName', {}).get('value', '')
        artist = ext.get('Artist', {}).get('value', '')
        import re as _re
        artist = _re.sub(r'<[^>]+>', '', artist).strip()
        if license_name and not any(h in license_name.lower() for h in FREE_LICENSE_HINTS):
            print(f'  non-free license, skipping: {slug} ({license_name})')
            nomatch += 1
            continue
        jpg_path = os.path.join(OUT_DIR, f'{slug}.jpg')
        req = urllib.request.Request(img_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r, open(jpg_path, 'wb') as f:
            f.write(r.read())
        if HAS_PIL:
            webp_path = os.path.join(OUT_DIR, f'{slug}.webp')
            im = Image.open(jpg_path).convert('RGB')
            im.thumbnail((1200, 1200))
            im.save(webp_path, 'WEBP', quality=82)
            os.remove(jpg_path)
            src = f'/{webp_path}'
        else:
            src = f'/{jpg_path}'
        credit_bits = [b for b in [f'Photo: {artist}' if artist else 'Photo', license_name] if b]
        photo_map[slug] = {'src': src, 'credit': ', '.join(credit_bits) + ', via Wikimedia'}
        save_map()  # atomic, per-venue: Ctrl+C safe
        done += 1
        if done % 10 == 0:
            print(f'  {done} fetched...')
        time.sleep(0.3)  # polite to Wikimedia
    except KeyboardInterrupt:
        print('\nStopped. Progress saved; re-run to resume.')
        break
    except Exception as e:
        print(f'  error {slug}: {e}')

save_map()
write_review()
print(f'Done. fetched={done} skipped={skipped} no-match/non-free={nomatch}')
print('Open tools/review.html, verify matches, then commit img/venues/ + data/venue_photos.json and deploy.')
