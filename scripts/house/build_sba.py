"""Build Scotiabank Arena's House Map from its official hockey seating map (full bowl; positions
read 2026-11-02), the West End Stage concert map, the food page and the FAQ."""
import json, math, sys
from pathlib import Path
REPO = Path(sys.argv[1]); SLUG = 'scotiabank-arena'
B = 'https://www.scotiabankarena.com'
MAPS = B + '/assets/img/SBA-Map_West-End-Stage_240-Concert-Mode_Nov-2023-1-82655ac617.png'
FOOD = B + '/plan-your-visit/food-beverage/food-concessions'; FAQ = B + '/plan-your-visit/plan-your-visit-faq'
CHECKED = '2026-11-02'
NAVY, CREAM, LINE, DIM, DIMTXT = '#121E36', '#F8F9F9', '#D9DEE5', '#E6E9EE', '#9AA3B2'
CROP = (240, 60, 1260, 810); CW, CH = CROP[2] - CROP[0], CROP[3] - CROP[1]
def norm(p): return (round((p[0] - CROP[0]) / CW, 4), round((p[1] - CROP[1]) / CH, 4))
def c(p): return (p[0] - CROP[0], p[1] - CROP[1])
def sp(s): return {k: tuple(int(n) for n in v.split(',')) for k, v in (t.split(':') for t in s.split())}
L100 = sp("""101:948,380 102:953,431 103:953,484 104:950,532 105:904,560 106:867,575 107:813,584 108:747,584 109:678,584 110:620,584
111:567,582 112:540,534 113:538,484 114:538,432 115:540,383 116:587,352 117:622,333 118:679,333 119:747,333 120:815,333 121:867,333 122:924,333
105A:944,580 116A:546,328""")
L300 = sp("""301:1030,310 302:1062,382 303:1074,456 304:1062,527 305:1029,600 306:994,681 307:918,714 308:829,720 309:744,720 310:663,720
311:574,714 312:484,670 313:438,620 314:430,522 315:427,456 316:432,390 317:438,294 318:484,243 319:570,198 320:663,198 321:745,198
322:829,198 323:916,198 324:991,234 309A:764,697 319A:559,221""")
CENTER = (745, 458)
R100 = (485, 262, 1030, 655); R300 = (398, 150, 1108, 768)
STAGE = (600, 458)
def ring_point(p, ring):
    dx, dy = p[0] - CENTER[0], p[1] - CENTER[1]; ts = []
    if dx: ts += [(ring[0] - CENTER[0]) / dx, (ring[2] - CENTER[0]) / dx]
    if dy: ts += [(ring[1] - CENTER[1]) / dy, (ring[3] - CENTER[1]) / dy]
    t = min(t for t in ts if t > 0); return (CENTER[0] + dx * t, CENTER[1] + dy * t)
def label(x, y, t, on, w=30):
    fill, txt = (NAVY, '#FFFFFF') if on else (DIM, DIMTXT)
    return (f'<rect x="{x - w/2:.1f}" y="{y - 9:.1f}" width="{w}" height="18" rx="5" fill="{fill}"/>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="10" font-weight="700" fill="{txt}" text-anchor="middle">{t}</text>')
def svg(active):
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{CW}" height="{CH}" fill="{CREAM}"/>']
    x0, y0 = c(R300[:2]); x1, y1 = c(R300[2:])
    p.append(f'<rect x="{x0 - 26:.1f}" y="{y0 - 34:.1f}" width="{x1 - x0 + 52:.1f}" height="{y1 - y0 + 60:.1f}" rx="110" fill="#FFFFFF" stroke="{LINE}" stroke-width="2"/>')
    p.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" rx="96" fill="none" stroke="{LINE}" stroke-width="{10 if active == "300" else 2}" opacity="0.55"/>')
    a0, b0 = c(R100[:2]); a1, b1 = c(R100[2:])
    p.append(f'<rect x="{a0:.1f}" y="{b0:.1f}" width="{a1 - a0:.1f}" height="{b1 - b0:.1f}" rx="80" fill="none" stroke="{LINE}" stroke-width="{10 if active == "100" else 2}" opacity="0.55"/>')
    f0, g0 = c((595, 398)); f1, g1 = c((900, 518))
    p.append(f'<rect x="{f0:.1f}" y="{g0:.1f}" width="{f1 - f0:.1f}" height="{g1 - g0:.1f}" rx="40" fill="#F1F3F6" stroke="{LINE}" stroke-width="1.5"/>')
    sx, sy = c(STAGE)
    p.append(f'<rect x="{sx - 18:.1f}" y="{sy - 50:.1f}" width="36" height="100" rx="5" fill="{NAVY}"/>'
             f'<text x="{sx:.1f}" y="{sy + 4:.1f}" font-size="9" font-weight="700" fill="#FFFFFF" text-anchor="middle" transform="rotate(-90 {sx:.1f} {sy:.1f})" letter-spacing="1.5">STAGE</text>')
    for t, (tx, ty, rot) in {'UNION STATION · FRONT ST': (CW / 2, 16, 0), 'LAKESHORE BLVD': (CW / 2, CH - 8, 0),
                             'MAPLE LEAF SQUARE': (14, CH / 2, -90), 'BAY ST': (CW - 10, CH / 2, 90)}.items():
        p.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="10" font-weight="700" fill="{DIMTXT}" text-anchor="middle" letter-spacing="1.2"'
                 + (f' transform="rotate({rot} {tx:.1f} {ty:.1f})"' if rot else '') + f'>{t}</text>')
    for k, q in L100.items(): x, y = c(q); p.append(label(x, y, k, active == '100', 34 if 'A' in k else 30))
    for k, q in L300.items(): x, y = c(q); p.append(label(x, y, k, active == '300', 34 if 'A' in k else 30))
    p.append('</svg>'); return ''.join(p)
(REPO / 'img/house/sba-100.svg').write_text(svg('100')); (REPO / 'img/house/sba-300.svg').write_text(svg('300'))

points = []
def add(kind, name, level, xy, sections=None, offers=None, tags=None, source=FAQ):
    points.append({'id': f'{level}-{len(points)+1}', 'kind': kind, 'name': name, 'level': level, 'x': xy[0], 'y': xy[1],
                   **({'sections': sections} if sections else {}), **({'offers': offers} if offers else {}),
                   **({'tags': tags} if tags else {}), 'source': source, 'verified': CHECKED})
def at(sec):
    if sec in L100: return '100', norm(ring_point(L100[sec], R100))
    return '300', norm(ring_point(L300[sec], R300))
FOODS = [  # food page wording: "Located at Section ..."
 ('stand', 'Hogtown', '103 112 319', 'Bacon-wrapped foot-long hot dogs and other foot-longs', None),
 ('stand', 'Wicked Carib', '104', 'Caribbean entrées, all halal-certified', ['halal']),
 ('stand', 'Panini', '106', 'Meatball, Reuben and Turkey Club sandwiches, subs', None),
 ('stand', 'Crispy', '107 313', 'Jumbo chicken tenders, wings, chicken sandwiches', None),
 ('stand', 'Tim Hortons', '116', 'Coffee', None),
 ('stand', 'Hot Stove Carve', '117 313', 'Prime Rib Sandwich with kettle chips', None),
 ('stand', 'La Cantina', '120', 'Quesadillas, loaded nachos, rice bowls', None),
 ('stand', 'St. Patties Burgers & Poutine', '122', 'Burgers (vegan version available) and poutine', ['vegan']),
 ('stand', 'Cherry Street Bar-B-Que', '313', 'Barbecue, beside the Coors Light Chill Zone', None),
 ('stand', 'Poutinerie', '322', 'House-made poutines', None),
 ('bar', 'Molson Canadian Brewhouse', '108', 'Beer', None),
 ('bar', 'Captain Morgan Rum Bar', '111', 'Rum cocktails', None),
 ('bar', 'Smirnoff Vodka Bar', '116 305 319', 'Specialty cocktails', None),
 ('bar', 'Ciroc Ultra Premium Bar', '118', 'Premium vodka and specialty cocktails', None),
 ('bar', 'Crown Royal Bar', '324', 'Whisky and cocktails', None),
]
for kind, name, secs, offers, tags in FOODS:
    for s in secs.split():
        lvl, xy = at(s); add(kind, name, lvl, xy, sections=[s], offers=offers, tags=tags, source=FOOD)
cz = [L300[k] for k in ('313', '314', '315', '316', '317')]
add('bar', 'Coors Light Chill Zone', '300', norm(ring_point((sum(a for a, _ in cz) / 5, sum(b for _, b in cz) / 5), R300)),
    sections=['313', '314', '315', '316', '317'], offers='Above Gate 6, behind Sections 313 to 317. Service to your table.', source=FOOD)
# FAQ
add('guest_services', 'Fan Services Desk', '100', norm((745, 262)), offers='Inside Gate 1. First aid kits and lost and found.')
add('guest_services', 'Fan Services Desk', '300', at('301')[1], sections=['301'], offers='Outside Section 301. First aid kits and lost and found.')
add('sensory', 'Sensory service desk', '100', at('119')[1], sections=['119'], offers='Behind Section 119.')
add('sensory', 'Sensory service desk', '300', at('301')[1], sections=['301'], offers='Behind Section 301.')
for s in ('105A', '116A', '309A', '319A'):
    lvl, xy = at(s); add('first_aid', 'Paramedics', lvl, xy, sections=[s], offers=f'Outside Section {s}.')
for a, b in (('103', '104'), ('114', '115'), ('310', '311'), ('317', '318')):
    lvl, p1 = at(a); _, p2 = at(b)
    add('family_restroom', 'Universal accessible washroom', lvl, ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2), sections=[a, b], offers=f'Sections {a}/{b}.')
for s in ('122', '113', '311', '322'):
    lvl, xy = at(s); add('water', 'Water fountain', lvl, xy, sections=[s], offers=f'By Section {s}.')
add('nursing', 'Infant feeding room', '100', norm((800, 262)), offers='100 Level concourse, by Gate 1.')
add('gate', 'Gate 1 (Galleria)', '100', norm((745, 99)), offers='Union Station and Front Street side. Has an accessible entrance lane.', tags=['accessible'])
add('gate', 'Gate 3', '100', norm((1186, 347)), offers='Bay Street side. Suggested for shorter lines.')
add('gate', 'Gate 4', '100', norm((1098, 687)), offers='Southeast corner. Suggested for shorter lines.')
add('gate', 'Gate 5', '100', norm((362, 643)), offers='Southwest, off Maple Leaf Square. Gate 5B is suggested for shorter lines.')
add('gate', 'Gate 6', '100', norm((298, 456)), offers='Maple Leaf Square side.')
add('gate', 'Scotiabank Premium Entrance', '100', norm((1140, 236)), offers='Bay Street. Used for general admission too.')
add('box_office', 'Ticket office', '100', norm((560, 125)), offers='West end of the Galleria, near Gate 1.')
add('merch', 'Real Sports Apparel', '100', norm((690, 262)), offers='At Gate 1.')
add('elevator', 'Elevator', '100', norm((375, 625)), offers='At Gate 5. Goes up to Level 400.')
exec(open(Path(__file__).parent / '_helpers_spread.py').read())
spread(points)
data = {'venue': SLUG, 'name': 'Scotiabank Arena', 'updated': CHECKED, 'sourceLabel': 'scotiabankarena.com',
        'note': 'On Scotiabank Arena’s concert map, the stage sits at the west end, in front of Sections 112 to 115. In this layout some west-end seats are closed. Your show’s layout can differ.',
        'levels': [{'id': '100', 'label': '100 Level', 'image': '/img/house/sba-100.svg', 'aspect': round(CW / CH, 4), 'sections': {k: dict(zip(('x', 'y'), norm(p))) for k, p in L100.items()}},
                   {'id': '300', 'label': '300 Level', 'image': '/img/house/sba-300.svg', 'aspect': round(CW / CH, 4), 'sections': {k: dict(zip(('x', 'y'), norm(p))) for k, p in L300.items()}}],
        'points': points}
(REPO / 'data/house' / f'{SLUG}.json').write_text(json.dumps(data, indent=1, ensure_ascii=False))
idx = REPO / 'data/house/index.json'; cur = json.loads(idx.read_text())
if SLUG not in cur: cur.append(SLUG)
idx.write_text(json.dumps(cur))
from collections import Counter; print(len(points), 'points', Counter((p['level'], p['kind']) for p in points))
