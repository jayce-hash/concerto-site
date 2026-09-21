#!/usr/bin/env python3
"""Stage clock history: when the opener and headliner actually went on, per tour.

Reads setlist.fm timings for the last ten shows of each tour and writes
data/stage_times.json as { tourSlug: { opener, headliner, shows, updated } }, times as
HH:MM in the venue's local time. The app and the site show it as "Headliner around
9:05, based on 7 shows this tour". Fewer than 3 shows: no entry, so nothing guesses.

Needs SETLISTFM_API_KEY (same key as fetch_setlists.py). Run weekly with it.
"""
import json, os, re, sys, time, urllib.parse, urllib.request, statistics
from datetime import date, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
API = 'https://api.setlist.fm/rest/1.0'; KEY = os.environ.get('SETLISTFM_API_KEY', '').strip()
OUT = ROOT / 'data/stage_times.json'; MIN_SHOWS = 3

def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def get(path, **params):
    url = API + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'x-api-key': KEY, 'Accept': 'application/json', 'User-Agent': 'Concerto/2.6 (concertocity.com)'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r: time.sleep(0.6); return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code == 429: time.sleep(3 * (attempt + 1)); continue
            raise
    return None

def minutes(t):
    try: h, m = t.split(':')[:2]; return int(h) * 60 + int(m)
    except Exception: return None
def clock(mins): return f'{mins // 60:02d}:{mins % 60:02d}'

def main():
    if not KEY: sys.exit('Set SETLISTFM_API_KEY first.')
    tours = json.loads((ROOT / 'data/tours.json').read_text())
    out = {}
    for t in tours:
        a = get('/search/artists', artistName=t['artist'], sort='relevance')
        arts = (a or {}).get('artist', []); art = next((x for x in arts if norm(x.get('name')) == norm(t['artist'])), arts[0] if arts else None)
        if not art: continue
        d = get(f"/artist/{art['mbid']}/setlists", p=1); cands = (d or {}).get('setlist', [])
        target = norm(t['tourName'])
        on_tour = [s for s in cands if norm((s.get('tour') or {}).get('name')) and (norm(s['tour']['name']) in target or target in norm(s['tour']['name']))] or cands
        heads, opens = [], []
        for s in on_tour[:10]:
            # setlist.fm exposes set-level "start" only on some entries; when present it is the show start in venue time.
            st = s.get('sets', {}).get('set', [])
            for i, block in enumerate(st):
                mins = minutes(block.get('start') or '')
                if mins is None: continue
                (opens if (block.get('name') or '').lower().startswith(('opening', 'support', 'opener')) else heads).append(mins)
        if len(heads) >= MIN_SHOWS:
            out[t['tourId']] = {'headliner': clock(int(statistics.median(heads))), 'opener': clock(int(statistics.median(opens))) if len(opens) >= MIN_SHOWS else None, 'shows': len(heads), 'updated': date.today().isoformat()}
    OUT.write_text(json.dumps(out, indent=1) + '\n')
    print(f'stage_times.json: {len(out)} tours with a stage clock (need {MIN_SHOWS}+ timed shows); {len(tours) - len(out)} say "not yet posted"')

if __name__ == '__main__': main()
