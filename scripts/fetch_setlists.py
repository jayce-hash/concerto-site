#!/usr/bin/env python3
"""Fill "Setlist Coming Soon" tours from setlist.fm.

For every tour in data/tours.json whose entry in setlists.json has no songs, look up the
artist on setlist.fm, take the most recent full setlist on the current tour (matching
the tour name when setlist.fm has it, else the most recent show), and write it in with
a note naming the show it came from. Hand-curated setlists (any entry that already has
songs) are never touched. The app and every website page read the same setlists.json,
so one run updates both.

Setup (one time):
  1. Get a free key: https://api.setlist.fm/docs/1.0/index.html  (Account > API key)
  2. export SETLISTFM_API_KEY=your-key

Run:
  python3 scripts/fetch_setlists.py --dry-run     # show what would change, write nothing
  python3 scripts/fetch_setlists.py               # write setlists.json
  python3 scripts/fetch_setlists.py --refresh     # also refresh setlist.fm-sourced entries older than 14 days

Then the normal push: python3 build_data.py (if you use it), scripts/build-public-site.py, etc.
setlist.fm allows about 2 requests per second on a free key; the script sleeps to stay under it.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOURS = ROOT / 'data/tours.json'
SETLISTS = ROOT / 'setlists.json'
API = 'https://api.setlist.fm/rest/1.0'
KEY = os.environ.get('SETLISTFM_API_KEY', '').strip()
DRY = '--dry-run' in sys.argv
REFRESH = '--refresh' in sys.argv
MIN_SONGS = 8          # anything shorter is a festival slot or a partial; skip it
STALE_DAYS = 14


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def get(path, **params):
    url = API + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'x-api-key': KEY, 'Accept': 'application/json', 'User-Agent': 'Concerto/2.5 (concertocity.com)'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                time.sleep(0.6)
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                time.sleep(3 * (attempt + 1)); continue
            raise
    return None


def find_artist(name):
    d = get('/search/artists', artistName=name, sort='relevance')
    for a in (d or {}).get('artist', []):
        if norm(a.get('name')) == norm(name):
            return a
    arts = (d or {}).get('artist', [])
    return arts[0] if arts else None


def songs_of(setlist):
    out = []
    for st in setlist.get('sets', {}).get('set', []):
        for song in st.get('song', []):
            n = (song.get('name') or '').strip()
            if not n or song.get('tape'):
                continue
            if song.get('cover'):
                n = f"{n} ({song['cover'].get('name')} cover)"
            out.append(n)
    return out


def best_setlist(mbid, tour_name):
    """Most recent setlist on this tour with a real song count; falls back to the most recent full show."""
    d = get(f'/artist/{mbid}/setlists', p=1)
    cands = (d or {}).get('setlist', [])
    target = norm(tour_name)
    on_tour = [s for s in cands if norm((s.get('tour') or {}).get('name')) and (norm(s['tour']['name']) in target or target in norm(s['tour']['name']))]
    for pool in (on_tour, cands):
        for s in pool:  # setlist.fm returns newest first
            sg = songs_of(s)
            if len(sg) >= MIN_SONGS:
                return s, sg
    return None, []


def main():
    if not KEY:
        sys.exit('Set SETLISTFM_API_KEY first (free at api.setlist.fm).')
    tours = json.loads(TOURS.read_text())
    setlists = json.loads(SETLISTS.read_text())
    today = date.today()
    changed, skipped, missing = [], [], []
    for t in tours:
        slug, artist, tour_name = t['tourId'], t['artist'], t['tourName']
        cur = setlists.get(slug) or {}
        has_songs = bool(cur.get('songs'))
        from_fm = 'setlist.fm' in (cur.get('note') or '')
        if has_songs and not (REFRESH and from_fm):
            continue
        if has_songs and from_fm and REFRESH:
            try:
                age = (today - datetime.strptime(cur.get('updated', '2000-01-01')[:10], '%Y-%m-%d').date()).days
            except ValueError:
                age = STALE_DAYS + 1
            if age < STALE_DAYS:
                continue
        a = find_artist(artist)
        if not a:
            missing.append((slug, 'artist not found on setlist.fm')); continue
        s, sg = best_setlist(a['mbid'], tour_name)
        if not s:
            missing.append((slug, 'no full setlist yet')); continue
        venue = s.get('venue', {}); city = venue.get('city', {})
        when = s.get('eventDate', '')  # dd-MM-yyyy
        try:
            when_iso = datetime.strptime(when, '%d-%m-%Y').date().isoformat()
        except ValueError:
            when_iso = today.isoformat()
        entry = {
            'artist': artist,
            'tour': tour_name,
            'updated': today.isoformat(),
            'songs': sg,
            'note': f"From setlist.fm: {venue.get('name', 'recent show')}, {city.get('name', '')} on {when_iso}. Setlists change by night.",
            'source': {'provider': 'setlist.fm', 'setlistId': s.get('id'), 'url': s.get('url'), 'eventDate': when_iso},
        }
        changed.append((slug, len(sg), entry['note']))
        if not DRY:
            setlists[slug] = entry
    if not DRY and changed:
        SETLISTS.write_text(json.dumps(setlists, indent=1, ensure_ascii=False) + '\n')
    print(f"{'DRY RUN: ' if DRY else ''}{len(changed)} tours filled, {len(missing)} still without a setlist")
    for slug, n, note in changed:
        print(f'  + {slug}: {n} songs  ({note})')
    for slug, why in missing:
        print(f'  - {slug}: {why}')
    live = sum(1 for v in setlists.values() if v.get('songs'))
    print(f"\nsetlists with songs: {live} of {len(tours)} tours")


if __name__ == '__main__':
    main()
