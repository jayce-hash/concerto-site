#!/usr/bin/env python3
"""
build_data.py -- regenerate every derived data file, then validate.

THE ONLY FILES YOU EDIT BY HAND:

  data/venues.json       one entry per venue (id, name, city, state,
                         country, lat, lng, guideUrl)
  data/venue_info.json   the real content: bag policy, parking,
                         concessions, rideshare, keyed by venue id
  data/tours.json        one entry per tour (tourId, tourName, artist,
                         tourWebsite)
  setlists.json          keyed by artist slug

EVERYTHING ELSE IS GENERATED FROM THOSE. Never edit these by hand:

  search-index.json      built here from venues + tours
  sitemap.xml            built by build_sitemap.py

Run:  python3 build_data.py
      python3 build_sitemap.py

On GitHub, the data workflow runs both automatically on every push
that touches the authored files, so browser edits are enough.

Exit code 1 on any validation failure, so CI fails loudly instead of
shipping broken data.
"""
import json
import os
import re
import sys
from datetime import date

FAIL = []
WARN = []
NO_DATE = []


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def fail(msg):
    FAIL.append(msg)


def warn(msg):
    WARN.append(msg)


venues = load('data/venues.json')
info = load('data/venue_info.json')
tours = load('data/tours.json')
setlists = load('setlists.json') if os.path.exists('setlists.json') else {}

# ── Validate venues ─────────────────────────────────────────────────
SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
seen = set()
for v in venues:
    vid = v.get('id', '')
    if not vid:
        fail(f'venue with no id: {v.get("name", "?")}')
        continue
    if not SLUG_RE.match(vid):
        fail(f'venue id is not a clean slug: {vid!r} '
             '(lowercase, digits and single hyphens only)')
    if vid in seen:
        fail(f'duplicate venue id: {vid}')
    seen.add(vid)
    for field in ('name', 'city', 'lat', 'lng'):
        if v.get(field) in (None, ''):
            fail(f'{vid}: missing {field}')
    if vid not in info:
        fail(f'{vid}: in venues.json but has NO entry in venue_info.json '
             '(the venue page would render empty)')

for key in info:
    if key not in seen:
        fail(f'venue_info.json has an entry for {key!r} but no such venue '
             'in venues.json (orphan; nothing will ever read it)')

# ── Validate tours ──────────────────────────────────────────────────
tseen = set()
today = date.today().isoformat()
for t in tours:
    tid = t.get('tourId', '')
    if not tid:
        fail(f'tour with no tourId: {t.get("tourName", "?")}')
        continue
    if not SLUG_RE.match(tid):
        fail(f'tour id is not a clean slug: {tid!r}')
    if tid in tseen:
        fail(f'duplicate tourId: {tid}')
    tseen.add(tid)
    for field in ('tourName', 'artist'):
        if not t.get(field):
            fail(f'{tid}: missing {field}')
    a = (t.get('artist') or '')
    if a.lower().endswith(' tour'):
        warn(f'{tid}: artist reads {a!r}, which looks like a tour name. '
             'Check the artist field.')
    # Optional but recommended: lastShowDate lets ended tours be caught
    last = t.get('lastShowDate')
    if last and last < today:
        warn(f'{tid}: lastShowDate {last} has passed. This tour has ended '
             'and should be removed from data/tours.json.')
    if not last:
        NO_DATE.append(tid)

# ── Generate search-index.json ──────────────────────────────────────
# This is the file that silently drifted: four tours existed but were
# unsearchable because they were never added here by hand.
search = {
    'venues': [
        {
            'name': v['name'],
            'slug': v['id'],
            'type': (info.get(v['id'], {}) or {}).get('type', 'Arena'),
        }
        for v in sorted(venues, key=lambda x: x['name'].lower())
    ],
    'tours': [
        {
            'name': t['tourName'],
            'slug': t['tourId'],
            'artist': t['artist'],
        }
        for t in sorted(tours, key=lambda x: x['artist'].lower())
    ],
}
save('search-index.json', search)

if NO_DATE:
    warn(f'{len(NO_DATE)} of {len(tours)} tours have no lastShowDate, so an '
         'ended tour cannot be detected automatically. Add '
         '"lastShowDate": "YYYY-MM-DD" as you touch each one.')

# ── Setlist coverage (informational) ─────────────────────────────────
if setlists:
    artists = {t['artist'] for t in tours}
    def artist_slug(a):
        return re.sub(r'[^a-z0-9]+', '-', a.lower()).strip('-')
    missing = sorted(a for a in artists if artist_slug(a) not in setlists)
    if missing:
        warn(f'{len(missing)} touring artists have no setlist entry, '
             f'e.g. {missing[:4]}')

# ── Report ──────────────────────────────────────────────────────────
print(f'venues: {len(venues)}   venue_info: {len(info)}   tours: {len(tours)}')
print(f'search-index.json rebuilt: {len(search["venues"])} venues, '
      f'{len(search["tours"])} tours')

for w in WARN:
    print(f'  WARN  {w}')

if FAIL:
    print()
    for f_ in FAIL:
        print(f'  FAIL  {f_}')
    print(f'\n{len(FAIL)} problem(s). Nothing was deployed. Fix and re-run.')
    sys.exit(1)

print('\nAll checks passed. Next: python3 build_sitemap.py')
