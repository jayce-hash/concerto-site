"""Build Madison Square Garden's House Map: four drawings (Concerto's own, from MSG's positions)
and the pin data, into the site repo."""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from msg_raw import *

REPO = Path(sys.argv[1])
SLUG = 'madison-square-garden'
(REPO / 'img/house').mkdir(parents=True, exist_ok=True)
(REPO / 'data/house').mkdir(parents=True, exist_ok=True)

NAVY, GOLD, CREAM, INK2, LINE, DIM, DIMTXT = '#121E36', '#C9A84C', '#F8F9F9', '#5B6578', '#D9DEE5', '#E6E9EE', '#9AA3B2'

def parse(s):
    out = {}
    for tok in s.split():
        k, v = tok.split(':'); x, y = v.split(','); out[k] = (int(x), int(y))
    return out

def parse_poi(s):
    return [(t.split(':')[0], tuple(int(n) for n in t.split(':')[1].split(','))) for t in s.split()]

# Main bowl: map thousandths -> px of MSG's 853x632 box, then crop to our canvas.
MAINP = parse(MAIN)
CROP = (115, 25, 735, 607)  # px box we draw: x0, y0, x1, y1
CW, CH = CROP[2] - CROP[0], CROP[3] - CROP[1]
def px(p): return (p[0] / 1000 * 853 - CROP[0], p[1] / 1000 * 632 - CROP[1])
def norm(p): x, y = px(p); return (round(x / CW, 4), round(y / CH, 4))
CENTER = (500, 497)

def outward(p, f):
    """Push a point away from the bowl's center (onto the concourse behind a section)."""
    return (CENTER[0] + (p[0] - CENTER[0]) * f, CENTER[1] + (p[1] - CENTER[1]) * f)

def label(x, y, t, on, w=30):
    fill, txt = (NAVY, '#FFFFFF') if on else (DIM, DIMTXT)
    return (f'<rect x="{x - w/2:.1f}" y="{y - 9:.1f}" width="{w}" height="18" rx="5" fill="{fill}"/>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="10" font-weight="700" fill="{txt}" text-anchor="middle">{t}</text>')

LEVEL_OF = lambda k: 'floor' if not k.isdigit() or len(k) == 1 else k[0]

def main_svg(active):
    cx, cy = px(CENTER)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" font-family="Helvetica, Arial, sans-serif">',
             f'<rect width="{CW}" height="{CH}" fill="{CREAM}"/>',
             f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{CW/2 - 8:.1f}" ry="{CH/2 - 8:.1f}" fill="#FFFFFF" stroke="{LINE}" stroke-width="2"/>',
             f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{CW*0.355:.1f}" ry="{CH*0.355:.1f}" fill="none" stroke="{LINE}" stroke-width="10" opacity="0.55"/>',
             f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{CW*0.245:.1f}" ry="{CH*0.25:.1f}" fill="#F1F3F6" stroke="{LINE}" stroke-width="1.5"/>']
    sx, sy = px(STAGE)
    parts.append(f'<rect x="{sx - 16:.1f}" y="{sy - 52:.1f}" width="32" height="104" rx="4" fill="{NAVY if active == "100" else "#7C879A"}"/>'
                 f'<text x="{sx:.1f}" y="{sy + 4:.1f}" font-size="9" font-weight="700" fill="#FFFFFF" text-anchor="middle" transform="rotate(-90 {sx:.1f} {sy:.1f})" letter-spacing="1.5">STAGE</text>')
    for k, p in MAINP.items():
        lv = LEVEL_OF(k)
        if (active == '400' and lv == '2') or (active != '400' and lv == '4'): continue  # 400s share the 200s' footprint
        on = (active == '100' and lv in ('floor', '1')) or (active == '200' and lv == '2') or (active == '400' and lv == '4')
        x, y = px(p)
        parts.append(label(x, y, k, on, 22 if lv == 'floor' else 30))
    parts.append('</svg>')
    return ''.join(parts)

BRP = parse(BRIDGE)
def bridge_svg():
    cx, cy = px(CENTER)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" font-family="Helvetica, Arial, sans-serif">',
             f'<rect width="{CW}" height="{CH}" fill="{CREAM}"/>',
             f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{CW/2 - 8:.1f}" ry="{CH/2 - 8:.1f}" fill="#FFFFFF" stroke="{LINE}" stroke-width="2"/>',
             f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{CW*0.3:.1f}" ry="{CH*0.3:.1f}" fill="#F1F3F6" stroke="{LINE}" stroke-width="1.5"/>',
             f'<text x="{cx:.1f}" y="{cy + 4:.1f}" font-size="11" font-weight="700" fill="{DIMTXT}" text-anchor="middle" letter-spacing="1.5">HYUNDAI BRIDGE</text>']
    for k, p in BRP.items():
        x, y = px(p); parts.append(label(x, y, k, True))
    parts.append('</svg>')
    return ''.join(parts)

# Outside: Concerto's schematic of MSG's own entrance map (streets, the building, Chase Square).
OW, OH = 620, 480
def outside_svg():
    road = '#E3E7EC'
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {OW} {OH}" font-family="Helvetica, Arial, sans-serif">',
         f'<rect width="{OW}" height="{OH}" fill="{CREAM}"/>',
         f'<rect x="0" y="20" width="{OW}" height="34" fill="{road}"/><rect x="0" y="{OH-54}" width="{OW}" height="34" fill="{road}"/>',
         f'<rect x="20" y="0" width="34" height="{OH}" fill="{road}"/><rect x="{OW-54}" y="0" width="34" height="{OH}" fill="{road}"/>',
         f'<text x="{OW/2}" y="42" font-size="12" font-weight="700" fill="{INK2}" text-anchor="middle" letter-spacing="1">W 33RD ST</text>',
         f'<text x="{OW/2}" y="{OH-32}" font-size="12" font-weight="700" fill="{INK2}" text-anchor="middle" letter-spacing="1">W 31ST ST</text>',
         f'<text x="41" y="{OH/2}" font-size="12" font-weight="700" fill="{INK2}" text-anchor="middle" letter-spacing="1" transform="rotate(-90 41 {OH/2})">8TH AVE</text>',
         f'<text x="{OW-37}" y="{OH/2}" font-size="12" font-weight="700" fill="{INK2}" text-anchor="middle" letter-spacing="1" transform="rotate(90 {OW-37} {OH/2})">7TH AVE</text>',
         f'<circle cx="255" cy="{OH/2}" r="150" fill="#FFFFFF" stroke="{LINE}" stroke-width="3"/>',
         f'<text x="255" y="{OH/2 - 6}" font-size="15" font-weight="700" fill="{NAVY}" text-anchor="middle" letter-spacing="1">MADISON</text>',
         f'<text x="255" y="{OH/2 + 14}" font-size="15" font-weight="700" fill="{NAVY}" text-anchor="middle" letter-spacing="1">SQUARE GARDEN</text>',
         f'<rect x="405" y="{OH/2 - 62}" width="150" height="124" rx="6" fill="#FFFFFF" stroke="{LINE}" stroke-width="2"/>',
         f'<text x="480" y="{OH/2 - 70}" font-size="10" font-weight="700" fill="{DIMTXT}" text-anchor="middle" letter-spacing="1.2">CHASE SQUARE</text>',
         *[f'<text x="{x}" y="{y}" font-size="11" font-weight="700" fill="{NAVY}" text-anchor="middle">{t}</text>' for x, y, t in
           ((132, 296, 'A'), (132, 192, 'B'), (190, 128, 'C'), (318, 128, 'D'), (556, 212, '7th Ave'), (438, 218, 'VIP N'), (438, 326, 'VIP S'), (112, 70, '8 Penn'))],
         '</svg>']
    return ''.join(p)

files = {'msg-outside.svg': outside_svg(), 'msg-100.svg': main_svg('100'), 'msg-200.svg': main_svg('200'), 'msg-400.svg': main_svg('400'), 'msg-bridge.svg': bridge_svg()}
for n, svg in files.items(): (REPO / 'img/house' / n).write_text(svg)

points = []
def add(kind, name, level, xy, sections=None, offers=None, tags=None, source=SEATMAP):
    points.append({'id': f'{level}-{len(points)+1}', 'kind': kind, 'name': name, 'level': level, 'x': xy[0], 'y': xy[1],
                   **({'sections': sections} if sections else {}), **({'offers': offers} if offers else {}),
                   **({'tags': tags} if tags else {}), 'source': source, 'verified': CHECKED})

# Outside (normalized to the outside drawing)
o = lambda x, y: (round(x / OW, 4), round(y / OH, 4))
add('gate', 'Chase Entrance A', 'outside', o(104, 292), offers='8th Avenue side, toward 31st Street. Your ticket shows the entrance for your seat.', source=ENTRANCES)
add('gate', 'Chase Entrance B', 'outside', o(104, 188), offers='8th Avenue side, toward 33rd Street. Has a CLEAR lane.', source=ENTRANCES)
add('gate', 'Chase Entrance C', 'outside', o(190, 98), offers='33rd Street side, toward 8th Avenue. Has a CLEAR lane.', source=ENTRANCES)
add('gate', 'Chase Entrance D', 'outside', o(318, 98), offers='33rd Street side, toward 7th Avenue.', source=ENTRANCES)
add('gate', '7th Ave Entrance', 'outside', o(556, 240), offers='Through Chase Square, on 7th Avenue between 31st and 33rd Streets. Accessible entrance.', tags=['accessible'], source=ENTRANCES)
add('gate', 'Lexus VIP North Entrance', 'outside', o(438, 186), offers='Off Chase Square.', source=ENTRANCES)
add('gate', 'Lexus VIP South Entrance', 'outside', o(438, 294), offers='Off Chase Square.', source=ENTRANCES)
add('gate', 'Accessible entrance at 8 Penn', 'outside', o(64, 64), offers='33rd Street and 8th Avenue.', tags=['accessible'], source=ACCESS)
add('merch', 'MSG Official Team Store', 'outside', o(478, 240), offers='In Chase Square.', source=FAQ)
add('rideshare', 'Rideshare pickup: 7th Avenue', 'outside', o(OW - 37, 110), offers='No official rideshare zone. Pick up and drop off on 7th Avenue between 31st and 34th Streets.', source=FAQ)
add('rideshare', 'Rideshare pickup: 8th Avenue', 'outside', o(37, 110), offers='No official rideshare zone. Pick up and drop off on 8th Avenue between 31st and 34th Streets.', source=FAQ)

def sec_point(keys, level, f):
    ps = [MAINP[k] for k in keys if k in MAINP] if level != 'bridge' else [BRP[k] for k in keys if k in BRP]
    p = (sum(a for a, _ in ps) / len(ps), sum(b for _, b in ps) / len(ps))
    return norm(outward(p, f))

DRINK = {'Mixed Drinks', 'Draft Beer', 'Craft Beer Garden', 'Courtside/Rinkside Bar', 'Rafters Bar', 'Bar at the Garden', 'Garden Pub', 'The Trophy Bar', 'Farley’s Bar', 'Bud Light', 'Beverage Grab & Go', 'Popcorn & Drinks'}
def tags_for(s):
    t = []
    if 'Gluten-Free' in s: t.append('gluten free')
    if 'Vegan' in s: t.append('vegan')
    if 'Halal' in s: t.append('halal')
    return t

def stands(table, level, f):
    for key, names in table.items():
        secs = []
        for part in key.replace(' ', '').split(','):
            if '-' in part:
                a, b = part.split('-'); secs += [str(n) for n in range(int(a), int(b) + 1)]
            else: secs.append(part)
        items = [n.strip() for n in names.split(',')]
        kind = 'bar' if all(i in DRINK for i in items) else 'stand'
        add(kind, names, level, sec_point(secs, level, f), sections=secs, tags=tags_for(names), source=FOOD)

stands(STANDS_100, '100', 1.27)
stands(STANDS_200, '200', 1.09)
stands(STANDS_400, '400', 1.12)
stands(STANDS_BRIDGE, 'bridge', 1.12)

KIND = {'m': ('restroom', 'Men’s restroom'), 'w': ('restroom', 'Women’s restroom'), 'retail': ('merch', 'Merchandise'),
        'elevator': ('elevator', 'Elevator'), 'escalator': ('escalator', 'Escalator'), 'restroom': ('restroom', 'Restroom')}
for lvl, src in (('100', POI_100), ('200', POI_200)):
    for k, p in parse_poi(src) + parse_poi(POI_ALL):
        kind, name = KIND[k]
        add(kind, name, lvl, norm(p))
for k, p in parse_poi(BRIDGE_POI):
    kind, name = KIND[k]; add(kind, name, 'bridge', norm(p))

# Guest services, from the FAQ and accessibility pages.
add('guest_services', 'Guest Services Office', '100', sec_point(['117'], '100', 1.36), sections=['117'],
    offers='Kalshi Concourse (sixth floor), outside Section 117. Sensory bags are available here at no cost with an ID.', source=ACCESS)
add('first_aid', 'First aid', '100', sec_point(['116'], '100', 1.38), sections=['117'],
    offers='Behind the Guest Services Office on the Kalshi Concourse (sixth floor), outside Section 117.', source=FAQ)
add('nursing', 'Nursing room', '100', sec_point(['118'], '100', 1.38), sections=['117'],
    offers='By the Guest Services Office on the Kalshi Concourse (sixth floor), outside Section 117.', source=FAQ)
add('guest_services', 'Guest experience booth', '200', sec_point(['206'], '200', 1.1), sections=['206'], offers='Outside Section 206.', source=ACCESS)
add('guest_services', 'Guest experience booth', 'bridge', sec_point(['328'], 'bridge', 1.1), sections=['328'], offers='Outside Section 328.', source=ACCESS)

# Pins that land on almost the same spot (a stand and a restroom both beside one section) are
# pushed apart a little, so each one can be tapped once the map is zoomed in.
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
    for q in points: q['x'], q['y'] = round(q['x'], 4), round(q['y'], 4)
spread(points)

def secmap(keys):
    return {k: dict(zip(('x', 'y'), norm(MAINP[k]))) for k in keys}
lv100 = [k for k in MAINP if LEVEL_OF(k) in ('floor', '1')]
lv200 = [k for k in MAINP if LEVEL_OF(k) == '2']
lv400 = [k for k in MAINP if LEVEL_OF(k) == '4']
data = {
    'venue': SLUG, 'name': 'Madison Square Garden', 'updated': CHECKED, 'sourceLabel': 'msg.com',
    'note': 'On MSG’s concert seat map, the stage sits in front of Sections 111 to 113. Your show’s layout can differ.',
    'levels': [
        {'id': '100', 'label': '100 Level', 'image': '/img/house/msg-100.svg', 'aspect': round(CW / CH, 4), 'sections': secmap(lv100)},
        {'id': '200', 'label': '200 Level', 'image': '/img/house/msg-200.svg', 'aspect': round(CW / CH, 4), 'sections': secmap(lv200)},
        {'id': '400', 'label': '400s', 'image': '/img/house/msg-400.svg', 'aspect': round(CW / CH, 4), 'sections': secmap(lv400)},
        {'id': 'bridge', 'label': 'Hyundai Bridge', 'image': '/img/house/msg-bridge.svg', 'aspect': round(CW / CH, 4),
         'sections': {k: dict(zip(('x', 'y'), norm(p))) for k, p in BRP.items()}},
        {'id': 'outside', 'label': 'Entrances', 'image': '/img/house/msg-outside.svg', 'aspect': round(OW / OH, 4), 'sections': {}},
    ],
    'points': points,
}
(REPO / 'data/house' / f'{SLUG}.json').write_text(json.dumps(data, indent=1, ensure_ascii=False))
(REPO / 'data/house/index.json').write_text(json.dumps([SLUG]))
from collections import Counter
print(len(points), 'points', Counter((p['level'], p['kind']) for p in points))
