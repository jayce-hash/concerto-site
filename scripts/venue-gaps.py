#!/usr/bin/env python3
"""What still needs work in Concerto's venue data, most important venues first.

  python3 scripts/venue-gaps.py            a summary, then the worklist
  python3 scripts/venue-gaps.py --json     the worklist as JSON (for a research session to work through)

A venue is "complete" for a fan's night when five things are true: the bag rule, parking and
entrances are confirmed from the venue's own pages, there is rideshare guidance (a confirmed
zone, or a named pickup spot), and there are at least three places to eat nearby.

It also lists sections that are marked confirmed but read as generic (written in the first
research pass): "a variety of", "several options", "it's advisable". Those say nothing a fan can
use, and are the first thing to re-research from the linked official page.
Reads data only. Changes nothing.
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
GENERIC = re.compile(r"advisable|variety of|several .{0,20}options|options nearby|varying|it's recommended|is recommended to|highlights include|range of|numerous|ample", re.I)
SECTIONS = ['bagPolicy', 'parking', 'rideshare', 'gates', 'concessions', 'accessibility', 'reEntry', 'ticketPickup']
ORDER = {'arena': 0, 'stadium': 0, 'amphitheater': 1, 'theater': 2, 'festival': 2, 'club': 3}


def main(argv):
    venues = json.loads((ROOT / 'data/venues.json').read_text())
    info = json.loads((ROOT / 'data/venue_info.json').read_text())
    exits = json.loads((ROOT / 'data/exit_plan.json').read_text())
    conf = lambda i, s: ((info.get(i) or {}).get(s) or {}).get('verificationStatus') == 'official_source_confirmed'
    def eats(i):
        p = ROOT / 'data/nearby' / f'{i}.json'
        if not p.exists(): return 0
        try: return len(((json.loads(p.read_text()).get('tabs') or {}).get('restaurants') or {}).get('items') or [])
        except Exception: return 0
    work = []
    for v in venues:
        i = v['id']
        missing = [name for name, ok in (('bag rule', conf(i, 'bagPolicy')), ('parking', conf(i, 'parking') or bool((exits.get(i) or {}).get('parking'))),
                                         ('entrances', conf(i, 'gates')), ('rideshare', conf(i, 'rideshare') or bool(((exits.get(i) or {}).get('pickup') or {}).get('name'))),
                                         ('places to eat', eats(i) >= 3)) if not ok]
        generic = [s for s in SECTIONS if conf(i, s) and GENERIC.search(' '.join(str(((info[i].get(s)) or {}).get(k) or '') for k in ('summary', 'note')))]
        if missing or generic:
            work.append({'id': i, 'name': v.get('name'), 'type': v.get('type'), 'missing': missing, 'generic': generic,
                         'links': {s: (info[i].get(s) or {}).get('officialLink') for s in generic}})
    work.sort(key=lambda w: (ORDER.get(w['type'], 4), -len(w['generic']), len(w['missing']), w['id']))
    if '--json' in argv: print(json.dumps(work, indent=1)); return
    total = len(venues); done = total - sum(1 for w in work if w['missing'])
    print(f'{done} of {total} venues are complete for a night (bag rule, parking, entrances, rideshare, places to eat).')
    for t in ('arena', 'stadium', 'amphitheater', 'theater', 'club', 'festival'):
        n = sum(1 for v in venues if v.get('type') == t); gaps = sum(1 for w in work if w['type'] == t and w['missing'])
        print(f'  {t:13} {n - gaps:4} of {n}')
    gen = sum(len(w['generic']) for w in work)
    print(f'{gen} confirmed sections read as generic, in {sum(1 for w in work if w["generic"])} venues. Re-research these first:')
    for w in [w for w in work if w['generic']][:40]:
        print(f"  {w['id']:38} {', '.join(w['generic'])}")
    print('Run with --json for the full worklist.')


if __name__ == '__main__':
    main(sys.argv[1:])
