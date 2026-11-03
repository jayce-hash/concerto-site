"""Build Crypto.com Arena's House Map from the arena's own interactive map (visit.cryptoarena.com/map),
read in Chrome on 2026-11-02: each listing's section, the map's pins, and section and aisle positions
read off the map. Plus the A-Z guide and accessibility pages for water, sensory and gates.
Frame: the Upper Concourse view, 980 x 900 (a zoomed capture of the map)."""
import json, math, sys
import numpy as np
from pathlib import Path
REPO = Path(sys.argv[1]); SLUG = 'cryptocom-arena'
MAP = 'https://visit.cryptoarena.com/map'; AZ = 'https://www.cryptoarena.com/a-z-guide'
ACC = 'https://www.cryptoarena.com/accessibility'; TRANS = 'https://www.cryptoarena.com/public-transportation'
CHECKED = '2026-11-02'
NAVY, CREAM, LINE, DIM, DIMTXT = '#121E36', '#F8F9F9', '#D9DEE5', '#E6E9EE', '#9AA3B2'
FW, FH = 980, 900
def sp(s): return {k: tuple(float(n) for n in v.split(',')) for k, v in (t.split(':') for t in s.split())}
S_M, S_U, K = (575, 315), (510, 398), 1.22     # main capture -> upper frame (same map, different zoom)
def m2u(p): return ((p[0] - S_M[0]) / K + S_U[0], (p[1] - S_M[1]) / K + S_U[1])
MAIN = {k: m2u(v) for k, v in sp("""101:512,472 102:462,507 103:425,532 104:400,568 105:357,555 106:314,527 107:280,472 108:282,414 109:315,375
110:358,345 111:402,318 112:440,270 113:488,258 114:538,230 115:611,243 116:635,320 117:627,380 118:598,416 119:535,440
205:342,620 206:291,598 207:245,562 208:216,518 209:202,464 210:204,412 214:574,165 215:617,186 216:662,220 217:694,265 218:709,320 219:711,370""").items()}
MAISLE = {k: m2u(v) for k, v in sp("""M1:578,622 M2:525,650 M3:460,675 M4:364,680 M5:293,665 M6:230,628 M7:178,572 M8:148,507 M9:143,430 M10:152,372
M11:192,293 M12:230,243 M13:283,198 M14:330,163 M15:383,136 M16:452,112 M17:545,103 M18:614,115 M19:681,155 M20:733,209 M21:762,278
M22:775,350 M23:764,416 M24:723,492 M25:682,540 M26:628,588""").items()}
UP = sp("""301:537,625 302:496,648 303:462,668 304:426,688 305:374,700 306:330,700 307:285,690 308:241,670 309:204,637 310:176,598 311:158,552
312:154,508 313:157,462 314:173,418 315:196,381 316:232,348 317:264,326 318:303,299 319:346,272 320:378,252 321:420,232 322:466,225 323:511,227
324:547,240 329:673,418 330:669,462 331:657,498 332:636,538 333:601,575 334:564,600""")
UAISLE = sp("""U1:530,666 U2:497,686 U3:462,705 U4:414,725 U5:360,730 U6:305,727 U7:250,715 U8:204,684 U9:162,635 U10:136,592 U11:120,531 U12:120,488
U13:136,423 U14:157,383 U15:196,339 U16:232,310 U17:258,292 U18:313,258 U19:342,238 U20:384,215 U21:437,200 U22:488,197 U23:536,203
U29:700,442 U30:692,483 U31:676,530 U32:637,578 U33:601,612 U34:568,637""")
TERRACE = (620, 320)   # Upper Concourse Terrace (where 325-328 would be)
STAGE = (510, 398)

def fit(pts):
    a = np.array(list(pts)); c = a.mean(0); u, s, vt = np.linalg.svd(a - c)
    proj = (a - c) @ vt.T; return c, vt, np.abs(proj).max(0)
def on_ring(p, ring, inset=0.97):
    c, vt, ax = ring; d = (np.array(p) - c) @ vt.T
    t = 1 / math.sqrt((d[0] / ax[0]) ** 2 + (d[1] / ax[1]) ** 2) * inset
    q = c + (d * t) @ vt; return (float(q[0]), float(q[1]))
RM, RU = fit(MAISLE.values()), fit(UAISLE.values())
def norm(p): return (round(p[0] / FW, 4), round(p[1] / FH, 4))

def ell(ring, stroke, w, fill='none', scale=1.0, op=1):
    c, vt, ax = ring; ang = math.degrees(math.atan2(vt[0][1], vt[0][0]))
    return (f'<ellipse cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="{ax[0]*scale:.1f}" ry="{ax[1]*scale:.1f}" transform="rotate({ang:.1f} {c[0]:.1f} {c[1]:.1f})" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{w}" opacity="{op}"/>')
def label(x, y, t, on, w=30):
    fill, txt = (NAVY, '#FFFFFF') if on else (DIM, DIMTXT)
    return (f'<rect x="{x - w/2:.1f}" y="{y - 9:.1f}" width="{w}" height="18" rx="5" fill="{fill}"/>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="10" font-weight="700" fill="{txt}" text-anchor="middle">{t}</text>')
def svg(active):
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FW} {FH}" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{FW}" height="{FH}" fill="{CREAM}"/>',
         ell(RU, LINE, 2, '#FFFFFF', 1.12),
         ell(RU, LINE, 10 if active == 'upper' else 2, scale=1.0, op=0.55),
         ell(RM, LINE, 10 if active == 'main' else 2, scale=1.0, op=0.55),
         ell(RM, LINE, 1.5, '#F1F3F6', 0.52)]
    sx, sy = STAGE
    p.append(f'<rect x="{sx - 34:.1f}" y="{sy - 26:.1f}" width="68" height="52" rx="5" fill="{NAVY}" transform="rotate(-28 {sx:.1f} {sy:.1f})"/>'
             f'<text x="{sx:.1f}" y="{sy + 4:.1f}" font-size="9" font-weight="700" fill="#FFFFFF" text-anchor="middle" letter-spacing="1.5">STAGE</text>')
    for t, (tx, ty) in {'CHICK HEARN CT': (700, 22), 'FIGUEROA ST': (940, 640), 'W 12TH ST': (470, 892), 'STAR PLAZA': (880, 160)}.items():
        p.append(f'<text x="{tx}" y="{ty}" font-size="10" font-weight="700" fill="{DIMTXT}" text-anchor="middle" letter-spacing="1.2">{t}</text>')
    for k, q in MAIN.items(): p.append(label(q[0], q[1], k, active == 'main'))
    for k, q in UP.items(): p.append(label(q[0], q[1], k, active == 'upper'))
    p.append(label(TERRACE[0], TERRACE[1], 'Terrace', active == 'upper', 52))
    p.append('</svg>'); return ''.join(p)
(REPO / 'img/house/crypto-main.svg').write_text(svg('main')); (REPO / 'img/house/crypto-upper.svg').write_text(svg('upper'))

points = []
def add(kind, name, level, xy, sections=None, offers=None, tags=None, source=MAP):
    points.append({'id': f'{level}-{len(points)+1}', 'kind': kind, 'name': name, 'level': level, 'x': norm(xy)[0], 'y': norm(xy)[1],
                   **({'sections': sections} if sections else {}), **({'offers': offers} if offers else {}),
                   **({'tags': tags} if tags else {}), 'source': source, 'verified': CHECKED})
def at(sec):
    if sec in MAIN: return 'main', on_ring(MAIN[sec], RM)
    if sec == '325': return 'upper', on_ring(TERRACE, RU)
    return 'upper', on_ring(UP[sec], RU)
FOOD = [  # the map's listing: name, its label, section
 ('bar', 'Bud Light Seltzer Market', 'Drinks and snacks', '113'), ('bar', 'Codigo Bar', 'Bar', '101'), ('stand', 'Deli & Dash', 'Deli', '115'),
 ('stand', 'Dirt Dog', 'Hot dogs and drinks', '112 102'), ('bar', 'Doritos After Dark', 'Bar and grill', '116'),
 ('stand', 'Farmer’s Fridge', 'Salads and sandwiches', '102'), ('bar', 'Golden Road Brew House', 'Bar', '118'),
 ('stand', 'LA Cooler Market', 'Drinks and snacks', '118'), ('stand', 'Ludo Bird', 'Fried chicken', '119'),
 ('stand', 'Ludobab', 'Mediterranean', '117'), ('stand', 'Pizza', 'Pizza', '109'), ('stand', 'Salt & Char', 'Burgers and drinks', '114 333'),
 ('stand', 'Tostitos Cart', 'Nachos', '112 319'), ('stand', 'Trois Familia', 'Mexican', '117'), ('stand', 'Wetzel’s Pretzels', 'Pretzels', '112 103 316'),
 ('stand', 'Coca-Cola Area', 'Food and drinks', '333'), ('stand', 'EATS', 'Snacks and drinks', '318'), ('stand', 'fuku', 'Chicken tenders', '325'),
 ('bar', 'Kona Big Wave Liquid Aloha', 'Drinks and snacks', '316'), ('bar', 'Marg Bar', 'Margaritas', '302'),
 ('stand', 'South Park Market', 'Snacks and drinks', '301'), ('bar', 'The Spirited Mule', 'Bar', '317'),
]
for kind, name, offers, secs in FOOD:
    for s in secs.split():
        lvl, xy = at(s)
        add(kind, name, lvl, xy, sections=[s] if s != '325' else None,
            offers=offers + ('. On the Upper Concourse Terrace, across from Section 325.' if s == '325' else ''))
add('stand', 'Michelob Ultra Club Market', 'main', (482, 830), offers='Snacks and drinks, at the Figueroa St. Entrance.')
for g, secs in (('Men’s', '208 219 217 214 210 205 110 101'), ('Women’s', '114 111 209 206 119 216 218 109')):
    for s in secs.split():
        lvl, xy = at(s); add('restroom', f'{g} restroom', lvl, xy, sections=[s])
add('family_restroom', 'All Gender Restroom', 'main', at('117')[1], sections=['117'])
add('family_restroom', 'All Gender Restroom', 'upper', at('331')[1], sections=['331'])
# The map's restroom pins (no section given), moved onto the concourse ring along their own direction.
for xy in ((183, 250), (210, 243), (410, 148), (437, 150)):
    add('restroom', 'Restroom', 'upper', on_ring(xy, RU, 1.0), offers='Toward the Kobe Bryant Entrance side.')
for xy in ((752, 430), (752, 500), (718, 583)):
    add('restroom', 'Restroom', 'upper', on_ring(xy, RU, 1.0), offers='By Sections 329 to 331.')
for xy in ((560, 780), (600, 745), (300, 820), (342, 825)):
    add('restroom', 'Restroom', 'upper', on_ring(xy, RU, 1.0), offers='Toward the Figueroa St. Entry side.')
add('guest_services', 'Guest Service Center', 'main', on_ring(MAISLE['M12'], RM, 1.04), offers='Main Concourse, across from aisle M12. Lost and found.')
add('guest_services', 'Guest Service Center', 'upper', on_ring(UAISLE['U6'], RU, 1.04), offers='Upper Concourse, across from aisle U6.')
add('first_aid', 'First Aid', 'main', on_ring(MAISLE['M3'], RM, 1.04), offers='Main Concourse, across from aisle M3.', source=AZ)
add('sensory', 'Sensory Pod', 'upper', on_ring(UAISLE['U3'], RU, 1.04), offers='Upper Concourse, across from aisle 3.', source=ACC)
for a in ('M6', 'M9', 'M17', 'M22'): add('water', 'Water fountain', 'main', on_ring(MAISLE[a], RM), offers=f'Main Concourse, aisle {a[1:]}.', source=AZ)
for a in ('U5', 'U16', 'U30'): add('water', 'Water fountain', 'upper', on_ring(UAISLE[a], RU), offers=f'Upper Concourse, aisle {a[1:]}.', source=AZ)
for xy in (m2u((295, 170)), m2u((520, 678))): add('merch', 'Team LA kiosk', 'main', xy)
for xy in ((330, 250), (480, 698)): add('merch', 'Team LA kiosk', 'upper', xy)
add('merch', 'Team LA Store', 'main', (900, 215), offers='At Star Plaza, beside the Star Plaza Entrance.', source=AZ)
add('box_office', 'Box Office', 'main', (672, 115), offers='At Star Plaza, by the Box Office Entrance.')
GATES = [('Kobe Bryant Entrance', (314, 75), 'Corner of Chick Hearn Ct. (11th St.) and Georgia St.'),
         ('Box Office Entrance', (672, 102), 'Chick Hearn Ct. side, by the Box Office.'),
         ('Star Plaza Entrance', (835, 197), 'Corner of Chick Hearn Ct. and Figueroa St., at Star Plaza.'),
         ('Star Plaza VIP Entrance', (955, 229), 'Star Plaza.'),
         ('Figueroa St. Entrance', (482, 880), 'Corner of 12th St. and Figueroa St.'),
         ('SW VIP Entrance', (12, 494), 'Southwest side, between the 11th Street and Figueroa entrances.')]
for n, xy, o in GATES: add('gate', n, 'main', xy, offers=o, source=AZ)
add('rideshare', 'Rideshare and taxi zone: Chick Hearn Ct.', 'main', (560, 14), offers='The white zone on Chick Hearn Ct., eastbound.', source=TRANS)
add('rideshare', 'Rideshare and taxi zone: Figueroa St.', 'main', (960, 600), offers='The white zone on Figueroa St., southbound, toward 12th St.', source=TRANS)

exec(open(Path(__file__).parent / '_helpers_spread.py').read())
spread(points)
data = {'venue': SLUG, 'name': 'Crypto.com Arena', 'updated': CHECKED, 'sourceLabel': 'cryptoarena.com',
        'note': 'On the arena’s own map, the stage sits at the northeast end, in front of Sections 113 to 117. Your show’s layout can differ.',
        'levels': [{'id': 'main', 'label': 'Main Concourse', 'image': '/img/house/crypto-main.svg', 'aspect': round(FW / FH, 4), 'sections': {k: dict(zip(('x', 'y'), norm(v))) for k, v in MAIN.items()}},
                   {'id': 'upper', 'label': 'Upper Concourse', 'image': '/img/house/crypto-upper.svg', 'aspect': round(FW / FH, 4), 'sections': {k: dict(zip(('x', 'y'), norm(v))) for k, v in UP.items()}}],
        'points': points}
(REPO / 'data/house' / f'{SLUG}.json').write_text(json.dumps(data, indent=1, ensure_ascii=False))
idx = REPO / 'data/house/index.json'; cur = json.loads(idx.read_text())
if SLUG not in cur: cur.append(SLUG)
idx.write_text(json.dumps(cur))
from collections import Counter; print(len(points), 'points', Counter((p['level'], p['kind']) for p in points))
