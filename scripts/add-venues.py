#!/usr/bin/env python3
"""Merge researched venues into Concerto: website data, and optionally the app's offline seed.

  python3 scripts/add-venues.py venues-to-add.json venue_info-to-add.json [--native ../concerto-native-repo] [--skip-invalid]

Checks every record the way the release validators do, and refuses the whole merge if anything
is wrong (use --skip-invalid to merge only the good ones). Venues marked "_remove": true are skipped.
Then it updates the hard-coded venue counts in both repos' validators. Nearby places come after:
  GOOGLE_PLACES_SERVER_KEY=... python3 scripts/build-nearby.py <ids...>
"""
import json, re, sys, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ['bagPolicy', 'parking', 'rideshare', 'concessions', 'accessibility', 'reEntry', 'ticketPickup', 'gates']
STATUSES = {'official_source_confirmed', 'official_source_reviewed_no_specific_extract'}
def norm(s): return re.sub(r'[^a-z0-9]', '', str(s or '').lower().replace('the ', ''))

def check(v, info, have_ids, have_names, today):
    e = []
    vid = v.get('id', '')
    if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', vid): e.append('id is not a slug')
    if vid in have_ids: e.append('id already exists on the site')
    if (norm(v.get('name')), norm(v.get('city'))) in have_names: e.append('a venue with this name and city already exists')
    for k in ('name', 'city'):
        if not str(v.get(k, '')).strip(): e.append(f'{k} missing')
    if not re.fullmatch(r'[A-Z]{2}', str(v.get('country', ''))): e.append('country must be a 2-letter ISO code (US, GB, ...)')
    try:
        lat, lng = float(v['lat']), float(v['lng'])
        if not (-90 <= lat <= 90 and -180 <= lng <= 180) or (lat == 0 and lng == 0): e.append('lat/lng out of range')
    except Exception: e.append('lat/lng missing or not numbers')
    r = info.get(vid)
    if not r: return e + ['no venue_info record']
    for s in SECTIONS:
        x = r.get(s)
        if not isinstance(x, dict): e.append(f'{s} missing'); continue
        if not str(x.get('summary', '')).strip(): e.append(f'{s}.summary empty')
        if not re.match(r'^https://', str(x.get('officialLink', ''))): e.append(f'{s}.officialLink missing or not https')
        d = str(x.get('verified', ''))
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d) or d > today: e.append(f'{s}.verified must be a past date YYYY-MM-DD')
        if x.get('verificationStatus') not in STATUSES: e.append(f'{s}.verificationStatus invalid')
        if not isinstance(x.get('allowed', []), list) or not isinstance(x.get('prohibited', []), list): e.append(f'{s} allowed/prohibited must be lists')
    return e

def bump_count(path, old, new):
    p = Path(path)
    if not p.exists(): return
    s = p.read_text(); s2 = re.sub(rf'(===\s*){old}\b', rf'\g<1>{new}', s); s2 = re.sub(rf'expected {old}\b', f'expected {new}', s2)
    if s2 != s: p.write_text(s2); print(f'  count {old} -> {new}: {p}')

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    native = sys.argv[sys.argv.index('--native') + 1] if '--native' in sys.argv else None
    if native in args: args.remove(native)
    if len(args) != 2: sys.exit(__doc__)
    new_v = json.loads(Path(args[0]).read_text()); new_i = json.loads(Path(args[1]).read_text())
    venues = json.loads((ROOT / 'data/venues.json').read_text()); info = json.loads((ROOT / 'data/venue_info.json').read_text())
    have_ids = {v['id'] for v in venues}; have_names = {(norm(v['name']), norm(v['city'])) for v in venues}
    today = datetime.date.today().isoformat()
    good, bad, removed = [], {}, 0
    for v in new_v:
        if v.get('_remove'): removed += 1; continue
        errs = check(v, new_i, have_ids, have_names, today)
        if errs: bad[v.get('id', '?')] = errs
        else: good.append(v)
    print(f'{len(good)} ready | {len(bad)} with problems | {removed} marked for removal')
    for vid, errs in list(bad.items())[:40]: print(f'  {vid}: ' + '; '.join(errs[:4]))
    if bad and '--skip-invalid' not in sys.argv: sys.exit('Nothing merged. Fix the problems above, or rerun with --skip-invalid to merge only the ready venues.')
    if not good: sys.exit('Nothing to merge.')
    old = len(venues)
    for v in good:
        rec = {k: v[k] for k in ('id', 'name', 'city', 'state', 'country', 'lat', 'lng', 'guideUrl')}
        rec['lat'], rec['lng'] = float(rec['lat']), float(rec['lng'])
        venues.append(rec)
        r = {k: x for k, x in new_i[v['id']].items() if not k.startswith('_')}
        r.update(name=rec['name'], city=rec['city'], state=rec['state'], country=rec['country'], lat=rec['lat'], lng=rec['lng'])
        info[v['id']] = r
    venues.sort(key=lambda x: x['id'])
    (ROOT / 'data/venues.json').write_text(json.dumps(venues, indent=2, ensure_ascii=False) + '\n')
    (ROOT / 'data/venue_info.json').write_text(json.dumps(info, indent=2, ensure_ascii=False) + '\n')
    new = len(venues); print(f'Website data: {old} -> {new} venues')
    bump_count(ROOT / 'scripts/validate-release.js', old, new)
    if native:
        nr = Path(native).expanduser(); seed = nr / 'src/data/seed'
        sv = json.loads((seed / 'venues.json').read_text()); si = json.loads((seed / 'venue_info.json').read_text())
        for v in good:
            sv.append({'slug': v['id'], 'name': v['name'], 'city': v['city'], 'state': v['state'], 'country': v['country'], 'lat': float(v['lat']), 'lng': float(v['lng'])})
            si[v['id']] = info[v['id']]
        sv.sort(key=lambda x: x['slug'])
        (seed / 'venues.json').write_text(json.dumps(sv, indent=2, ensure_ascii=False) + '\n')
        (seed / 'venue_info.json').write_text(json.dumps(si, indent=2, ensure_ascii=False) + '\n')
        print(f'App offline seed: {len(sv)} venues')
        for f in ('scripts/validate-release.js', 'scripts/validate-seo.js'): bump_count(nr / f, old, new)
    ids = ' '.join(v['id'] for v in good)
    Path(ROOT / 'data/.new-venue-ids').write_text(ids + '\n')
    print('\nNext: build nearby places for the new venues (needs your Google Places key):')
    print('  GOOGLE_PLACES_SERVER_KEY=your-key python3 scripts/build-nearby.py $(cat data/.new-venue-ids)')

if __name__ == '__main__':
    main()
