#!/usr/bin/env python3
"""Give every tour a genre for the Tours filter, from Ticketmaster's own classification.

  python3 scripts/tag-tour-genres.py            # tours without a genre
  python3 scripts/tag-tour-genres.py --all      # re-check every tour

Looks up each artist through Concerto's own Ticketmaster proxy (no key needed), takes the
genre Ticketmaster files the artist under, and groups it into the buckets the filter shows.
Writes "genre" into data/tours.json. Hand corrections go in data/tour_genre_overrides.json
({"tourId": "Country & Folk"}) and always win. Run it again when you add tours.
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROXY = 'https://concertocity.com/.netlify/functions/tm/attractions.json'
BUCKET = {
    'pop': 'Pop', 'ballads/romantic': 'Pop',
    'rock': 'Rock & Alternative', 'alternative': 'Rock & Alternative', 'metal': 'Rock & Alternative', 'punk': 'Rock & Alternative',
    'country': 'Country & Folk', 'folk': 'Country & Folk',
    'hip-hop/rap': 'Hip-Hop & R&B', 'r&b': 'Hip-Hop & R&B',
    'latin': 'Latin',
    'dance/electronic': 'Electronic',
    'jazz': 'Jazz & Blues', 'blues': 'Jazz & Blues',
    'classical': 'Classical',
}
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def lookup(artist):
    q = urllib.parse.urlencode({'keyword': artist, 'classificationName': 'Music', 'size': '10'})
    req = urllib.request.Request(f'{PROXY}?{q}', headers={'Referer': 'https://concertocity.com/', 'User-Agent': 'ConcertoGenreTagger/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    for a in (data.get('_embedded') or {}).get('attractions', []):
        if norm(a.get('name')) == norm(artist):
            c = (a.get('classifications') or [{}])[0]
            g = ((c.get('genre') or {}).get('name') or '').strip()
            if not g or g.lower() in ('undefined', 'other'):
                return 'Other' if g else None
            return BUCKET.get(g.lower(), 'Other')
    return None

def main():
    tours = json.loads((ROOT / 'data/tours.json').read_text())
    over_p = ROOT / 'data/tour_genre_overrides.json'
    over = json.loads(over_p.read_text()) if over_p.exists() else {}
    redo = '--all' in sys.argv
    cache, done, missing = {}, 0, []
    for t in tours:
        if t['tourId'] in over:
            t['genre'] = over[t['tourId']]; continue
        if t.get('genre') and not redo: continue
        a = t['artist']
        if a not in cache:
            try: cache[a] = lookup(a)
            except Exception as e: print(f'  {a}: lookup failed ({type(e).__name__})'); cache[a] = None
            time.sleep(0.25)
        if cache[a]: t['genre'] = cache[a]; done += 1
        else: t.pop('genre', None); missing.append(t['tourId'])
    (ROOT / 'data/tours.json').write_text(json.dumps(tours, indent=2, ensure_ascii=False) + '\n')
    print(f'{done} tours tagged; {len(missing)} without a Ticketmaster genre (they still show under All).')
    for m in missing: print('  ', m)
    if missing: print('Add any of these to data/tour_genre_overrides.json to place them by hand.')

if __name__ == '__main__':
    main()
