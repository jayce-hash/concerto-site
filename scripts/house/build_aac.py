"""Build American Airlines Center's House Map: Concerto's own drawings of the Plaza and Terrace
concourses (positions read from AAC's official 2026 concourse maps) and the pin data.

Sources, read 2026-11-02:
- Concourse maps (Plaza and Terrace images, plus the interactive map's restroom pins): /floorplans
- Stands, bars, menus, and the section each sits outside: /food-beverage/concessions
- Entrances, guest relations, first aid, reverse ATMs, nursing room, rideshare: /plan-your-visit/arena-faq
Stand names come only from the concessions page (the interactive map still shows older names).
"""
import json, math, sys
from pathlib import Path

REPO = Path(sys.argv[1])
SLUG = 'american-airlines-center'
BASE = 'https://www.americanairlinescenter.com'
MAPS, FOOD, FAQ = BASE + '/floorplans', BASE + '/food-beverage/concessions', BASE + '/plan-your-visit/arena-faq'
CHECKED = '2026-11-02'
NAVY, GOLD, CREAM, INK2, LINE, DIM, DIMTXT = '#121E36', '#C9A84C', '#F8F9F9', '#5B6578', '#D9DEE5', '#E6E9EE', '#9AA3B2'

# Both official images are 3301 x 2548; positions below are in that image scaled to 853 x 658.
FW, FH = 853, 658
CROP = (8, 4, 845, 654)
CW, CH = CROP[2] - CROP[0], CROP[3] - CROP[1]
def norm(p): return (round((p[0] - CROP[0]) / CW, 4), round((p[1] - CROP[1]) / CH, 4))
def sp(s): return {k: tuple(int(n) for n in v.split(',')) for k, v in (t.split(':') for t in s.split())}

# Plaza (100 Level). West is up, north is right; the concert stage is at the south end (left).
PLAZA = sp("""101:230,297 102:240,246 103:271,216 104:316,207 105:362,207 106:409,207 107:457,207 108:504,207
109:548,207 110:598,209 111:623,249 112:623,297 113:623,350 114:617,402 115:592,432 116:549,440 117:503,440
118:457,440 119:409,440 120:362,440 121:313,438 122:272,430 123:246,387 124:233,345
12:410,294 15:462,294 18:519,294 11:410,326 14:462,326 17:519,326 10:410,355 13:462,355 16:519,355""")
P_CENTER, P_RING = (430, 326), (152, 135, 688, 517)   # concourse ring: x0, y0, x1, y1
STAGE = (323, 330)

# Terrace (300 Level), same frame.
TERR = sp("""301:150,331 302:150,285 303:159,240 304:177,200 305:218,143 306:254,123 307:300,100 308:342,100
309:391,100 310:438,100 311:486,98 312:551,100 313:608,113 314:650,143 315:695,195 316:717,230 317:728,283
318:728,333 319:728,384 320:717,431 321:696,468 322:650,524 323:607,549 324:551,575 325:487,575 326:438,575
327:393,575 328:342,575 329:302,567 330:254,543 331:219,524 332:180,461 333:162,418 334:150,374""")
T_CENTER, T_RING = (432, 337), (110, 69, 762, 597)

def ring_point(p, center, ring):
    """Where a ray from the bowl's center through a section meets the concourse ring."""
    dx, dy = p[0] - center[0], p[1] - center[1]
    ts = []
    if dx: ts += [(ring[0] - center[0]) / dx, (ring[2] - center[0]) / dx]
    if dy: ts += [(ring[1] - center[1]) / dy, (ring[3] - center[1]) / dy]
    t = min(t for t in ts if t > 0)
    return (center[0] + dx * t, center[1] + dy * t)

def label(x, y, t, on, w=30):
    fill, txt = (NAVY, '#FFFFFF') if on else (DIM, DIMTXT)
    return (f'<rect x="{x - w/2:.1f}" y="{y - 9:.1f}" width="{w}" height="18" rx="5" fill="{fill}"/>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="10" font-weight="700" fill="{txt}" text-anchor="middle">{t}</text>')

def c(p): return (p[0] - CROP[0], p[1] - CROP[1])

def svg(level):
    ring = P_RING if level == 'plaza' else T_RING
    x0, y0 = c(ring[:2]); x1, y1 = c(ring[2:])
    secs = PLAZA if level == 'plaza' else TERR
    xs = [c(p)[0] for k, p in secs.items() if len(k) == 3]; ys = [c(p)[1] for k, p in secs.items() if len(k) == 3]
    bx0, by0, bx1, by1 = min(xs) - 26, min(ys) - 22, max(xs) + 26, max(ys) + 22
    fx0, fy0, fx1, fy1 = bx0 + 62, by0 + 56, bx1 - 62, by1 - 56
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" font-family="Helvetica, Arial, sans-serif">',
             f'<rect width="{CW}" height="{CH}" fill="{CREAM}"/>',
             f'<rect x="26" y="26" width="{CW - 52}" height="{CH - 52}" rx="80" fill="#FFFFFF" stroke="{LINE}" stroke-width="2"/>',
             f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" rx="56" fill="none" stroke="{LINE}" stroke-width="10" opacity="0.55"/>',
             f'<rect x="{bx0:.1f}" y="{by0:.1f}" width="{bx1 - bx0:.1f}" height="{by1 - by0:.1f}" rx="120" fill="#FFFFFF" stroke="{LINE}" stroke-width="1.5"/>',
             f'<rect x="{fx0:.1f}" y="{fy0:.1f}" width="{fx1 - fx0:.1f}" height="{fy1 - fy0:.1f}" rx="70" fill="#F1F3F6" stroke="{LINE}" stroke-width="1.5"/>']
    for t, (tx, ty, rot) in {'WEST · VICTORY AVE': (CW / 2, 14, 0), 'EAST · N. HOUSTON ST': (CW / 2, CH - 6, 0),
                             'SOUTH · PNC PLAZA': (12, CH / 2, -90), 'NORTH · ALL-STAR WAY': (CW - 8, CH / 2, 90)}.items():
        parts.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="10" font-weight="700" fill="{DIMTXT}" text-anchor="middle" letter-spacing="1.2"'
                     + (f' transform="rotate({rot} {tx:.1f} {ty:.1f})"' if rot else '') + f'>{t}</text>')
    sx, sy = c(STAGE)
    parts.append(f'<rect x="{sx - 18:.1f}" y="{sy - 58:.1f}" width="36" height="116" rx="5" fill="{NAVY if level == "plaza" else "#7C879A"}"/>'
                 f'<text x="{sx:.1f}" y="{sy + 4:.1f}" font-size="9" font-weight="700" fill="#FFFFFF" text-anchor="middle" transform="rotate(-90 {sx:.1f} {sy:.1f})" letter-spacing="1.5">STAGE</text>')
    for k, p in secs.items():
        x, y = c(p); parts.append(label(x, y, k, True, 22 if len(k) < 3 else 30))
    parts.append('</svg>')
    return ''.join(parts)

(REPO / 'img/house').mkdir(parents=True, exist_ok=True)
(REPO / 'data/house').mkdir(parents=True, exist_ok=True)
(REPO / 'img/house/aac-plaza.svg').write_text(svg('plaza'))
(REPO / 'img/house/aac-terrace.svg').write_text(svg('terrace'))

points = []
def add(kind, name, level, xy, sections=None, offers=None, tags=None, source=MAPS):
    points.append({'id': f'{level}-{len(points)+1}', 'kind': kind, 'name': name, 'level': level, 'x': xy[0], 'y': xy[1],
                   **({'sections': sections} if sections else {}), **({'offers': offers} if offers else {}),
                   **({'tags': tags} if tags else {}), 'source': source, 'verified': CHECKED})

def at_section(sec):
    if sec in PLAZA: return 'plaza', norm(ring_point(PLAZA[sec], P_CENTER, P_RING))
    return 'terrace', norm(ring_point(TERR[sec], T_CENTER, T_RING))

MENU = {
 '7 Eleven Slurpee': 'Slurpees and Coca-Cola',
 'Big D Dogs + Brews': 'Niman Ranch Hot Dog, Sonoran Dog, Beer Brat, Nachos, Bottomless Popcorn, Beer and Wine',
 'Bonanno Brothers Pizzeria': 'Cheese and Pepperoni Pizza, Beer and Wine, Frozen Margaritas',
 'Bud and Burger': 'Smashburger Baskets, Chicken Tenders, Garlic Parmesan Fries, Bottomless Popcorn, Beer and Wine, Cold Brew',
 'DBQ': 'Brisket or Pulled Pork Sandwich, Loaded BBQ Nachos, BBQ Beer Brat, Brisket Mac and Cheese',
 'El Taco Tex': 'Street Tacos, Loaded Nachos, Vegan Tacos, Vegan Nachos, Churros, Elote Cup, Frozen Margaritas',
 'Fast Break': 'Chili Cheese Nacho, Texas Chili Cheese Dog, Niman Ranch Hot Dog, Soft Pretzel, Popcorn, Cotton Candy',
 'Hot dog stand': 'Niman Ranch Hot Dog, Sonoran Dog, Beer Brat, Nachos, Artisan Pretzel, Beer and Wine',
 'Grill Zone': 'Smashburger Baskets, Chicken Tenders, Grilled Chicken Sandwich, Garlic Parmesan Fries, Beer and Wine',
 'High Steaks': 'Texas Cheese Steak Sandwich, Cheese Steak Nachos, Corn Dog, S’mores Nachos, Frozen Margaritas',
 'Hot Popped and Twisted': 'Nachos, Soft Pretzel, Bottomless Popcorn, Peanuts, Beer and Wine',
 'Market to Go': 'Deli Sandwiches, Salads, Vegan Power Bowl, Fruit Cups, Gelato, Frozen Treats',
 'The Nutty Bavarian': 'Cinnamon Glazed Almonds, Cashews and Pecans',
 'Tostitos Cantina': 'Street Corn Nachos, Flamin’ Hot Elote Dog, Niman Ranch Hot Dog, Soft Pretzel, Beer and Wine',
 'Zavala’s Barbeque': 'Brisket Tacos, Sandwiches and Nachos, Smoked Brisket Dog, BBQ Popcorn',
 'Bud Light Bar': 'Bud Light Seltzers, Karbach, Kona, Golden Road, Michelob Ultra, Bud Light, Budweiser',
 'Karbach Craft Beer Bar': 'Light Circus, Lovestreet, Hopadillo, Jukebock',
 'Ranch Water Bar': 'Frozen Margaritas, Bottled and Canned Beer, Wine',
 'Michelob Ultra Bar': 'Michelob Ultra, Bud Light, Shock Top, rotating craft beers',
 'Modelo Beer Bar': 'Modelo, Modelo Negra, Pacifico, Corona, rotating imports',
 'Texas Craft Beer Bar': 'Ziegenbock, Saint Arnold, Fireman’s 4, Franconia',
}
STANDS = {  # as the concessions page states them: "outside section ..."
 '7 Eleven Slurpee': '109 121', 'Big D Dogs + Brews': '318', 'Bonanno Brothers Pizzeria': '102 107 111 119 312 329',
 'Bud and Burger': '114 124', 'DBQ': '334', 'El Taco Tex': '105 117', 'Fast Break': '113 116 307 324',
 'Hot dog stand': '101 109 301', 'Grill Zone': '106 118 310 326', 'High Steaks': '108 120', 'Hot Popped and Twisted': '302 317',
 'Market to Go': '104 111 319', 'The Nutty Bavarian': '110', 'Tostitos Cantina': '104', 'Zavala’s Barbeque': '121',
}
BARS = {'Bud Light Bar': '111', 'Karbach Craft Beer Bar': '109', 'Ranch Water Bar': '327', 'Michelob Ultra Bar': '104',
        'Modelo Beer Bar': '114', 'Texas Craft Beer Bar': '116'}
for table, kind in ((STANDS, 'stand'), (BARS, 'bar')):
    for name, secs in table.items():
        for s in secs.split():
            lvl, xy = at_section(s)
            tags = ['vegan'] if 'Vegan' in MENU[name] else None
            add(kind, name, lvl, xy, sections=[s], offers=MENU[name], tags=tags, source=FOOD)

# Bars and lounges named on the official concourse maps.
add('bar', 'Modelo Gold Lion Bar & Grill', 'plaza', norm((140, 100)), offers='Southwest corner of the Plaza concourse.')
add('bar', 'Karbach Rotunda Bar', 'plaza', norm((634, 88)), offers='Northwest rotunda, Plaza level.')
add('bar', '1933 Ranch Bar & Lounge', 'terrace', norm((125, 83)), offers='Southwest corner of the Terrace level.')
add('bar', 'Casa Bacardí', 'terrace', norm((122, 588)), offers='Southeast corner of the Terrace level.')

# Restrooms. Plaza: the interactive map's pins (its 1985 x 2000 space). Terrace: the map's restroom icons.
def pin(x, y): return (x / 1985 * FW, (y / 2000 * 1.291 - 0.008) * FH)
for g, (x, y) in (('Men’s', (1420, 330)), ('Women’s', (1600, 500)), ('Men’s', (1600, 1050)), ('Women’s', (1430, 1230)),
                  ('Men’s', (570, 1230)), ('Women’s', (355, 1030)), ('Men’s', (355, 525)), ('Women’s', (570, 330))):
    add('restroom', f'{g} restroom', 'plaza', norm(pin(x, y)))
for x, y in ((310, 69), (360, 69), (410, 69), (462, 69), (566, 69), (236, 95), (656, 111), (123, 214), (741, 201), (110, 278),
             (110, 358), (110, 389), (762, 278), (122, 443), (739, 468), (262, 579), (638, 561), (310, 597), (360, 597),
             (410, 597), (462, 597), (566, 597)):
    add('restroom', 'Restroom', 'terrace', norm((x, y)))
FAM = 'Men’s, women’s and gender neutral family restrooms are in the corners of every concourse.'

for x, y in ((158, 105), (748, 141), (760, 513), (158, 561)):
    add('escalator', 'Escalator', 'terrace', norm((x, y)))
add('merch', 'Fan Shop', 'plaza', norm((775, 80)), offers='Northwest corner, Plaza level.')
add('merch', 'Fan Shop', 'plaza', norm((97, 140)), offers='Southwest side, Plaza level.')
add('merch', 'Fan Shop', 'terrace', norm((513, 71)), offers='West side, Terrace level.')
add('merch', 'Fan Shop', 'terrace', norm((513, 602)), offers='East side, Terrace level.')

# From the arena FAQ.
add('guest_services', 'Guest Relations', 'plaza', norm((300, 104)), sections=['104'],
    offers='Plaza concourse, across from Section 104. Open one hour before and after every event. Lost and found goes here.', source=FAQ)
add('guest_services', 'Guest Relations', 'terrace', norm((464, 612)), sections=['326'],
    offers='Terrace level, across from Section 326. Open one hour before and after every event.', source=FAQ)
add('first_aid', 'First aid', 'plaza', at_section('111')[1], sections=['111'], offers='Plaza concourse, near Section 111.', source=FAQ)
add('first_aid', 'First aid', 'terrace', norm((620, 83)), sections=['313'], offers='Terrace concourse, near Section 313.', source=FAQ)
add('atm', 'Reverse ATM (cash to card)', 'plaza', norm((168, 118)),
    offers='The arena is cashless. Next to the Modelo Gold Lion Bar & Grill, southwest Plaza level.', source=FAQ)
add('atm', 'Reverse ATM (cash to card)', 'plaza', norm((735, 560)),
    offers='The arena is cashless. Next to the Michelob Ultra Club, northeast Plaza level.', source=FAQ)
add('nursing', 'Nursing room', 'plaza', norm((190, 150)), offers='Across from the Modelo Gold Lion Bar & Grill, Plaza level. Locking door.', source=FAQ)
add('gate', 'South Entry (PNC Plaza)', 'plaza', norm((32, 300)), offers='Main entrance, open to all ticketed guests.', source=FAQ)
add('gate', 'West Entry (DART Station)', 'plaza', norm((430, 20)), offers='Main entrance, open to all ticketed guests. Closest to the DART station.', source=FAQ)
add('gate', 'North Entry (ADA Parking)', 'plaza', norm((828, 300)), offers='Main entrance, open to all ticketed guests. By the ADA parking.', tags=['accessible'], source=FAQ)
add('gate', 'East Entry (Lexus Garage)', 'plaza', norm((430, 636)), offers='Main entrance, open to all ticketed guests. Across from the Lexus Garage.', source=FAQ)
add('gate', 'Platinum Entry (VIP)', 'plaza', norm((825, 408)), offers='Northeast, All-Star Way side. Suite and Premier Seat holders only.', source=FAQ)
add('box_office', 'Box office', 'plaza', norm((708, 630)), offers='On North Houston Street, across from the Lexus Garage.', source=FAQ)
add('rideshare', 'Uber pickup: All-Star Way', 'plaza', norm((838, 200)), offers='Designated Uber pickup and drop-off on All-Star Way (north side).', source=FAQ)
add('rideshare', 'Uber pickup: Nowitzki Way', 'plaza', norm((22, 200)), offers='Designated Uber pickup and drop-off on Nowitzki Way (south side).', source=FAQ)

def spread(points, gap=0.022, rounds=40):
    for _ in range(rounds):
        moved = False
        for i, a in enumerate(points):
            for b in points[i + 1:]:
                if a['level'] != b['level']: continue
                dx, dy = b['x'] - a['x'], b['y'] - a['y']; d = math.hypot(dx, dy)
                if d < gap:
                    push = (gap - d) / 2
                    ux, uy = (dx / d, dy / d) if d else (1.0, 0.0)  # same spot: split them sideways
                    a['x'] -= ux * push; a['y'] -= uy * push
                    b['x'] += ux * push; b['y'] += uy * push
                    moved = True
        if not moved: break
    for q in points: q['x'], q['y'] = round(min(max(q['x'], 0.01), 0.99), 4), round(min(max(q['y'], 0.01), 0.99), 4)
spread(points)

data = {
    'venue': SLUG, 'name': 'American Airlines Center', 'updated': CHECKED, 'sourceLabel': 'americanairlinescenter.com',
    'note': 'On AAC’s concert seating map, the stage sits at the south end, in front of Sections 101 and 124. Your show’s layout can differ. ' + FAM,
    'levels': [
        {'id': 'plaza', 'label': 'Plaza (100s)', 'image': '/img/house/aac-plaza.svg', 'aspect': round(CW / CH, 4),
         'sections': {k: dict(zip(('x', 'y'), norm(p))) for k, p in PLAZA.items()}},
        {'id': 'terrace', 'label': 'Terrace (300s)', 'image': '/img/house/aac-terrace.svg', 'aspect': round(CW / CH, 4),
         'sections': {k: dict(zip(('x', 'y'), norm(p))) for k, p in TERR.items()}},
    ],
    'points': points,
}
(REPO / 'data/house' / f'{SLUG}.json').write_text(json.dumps(data, indent=1, ensure_ascii=False))
idx = REPO / 'data/house/index.json'
cur = json.loads(idx.read_text()) if idx.exists() else []
if SLUG not in cur: cur.append(SLUG)
idx.write_text(json.dumps(cur))
from collections import Counter
print(len(points), 'points', Counter((p['level'], p['kind']) for p in points))
