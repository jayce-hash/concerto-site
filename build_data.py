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
  data/updates/*.json    venue info patches from research chats;
                         merged into venue_info.json then moved to
                         data/updates/applied/

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


# ── Apply venue info updates ────────────────────────────────────────
# Research chats write a patch file to data/updates/*.json instead of
# hand-editing the 1MB venue_info.json. Shape:
#
#   { "venue-slug": { "bagPolicy": {...}, "concessions": {...} } }
#
# Only the sections present are replaced; everything else on that
# venue is left alone. Each patched section gets today's date stamped
# into "verified" unless the patch supplied one. Applied patches are
# moved to data/updates/applied/ so they run exactly once.
UPD = 'data/updates'
applied_any = False
if os.path.isdir(UPD):
    os.makedirs(f'{UPD}/applied', exist_ok=True)
    today_str = date.today().isoformat()
    for fn in sorted(os.listdir(UPD)):
        if not fn.endswith('.json'):
            continue
        path = f'{UPD}/{fn}'
        try:
            patch = load(path)
        except json.JSONDecodeError as e:
            fail(f'{path}: not valid JSON ({e})')
            continue
        if not isinstance(patch, dict):
            fail(f'{path}: expected an object keyed by venue slug')
            continue
        count = 0
        for slug, sections in patch.items():
            if slug not in info:
                fail(f'{path}: no venue named {slug!r} '
                     '(check the slug against data/venues.json)')
                continue
            if not isinstance(sections, dict):
                fail(f'{path}: {slug} should map to an object of sections')
                continue
            for sec, body in sections.items():
                if sec not in ('bagPolicy', 'parking', 'rideshare',
                               'concessions', 'accessibility', 'reEntry',
                               'ticketPickup', 'gates'):
                    fail(f'{path}: {slug} has unknown section {sec!r}')
                    continue
                if isinstance(body, dict) and not body.get('verified'):
                    body['verified'] = today_str
                info[slug][sec] = body
                count += 1
        if not FAIL:
            os.rename(path, f'{UPD}/applied/{fn}')
            print(f'applied {fn}: {count} section(s) updated')
            applied_any = True

if applied_any:
    save('data/venue_info.json', info)


# ── One-time corrections + permanent reconciliation ─────────────────
# Verified against official sources (artist sites, Live Nation,
# Sphere Entertainment, Variety) on 2026-08-07. tours.json is the
# single source of truth for artist and tour names; setlists.json
# inherits both below, so the two files can never disagree again.

ID_FIXES = {
    # typo in the slug; a 301 in _redirects covers the old URL
    'backstreet-boys-into-the-millenium-sphere-las-vegas':
        'backstreet-boys-into-the-millennium-sphere-las-vegas',
}
NAME_FIXES = {
    # tourId: (artist or None, tourName or None)
    'mumford-and-sons-prizefighter-tour': ('Mumford & Sons', None),
    'harry-styles-together-together-tour': (None, 'Together, Together'),
    'my-chemical-romance-the-black-parade-tour': (None, 'The Black Parade 2026'),
    'eagles-live-at-sphere-2026': (None, 'Eagles: Live in Concert at Sphere'),
    'hayley-williams-at-a-bachelorette-party-tour':
        (None, 'Hayley Williams at a Bachelorette Party'),
    'olivia-dean-the-art-of-loving-tour': (None, 'The Art of Loving Live'),
}

changed_data = False
for t in tours:
    if 'lastShowDate' in t:
        t.pop('lastShowDate', None)
        changed_data = True
    tid = t.get('tourId', '')
    if tid in ID_FIXES:
        t['tourId'] = ID_FIXES[tid]
        tid = t['tourId']
        changed_data = True
    if tid in NAME_FIXES:
        art, name = NAME_FIXES[tid]
        if art and t.get('artist') != art:
            t['artist'] = art
            changed_data = True
        if name and t.get('tourName') != name:
            t['tourName'] = name
            changed_data = True

# setlists.json: keys must be resolvable from a current tourId (the
# app matches by prefix). Delete orphans, propagate names from tours.
if setlists:
    tids = [t['tourId'] for t in tours]
    orphans = [k for k in list(setlists)
               if not any(tid.startswith(k) for tid in tids)]
    for k in orphans:
        del setlists[k]
        print(f'setlists: removed orphan {k!r} (no matching tour)')
        changed_data = True
    for t in tours:
        k = next((k for k in setlists if t['tourId'].startswith(k)), None)
        if not k:
            continue
        s = setlists[k]
        if s.get('artist') != t['artist']:
            s['artist'] = t['artist']
            changed_data = True
        if s.get('tour') != t['tourName']:
            s['tour'] = t['tourName']
            changed_data = True

if changed_data:
    save('data/tours.json', tours)
    if setlists:
        save('setlists.json', setlists)
    print('tours.json / setlists.json reconciled and saved')

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
    # Dates are Ticketmaster's job (the app queries TM live). A hand
    # maintained lastShowDate drifts, so the field is retired; strip it
    # if present so it cannot mislead anyone later.
    t.pop('lastShowDate', None)

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

# ── Setlist coverage (informational) ─────────────────────────────────
if setlists:
    # setlists.json is keyed by tourId. (It used to be keyed by artist
    # slug, and this check still assumed that, so it reported every
    # tour as missing a setlist even when all 78 were present.)
    empty = sorted(t['tourId'] for t in tours
                   if not (setlists.get(t['tourId']) or {}).get('songs'))
    if empty:
        warn(f'{len(empty)} of {len(tours)} tours have no songs yet, '
             f'e.g. {empty[:3]}')

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
