#!/usr/bin/env python3
"""
Concerto static build. Bakes JSON data into pages, upgrades schema,
adds nearby-venue links, converts images to WebP, adds lazy loading,
skip links, analytics hook, and generates static city guide pages.

Idempotent: safe to re-run after data/*.json changes.
Run from the site root:  python3 build_static.py
"""
import json, math, os, re, sys, glob, urllib.parse, html.parser

ROOT = os.path.dirname(os.path.abspath(__file__))
def rp(*p): return os.path.join(ROOT, *p)

def read(p):  return open(rp(p), encoding='utf-8').read()
def write(p, s): open(rp(p), 'w', encoding='utf-8').write(s)

# ================= STAGE 0 (opt-in): sync data from the master sheet =================
# Run as:  python3 build_static.py --from-sheet            (fetches the published Google Sheet)
#          python3 build_static.py --from-sheet local.csv  (reads a local CSV export instead)
# Merge-based: only fields managed by the sheet are updated; unknown fields
# (isFestival, legacy guideUrl formats, etc.) are preserved, and entries not in
# the sheet are left untouched. Backs up current JSONs first.
MASTER_SHEET_CSV = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vT39Vf8zB5l1Vnpyi2qVacwp_3ddGcdU-0yXGWN2VypxDhCtC0XgcXZ8t7Hz1X-iBCQdPsCcrT0Y-7r/pub?output=csv'
if '--from-sheet' in sys.argv:
    import csv as _csv, datetime as _dt, shutil as _sh, io as _io, urllib.request as _rq
    _arg = sys.argv[sys.argv.index('--from-sheet') + 1] if len(sys.argv) > sys.argv.index('--from-sheet') + 1 else None
    if _arg and os.path.exists(_arg):
        _raw = open(_arg, encoding='utf-8-sig').read()
    else:
        _raw = _rq.urlopen(MASTER_SHEET_CSV, timeout=30).read().decode('utf-8-sig')
    _rows = list(_csv.DictReader(_io.StringIO(_raw)))
    _req = {'slug','name','bag_summary','parking_note','concessions_note'}
    assert len(_rows) >= 300, f'sheet sanity check failed: only {len(_rows)} rows'
    assert _req.issubset(_rows[0].keys()), f'sheet missing columns: {_req - set(_rows[0].keys())}'
    _bk = rp('data', 'backup-' + _dt.date.today().isoformat())
    os.makedirs(_bk, exist_ok=True)
    for _f in ['venues.json','bag_policies.json','parking.json','concessions.json']:
        _sh.copy2(rp('data', _f), os.path.join(_bk, _f))
    _V = json.load(open(rp('data/venues.json')))
    _B = json.load(open(rp('data/bag_policies.json')))
    _P = json.load(open(rp('data/parking.json')))
    _C = json.load(open(rp('data/concessions.json')))
    _vmap = {v['id']: v for v in _V}
    def _n(s): return re.sub(r'[^a-z0-9]', '', str(s or '').lower())
    def _key(d, slug):
        if slug in d: return slug
        n = _n(slug)
        for k in d:
            if _n(k) == n: return k
        return slug
    def _split(s): return [x.strip() for x in (s or '').split('|') if x.strip()]
    def _num(s):
        try: return float(s)
        except (TypeError, ValueError): return None
    _order = []
    for r in _rows:
        sl = r['slug'].strip()
        if not sl: continue
        _order.append(sl)
        if r.get('status','').strip() != 'no-page':
            ve = dict(_vmap.get(sl, {'guideUrl': '/cityguide/' + sl}))
            ve.update({'id': sl, 'name': r.get('name',''), 'city': r.get('city',''), 'state': r.get('state',''),
                       'country': r.get('country',''), 'lat': _num(r.get('lat')), 'lng': _num(r.get('lng'))})
            _vmap[sl] = ve
        if any((r.get(k) or '').strip() for k in ['bag_summary','bag_allowed','bag_not_allowed','bag_note','bag_official_link']):
            k = _key(_B, sl); e = dict(_B.get(k, {}))
            e.update({'summary': r.get('bag_summary',''), 'fullLink': r.get('bag_official_link',''),
                      'updated': r.get('bag_verified',''), 'allowed': _split(r.get('bag_allowed')),
                      'notAllowed': _split(r.get('bag_not_allowed')), 'note': r.get('bag_note',''),
                      'venueName': r.get('name',''), 'city': r.get('city',''), 'state': r.get('state','')})
            e.setdefault('guideUrl',''); _B[k] = e
        if any((r.get(k) or '').strip() for k in ['parking_note','parking_lots','parking_official_link','rideshare_note']):
            k = _key(_P, sl); e = dict(_P.get(k, {}))
            e.update({'note': r.get('parking_note',''), 'officialParkingUrl': r.get('parking_official_link',''),
                      'rideshare': r.get('rideshare_note',''), 'lots': _split(r.get('parking_lots'))})
            _P[k] = e
        if any((r.get(k) or '').strip() for k in ['concessions_note','concessions_stands','concessions_official_link']):
            k = _key(_C, sl); e = dict(_C.get(k, {}))
            e.update({'note': r.get('concessions_note',''), 'officialConcessionsUrl': r.get('concessions_official_link',''),
                      'stands': _split(r.get('concessions_stands'))})
            _C[k] = e
    _sheet_slugs = set(_order)
    _new_venues = [_vmap[s] for s in _order if s in _vmap] + [v for v in _V if v['id'] not in _sheet_slugs]
    json.dump(_new_venues, open(rp('data/venues.json'),'w'), indent=2, ensure_ascii=False)
    json.dump(_B, open(rp('data/bag_policies.json'),'w'), indent=2, ensure_ascii=False)
    json.dump(_P, open(rp('data/parking.json'),'w'), indent=2, ensure_ascii=False)
    json.dump(_C, open(rp('data/concessions.json'),'w'), indent=2, ensure_ascii=False)
    print(f'sheet sync (merge): {len(_new_venues)} venues, {len(_B)} bag, {len(_P)} parking, {len(_C)} concessions (backup in {_bk})')

# ---------- data ----------
venues      = json.load(open(rp('data/venues.json')))
bag         = json.load(open(rp('data/bag_policies.json')))
parking     = json.load(open(rp('data/parking.json')))
concessions = json.load(open(rp('data/concessions.json')))
top_picks   = json.load(open(rp('data/top_picks.json')))
besteats    = json.load(open(rp('besteats.json')))
vmap = {v['id']: v for v in venues}

def norm(s): return re.sub(r'[^a-z0-9]', '', str(s or '').lower())
def pick(obj, slug):
    if not obj: return None
    if slug in obj: return obj[slug]
    n = norm(slug)
    for k in obj:
        if norm(k) == n: return obj[k]
    return None

# esc() matches the JS widget exactly (&, <, >, ")
def esc(s):
    return ('' if s is None else str(s)).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

# ---------- 1. cvi pre-render (port of venue-info.js) ----------
FEAT_ID = {'Bag Policy':'bag','Parking':'parking','Concessions':'concessions','Rideshare':'rideshare'}
def feature(eyebrow, title, body):
    if not body: return ''
    return (f'<section class="cvi-feature" id="{FEAT_ID.get(title,"")}"><div class="cvi-feature-head">\n'
            f'      <span class="cvi-eyebrow">{esc(eyebrow)}</span>\n'
            f'      <h2 class="cvi-title">{esc(title)}</h2></div>{body}</section>')
def block(label, inner, cls=''):
    return f'<div class="cvi-block"><span class="cvi-block-label {cls}">{esc(label)}</span>{inner}</div>'
def ulist(arr):
    return '<ul class="cvi-list">' + ''.join(f'<li>{esc(i)}</li>' for i in arr) + '</ul>'
def cta(href, text):
    return f'<a class="cvi-cta" href="{esc(href)}" target="_blank" rel="noopener noreferrer">{esc(text)} &rarr;</a>'

def render_bag(v):
    if not v: return ''
    b = ''
    if v.get('summary'): b += f'<p class="cvi-desc">{esc(v["summary"])}</p>'
    sub = []
    if v.get('allowed'):
        sub.append(f'<div class="cvi-subcard"><span class="cvi-block-label allow">Allowed</span>{ulist(v["allowed"])}</div>')
    if v.get('notAllowed'):
        sub.append(f'<div class="cvi-subcard"><span class="cvi-block-label deny">Not Allowed</span>{ulist(v["notAllowed"])}</div>')
    if sub: b += f'<div class="cvi-subgrid">{"".join(sub)}</div>'
    if v.get('note'): b += block('Extra Notes', f'<p class="cvi-desc">{esc(v["note"])}</p>')
    if v.get('fullLink'): b += cta(v['fullLink'], 'View Full Policy')
    return feature('Know Before You Go', 'Bag Policy', b)

def render_parking(v):
    if not v: return ''
    b = f'<p class="cvi-desc">{esc(v.get("note") or "Parking details for this venue are not available yet.")}</p>'
    if v.get('lots'): b += block('Key Lots', ulist(v['lots']))
    if v.get('officialParkingUrl'): b += cta(v['officialParkingUrl'], 'View Official Parking Guide')
    return feature('Getting There', 'Parking', b)

def render_concessions(v):
    if not v: return ''
    b = f'<p class="cvi-desc">{esc(v.get("note") or "Concessions details for this venue are not available yet.")}</p>'
    if v.get('stands'): b += block('Notable Stands', ulist(v['stands']))
    if v.get('officialConcessionsUrl'): b += cta(v['officialConcessionsUrl'], 'View Official Concessions Guide')
    return feature('Inside the Venue', 'Concessions', b)

def render_rideshare(park_v, venue):
    note = (park_v or {}).get('rideshare') or ''
    if re.match(r'^no specific rideshare', note, re.I): note = ''
    b = ''
    if note: b += f'<p class="cvi-desc">{esc(note)}</p>'
    if venue and venue.get('lat') is not None and venue.get('lng') is not None:
        from urllib.parse import quote
        lat, lng = quote(str(venue['lat'])), quote(str(venue['lng']))
        nm = quote(venue.get('name') or 'Venue')
        u = lambda q: f'https://m.uber.com/ul/?action=setPickup&{q}'
        links = [
            ('Uber to Venue',   u(f'pickup=my_location&dropoff[latitude]={lat}&dropoff[longitude]={lng}&dropoff[nickname]={nm}')),
            ('Uber from Venue', u(f'pickup[latitude]={lat}&pickup[longitude]={lng}&pickup[nickname]={nm}')),
            ('Lyft to Venue',   f'https://ride.lyft.com/?destination[latitude]={lat}&destination[longitude]={lng}'),
            ('Lyft from Venue', f'https://ride.lyft.com/?pickup[latitude]={lat}&pickup[longitude]={lng}'),
        ]
        btns = ''.join(f'<a class="cvi-btn" href="{h}" target="_blank" rel="noopener noreferrer">{t}</a>' for t, h in links)
        b += block('Use Rideshare Apps', f'<div class="cvi-ride-grid">{btns}</div>')
    return feature('Uber & Lyft', 'Rideshare', b)

def prerender_cvi(slug, feats):
    venue = vmap.get(slug) or next((v for v in venues if norm(v['id']) == norm(slug)), None)
    data = {'bag': pick(bag, slug), 'parking': pick(parking, slug), 'concessions': pick(concessions, slug)}
    out = ''
    for f in feats:
        if f == 'bag': out += render_bag(data['bag'])
        elif f == 'parking': out += render_parking(data['parking'])
        elif f == 'concessions': out += render_concessions(data['concessions'])
        elif f == 'rideshare': out += render_rideshare(data['parking'], venue)
    return out

# ---------- 2. schema ----------
def venue_type(name):
    n = name.lower()
    if re.search(r'\b(stadium|arena|coliseum|dome|fieldhouse|field house|forum|garden|center|centre)\b', n):
        return 'StadiumOrArena'
    if re.search(r'\b(theat(er|re)|hall|opera|playhouse|amphitheat(er|re)|auditorium|pavilion)\b', n):
        return 'PerformingArtsTheater'
    return 'MusicVenue'

def clean_txt(s, limit=550):
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    return s[:limit].rsplit(' ', 1)[0] + '…' if len(s) > limit else s

def venue_schema(slug, name):
    v = vmap.get(slug, {})
    url = f'https://concertocity.com/venues/{slug}'
    place = {
        '@type': venue_type(name), 'name': name, 'url': url,
        'description': f'Venue guide for {name}, bag policies, parking, concessions, rideshare, and city guides for concertgoers.',
    }
    addr = {}
    if v.get('city'): addr['addressLocality'] = v['city']
    if v.get('state'): addr['addressRegion'] = v['state']
    if v.get('country'): addr['addressCountry'] = v['country']
    if addr: place['address'] = {'@type': 'PostalAddress', **addr}
    if v.get('lat') is not None and v.get('lng') is not None:
        place['geo'] = {'@type': 'GeoCoordinates', 'latitude': v['lat'], 'longitude': v['lng']}
    crumbs = {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': 'https://concertocity.com'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Venues', 'item': 'https://concertocity.com/venues.html'},
        {'@type': 'ListItem', 'position': 3, 'name': name, 'item': url},
    ]}
    faqs = []
    b, p, c = pick(bag, slug), pick(parking, slug), pick(concessions, slug)
    if b and b.get('summary'):
        ans = b['summary']
        if b.get('notAllowed'): ans += ' Not allowed: ' + ', '.join(b['notAllowed'][:6]) + '.'
        faqs.append((f'What is the bag policy at {name}?', ans))
    if p and p.get('note'):
        faqs.append((f'Where can I park at {name}?', p['note']))
    if c and c.get('note'):
        faqs.append((f'What food and drink options are at {name}?', c['note']))
    graph = [place, crumbs]
    if faqs:
        graph.append({'@type': 'FAQPage', 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': clean_txt(a)}}
            for q, a in faqs]})
    return json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, indent=2)

# ---------- 3. nearby venues ----------
def haversine(a, b):
    R = 3958.8  # miles
    la1, lo1, la2, lo2 = map(math.radians, [a['lat'], a['lng'], b['lat'], b['lng']])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(h))

geo_venues = [v for v in venues if v.get('lat') is not None and v.get('lng') is not None]
def nearby_html(slug):
    me = vmap.get(slug)
    if not me or me.get('lat') is None: return ''
    others = sorted((v for v in geo_venues if v['id'] != slug and os.path.exists(rp('venues', v['id'] + '.html'))),
                    key=lambda v: haversine(me, v))[:4]
    if not others: return ''
    metric = me.get('country') and me['country'] != 'US'
    cards = []
    for v in others:
        d = haversine(me, v)
        dist = f'{d*1.60934:.1f} km away' if metric else f'{d:.1f} mi away'
        loc = ', '.join(x for x in [v.get('city'), v.get('state')] if x)
        cards.append(f'<a class="nearby-card" href="/venues/{v["id"]}">'
                     f'<span class="nearby-name">{esc(v["name"])}</span>'
                     f'<span class="nearby-city">{esc(loc)}</span>'
                     f'<span class="nearby-dist">{dist}</span></a>')
    return ('\n    <!-- Nearby Venues (generated by build_static.py) -->\n'
            '    <section class="nearby-section reveal">\n'
            '      <div class="section-header"><div><span class="eyebrow">Explore More</span>'
            '<h2 class="section-title">Nearby Venues</h2></div></div>\n'
            '      <div class="nearby-grid">' + ''.join(cards) + '</div>\n'
            '    </section>\n\n    ')

NEARBY_CSS = '''
/* ---- Nearby Venues (generated by build_static.py) ---- */
.nearby-section{background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius-lg,24px);padding:2.5rem;margin:0 4% 1.5rem;max-width:calc(1280px - 8%);box-shadow:var(--shadow-sm);}
.nearby-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;}
@media(max-width:960px){.nearby-grid{grid-template-columns:1fr 1fr;}}
@media(max-width:560px){.nearby-grid{grid-template-columns:1fr;}}
.nearby-card{background:var(--bg);border:1px solid var(--border);border-radius:16px;padding:1.15rem 1.25rem;display:flex;flex-direction:column;gap:5px;transition:transform .3s cubic-bezier(0.16,1,0.3,1),box-shadow .3s cubic-bezier(0.16,1,0.3,1);}
.nearby-card:hover{transform:translateY(-2px);box-shadow:var(--shadow-md);}
.nearby-name{font-weight:600;font-size:.95rem;color:var(--text);}
.nearby-city{color:var(--text-dim);font-size:.8rem;}
.nearby-dist{color:var(--gold);font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-top:2px;}
'''

# ---------- shared page transforms ----------
SKIP_SNIPPET = ('<style>.skip-link{position:absolute;left:-9999px;top:0;z-index:2000;background:#121E36;color:#fff;'
                'padding:10px 18px;border-radius:0 0 12px 0;font-size:.8rem;text-decoration:none;}'
                '.skip-link:focus{left:0;}</style>'
                '<a class="skip-link" href="#main-content">Skip to content</a>')

ANALYTICS_TAG = '<script defer src="/analytics.js"></script>'

def add_skip_link(html_src):
    if 'class="skip-link"' in html_src or '<main' not in html_src: return html_src
    html_src = re.sub(r'(<body[^>]*>)', r'\1' + SKIP_SNIPPET, html_src, count=1)
    if 'id="main-content"' not in html_src:
        html_src = re.sub(r'<main(?![^>]*\bid=)', '<main id="main-content"', html_src, count=1)
    return html_src

def add_analytics(html_src):
    if 'analytics.js' in html_src or 'noindex' in html_src[:3000]: return html_src
    return html_src.replace('</head>', '  ' + ANALYTICS_TAG + '\n</head>', 1)

def add_lazy(html_src):
    def fix(m):
        tag = m.group(0)
        if 'loading=' in tag or 'nav-logo-img' in tag or 'hero-logo' in tag: return tag
        return tag[:4] + ' loading="lazy" decoding="async"' + tag[4:]
    return re.sub(r'<img\b[^>]*', fix, html_src)

# ---------- run: venue pages ----------
changed, faq_count, nearby_count = 0, 0, 0
for fn in sorted(os.listdir(rp('venues'))):
    if not fn.endswith('.html'): continue
    slug = fn[:-5]
    src = read(f'venues/{fn}')
    orig = src

    # 1: pre-render cvi (balanced-div replacement, safe on re-runs)
    m = re.search(r'<div class="cvi" data-slug="([^"]+)" data-features="([^"]+)"[^>]*>', src)
    if m:
        # walk forward counting <div/</div to find the true closing tag
        depth, pos, end = 1, m.end(), None
        for t in re.finditer(r'<div\b|</div>', src[m.end():]):
            depth += 1 if t.group(0) != '</div>' else -1
            if depth == 0:
                end = m.end() + t.end(); break
        if end is None:
            raise SystemExit(f'unbalanced cvi div in venues/{fn}')
        feats = [f.strip() for f in m.group(2).split(',') if f.strip()]
        inner = prerender_cvi(m.group(1), feats)
        if not inner:
            inner = f'<p class="cvi-empty">Venue info for &ldquo;{esc(m.group(1))}&rdquo; isn\'t available yet.</p>'
        src = src[:m.start()] + (f'<div class="cvi" data-slug="{m.group(1)}" data-features="{m.group(2)}" data-static="1">{inner}</div>') + src[end:]

    # 2: schema
    name_m = re.search(r'<h1 class="venue-name">([^<]+)</h1>', src)
    name = name_m.group(1).replace('&amp;', '&') if name_m else (vmap.get(slug, {}).get('name') or slug)
    sm = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', src, re.S)
    if sm:
        new_schema = venue_schema(slug, name)
        if '"FAQPage"' in new_schema: faq_count += 1
        src = src[:sm.start()] + '<script type="application/ld+json">\n' + new_schema + '\n  </script>' + src[sm.end():]

    # 2b: title + description with city
    v = vmap.get(slug, {})
    if v.get('city'):
        city = v['city']
        loc = city + (f', {v["state"]}' if v.get('state') else '')
        src = re.sub(r'<title>[^<]*</title>',
                     f'<title>{esc(name)} Bag Policy, Parking &amp; City Guide | {esc(city)} | Concerto</title>',
                     src, count=1)
        src = re.sub(r'(<meta name="description" content=")[^"]*(")',
                     r'\1' + esc(f'Everything you need for {name} in {loc}: bag policy, parking, concessions, rideshare zones, and a curated city guide. Know before you go with Concerto.') + r'\2',
                     src, count=1)

    # 3: nearby venues (insert before App CTA)
    if 'nearby-section' not in src:
        nb = nearby_html(slug)
        if nb and '<!-- App CTA -->' in src:
            src = src.replace('<!-- App CTA -->', nb + '<!-- App CTA -->', 1)
            nearby_count += 1

    # 7-9: lazy, skip link, analytics
    src = add_lazy(add_skip_link(add_analytics(src)))

    if src != orig:
        write(f'venues/{fn}', src); changed += 1

print(f'venues: {changed} updated, {faq_count} with FAQ schema, {nearby_count} with nearby sections')

# patch widget js to skip pre-rendered divs
wjs = read('venue-info/venue-info.js')
if 'data-static' not in wjs:
    wjs = wjs.replace('async function render(el) {',
                      "async function render(el) {\n    if (el.getAttribute('data-static') === '1') return; // pre-rendered by build_static.py")
    write('venue-info/venue-info.js', wjs)

# append nearby css
vcss = read('venue-info/venue-info.css')
if 'nearby-section' not in vcss:
    write('venue-info/venue-info.css', vcss + NEARBY_CSS)

# ---------- tours + top-level pages: lazy, skip, analytics ----------
def touch_pages(paths):
    n = 0
    for p in paths:
        src = read(p); orig = src
        src = add_lazy(add_skip_link(add_analytics(src)))
        if src != orig: write(p, src); n += 1
    return n

tour_pages = [f'tours/{f}' for f in sorted(os.listdir(rp('tours'))) if f.endswith('.html')]
SKIP_TOP = {'login.html'}  # noindex pages skip analytics automatically; leave login alone entirely
top_pages = [f for f in sorted(os.listdir(ROOT)) if f.endswith('.html') and not f.startswith('mobile') and f not in SKIP_TOP]
print('tours touched:', touch_pages(tour_pages))
print('top-level touched:', touch_pages(top_pages))

# ---------- analytics.js (single-file activation) ----------
if not os.path.exists(rp('analytics.js')):
    write('analytics.js', '''/* Concerto analytics loader.
   To activate: create a GA4 property at analytics.google.com,
   then replace the placeholder ID below with your G- ID. One file, whole site. */
(function () {
  var ID = 'G-XXXXXXXXXX';
  if (ID.indexOf('XXXXXXXX') !== -1) return; // not configured yet, do nothing
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('config', ID);
})();
''')
print('analytics.js written')

# ================= STAGE 2: media + city guides =================
from PIL import Image

# ---------- 6. images -> WebP ----------
converted = 0
for dirpath, _, files in os.walk(rp('img/cityguides')):
    for f in files:
        if not f.lower().endswith('.jpg'): continue
        src_p = os.path.join(dirpath, f)
        dst_p = src_p[:-4] + '.webp'
        if not os.path.exists(dst_p):
            im = Image.open(src_p).convert('RGB')
            if max(im.size) > 1600:
                r = 1600 / max(im.size)
                im = im.resize((round(im.width*r), round(im.height*r)), Image.LANCZOS)
            im.save(dst_p, 'WEBP', quality=80, method=6)
            converted += 1
        os.remove(src_p)
print('images converted to webp:', converted)

# update photo refs in top_picks.json (preserve structure)
tp_raw = read('data/top_picks.json')
tp_new = tp_raw.replace('.jpg"', '.webp"')
if tp_new != tp_raw:
    write('data/top_picks.json', tp_new)
    top_picks = json.loads(tp_new)
print('top_picks.json photo refs -> webp')

# ---------- 5. static city guide pages ----------
def slugify(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', str(s).lower())).strip('-')

def find_photo(vslug, item):
    if item.get('photo') and os.path.exists(rp(item['photo'].lstrip('/'))):
        return '/' + item['photo'].lstrip('/')
    d = rp('img/cityguides', vslug)
    if os.path.isdir(d):
        want = slugify(item['name'])
        for f in os.listdir(d):
            if slugify(os.path.splitext(f)[0]) == want:
                return f'/img/cityguides/{vslug}/{f}'
    return None

def hero_photo(vslug, vname):
    d = rp('img/cityguides', vslug)
    if os.path.isdir(d):
        want = slugify(vname)
        for f in os.listdir(d):
            if slugify(os.path.splitext(f)[0]) == want:
                return f'/img/cityguides/{vslug}/{f}'
    return None

GUIDE_CSS = '''<style>
.guide-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.25rem;}
@media(max-width:960px){.guide-grid{grid-template-columns:1fr 1fr;}}
@media(max-width:600px){.guide-grid{grid-template-columns:1fr;}}
.guide-card{background:var(--bg);border:1px solid var(--border);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;transition:transform .3s cubic-bezier(0.16,1,0.3,1),box-shadow .3s cubic-bezier(0.16,1,0.3,1);}
.guide-card:hover{transform:translateY(-2px);box-shadow:var(--shadow-md);}
.guide-card img{width:100%;height:180px;object-fit:cover;}
.guide-card-body{padding:1.1rem 1.2rem 1.3rem;display:flex;flex-direction:column;gap:6px;}
.guide-card-name{font-weight:600;font-size:1rem;color:var(--text);}
.guide-card-notes{color:var(--text-dim);font-size:.85rem;line-height:1.55;}
.guide-card-addr{color:var(--text-xdim);font-size:.75rem;margin-top:auto;padding-top:6px;}
.guide-badge{display:inline-block;align-self:flex-start;background:linear-gradient(135deg,var(--gold),var(--gold-light));color:var(--text);font-size:.62rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:3px 10px;border-radius:99px;}
.guide-hero-img{width:100%;max-width:calc(1280px - 8%);margin:0 auto 1.5rem;border-radius:var(--radius-lg,24px);overflow:hidden;box-shadow:var(--shadow-md);padding:0;}
.guide-hero-img img{width:100%;height:340px;object-fit:cover;display:block;}
@media(max-width:600px){.guide-hero-img img{height:200px;}}
</style>'''

def guide_section(title, eyebrow, cards):
    if not cards: return ''
    return ('    <section class="events-section reveal">\n'
            f'      <div class="section-header"><div><span class="eyebrow">{esc(eyebrow)}</span>'
            f'<h2 class="section-title">{esc(title)}</h2></div></div>\n'
            f'      <div class="guide-grid">{"".join(cards)}</div>\n'
            '    </section>\n')

def guide_card(vslug, item, badge=None):
    photo = find_photo(vslug, item)
    img = f'<img src="{esc(photo)}" alt="{esc(item["name"])}" loading="lazy" decoding="async">' if photo else ''
    badge_html = f'<span class="guide-badge">{esc(badge)}</span>' if badge else ''
    notes = f'<p class="guide-card-notes">{esc(item.get("notes") or "")}</p>' if item.get('notes') else ''
    addr = f'<span class="guide-card-addr">{esc(item.get("address") or "")}</span>' if item.get('address') else ''
    extra = ' &middot; '.join(esc(x) for x in [item.get('cuisine'), item.get('walk')] if x)
    extra = f'<span class="guide-card-addr">{extra}</span>' if extra else ''
    return (f'<article class="guide-card">{img}<div class="guide-card-body">{badge_html}'
            f'<span class="guide-card-name">{esc(item["name"])}</span>{notes}{extra}{addr}</div></article>')

tp_by_slug = {v['slug']: v for v in top_picks}
be_by_slug = {v['slug']: v for v in besteats}
guide_slugs = []  # static guides disabled: /cityguide/* is the interactive map SPA, leave it alone
built_guides = []

for gslug in guide_slugs:
    shell_path = rp('venues', gslug + '.html')
    if not os.path.exists(shell_path):
        print('  skip guide (no venue shell):', gslug); continue
    tp_v, be_v = tp_by_slug.get(gslug), be_by_slug.get(gslug)
    meta = tp_v or be_v
    vname, city = meta['venueName'], meta.get('city') or ''
    state = meta.get('state') or ''
    loc = ', '.join(x for x in [city, state] if x)

    tp_items = (tp_v or {}).get('items', [])
    tp_names = {slugify(i['name']) for i in tp_items}
    be_items = [i for i in (be_v or {}).get('items', []) if slugify(i['name']) not in tp_names]

    cards_tp = [guide_card(gslug, i, badge=(i.get('badge') or ('Featured Partner' if i.get('sponsored') else None))) for i in tp_items]
    cards_be = [guide_card(gslug, i) for i in be_items]

    hero = hero_photo(gslug, vname)
    hero_html = (f'    <div class="guide-hero-img"><img src="{esc(hero)}" alt="{esc(vname)}" decoding="async"></div>\n' if hero else '')

    url = f'https://concertocity.com/cityguide/{gslug}'
    all_items = tp_items + be_items
    schema = json.dumps({'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebPage', 'name': f'{vname} City Guide', 'url': url,
         'description': f'The best restaurants and bars near {vname}' + (f' in {loc}' if loc else '') + ', curated for concertgoers and sports fans.',
         'isPartOf': {'@type': 'WebSite', 'name': 'Concerto', 'url': 'https://concertocity.com'}},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': 'https://concertocity.com'},
            {'@type': 'ListItem', 'position': 2, 'name': 'City Guides', 'item': 'https://concertocity.com/cityguides.html'},
            {'@type': 'ListItem', 'position': 3, 'name': f'{vname} City Guide', 'item': url}]},
        {'@type': 'ItemList', 'name': f'Best food and drinks near {vname}',
         'itemListElement': [{'@type': 'ListItem', 'position': i+1,
                              'item': {'@type': 'FoodEstablishment', 'name': it['name'],
                                       **({'address': it['address']} if it.get('address') else {})}}
                             for i, it in enumerate(all_items)]},
    ]}, ensure_ascii=False, indent=2)

    shell = read(f'venues/{gslug}.html')
    head_end = shell.index('<main')
    main_close = shell.index('</main>') + len('</main>')
    head = shell[:head_end]
    tail = shell[main_close:]

    title = f'{vname} City Guide | Best Restaurants &amp; Bars Nearby | Concerto'
    desc = esc(f'Where to eat and drink near {vname}' + (f' in {loc}' if loc else '') + '. Curated picks for concertgoers and sports fans, not tourists.')
    head = re.sub(r'<title>[^<]*</title>', f'<title>{title}</title>', head, count=1)
    head = re.sub(r'(<meta name="description" content=")[^"]*(")', r'\g<1>' + desc + r'\g<2>', head, count=1)
    head = re.sub(r'(<link rel="canonical" href=")[^"]*(")', r'\g<1>' + url + r'\g<2>', head, count=1)
    head = re.sub(r'(<meta property="og:url" content=")[^"]*(")', r'\g<1>' + url + r'\g<2>', head, count=1)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*(")', r'\g<1>' + esc(f'{vname} City Guide') + r'\g<2>', head, count=1)
    head = re.sub(r'(<meta property="og:description" content=")[^"]*(")', r'\g<1>' + desc + r'\g<2>', head, count=1)
    head = re.sub(r'<script type="application/ld\+json">\s*\{.*?\}\s*</script>',
                  '<script type="application/ld+json">\n' + schema + '\n  </script>', head, count=1, flags=re.S)

    count_line = f'{len(all_items)} curated spots' + (f' in {city}' if city else '')
    main = (f'<main id="main-content">\n'
            f'{GUIDE_CSS}\n'
            f'    <div class="venue-hero">\n'
            f'      <p class="breadcrumb"><a href="../index.html">Home</a> &rsaquo; <a href="../cityguides.html">City Guides</a> &rsaquo; {esc(vname)}</p>\n'
            f'      <span class="eyebrow">City Guide</span>\n'
            f'      <h1 class="venue-name">{esc(vname)} City Guide</h1>\n'
            f'    </div>\n{hero_html}'
            + guide_section('Top Picks', count_line, cards_tp)
            + guide_section('Best Eats', 'More Great Spots Nearby', cards_be) +
            '    <div class="app-cta">\n'
            '      <div class="app-cta-copy">\n'
            f'        <h3>Heading to {esc(vname)}?</h3>\n'
            '        <p>Get the full venue guide in the Concerto app: bag policy, parking, rideshare zones, and your event-night itinerary.</p>\n'
            '      </div>\n'
            f'      <a href="/venues/{gslug}" class="btn btn-gold" style="margin-right:10px;">Venue Guide</a>'
            '<a href="https://apps.apple.com/us/app/concerto-show-go/id6744903414" target="_blank" rel="noopener noreferrer" class="btn btn-dark">Download Free on iOS</a>\n'
            '    </div>\n'
            '  </main>')
    write(f'cityguide/{gslug}.html', head + main + tail)
    built_guides.append(gslug)
print('static city guides built:', built_guides)

# link venue pages to their static guide (already linked via /cityguide/slug, which now serves the static file)

# ---------- sitemap: add guide urls ----------
sm = read('sitemap.xml')
added = 0
for gslug in built_guides:
    loc = f'https://concertocity.com/cityguide/{gslug}'
    if loc + '<' not in sm and loc + '</loc>' not in sm:
        entry = (f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>2026-07-18</lastmod>\n'
                 '    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n')
        sm = sm.replace('</urlset>', entry + '</urlset>')
        added += 1
write('sitemap.xml', sm)
print('sitemap entries added:', added)

# ---------- cityguide index og:url fix ----------
cgi = read('cityguide/index.html')
fixed = cgi.replace('content="https://concertocity.com/cityguide/index.html"', 'content="https://concertocity.com/cityguide/"')
if fixed != cgi:
    write('cityguide/index.html', fixed)
    print('cityguide og:url fixed')

# ================= STAGE 3: JS crash fixes =================
# 1) Dead features-panel wiring crashes script block 1, killing the events
#    loader downstream (infinite spinner). Guard it.
# 2) auth.js needs the supabase CDN lib; many pages load auth.js without it.
SUPA_CDN = '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>'
FEAT_CONST = "const featuresBtn=document.getElementById('featuresBtn'),featuresPanel=document.getElementById('featuresPanel');"

def fix_js_crashes(src):
    changed = False
    # guard the features wiring (line-wise wrap of consecutive features statements)
    if FEAT_CONST in src and 'if(featuresBtn&&featuresPanel){' not in src:
        lines = src.split('\n')
        out, i = [], 0
        while i < len(lines):
            out.append(lines[i])
            if FEAT_CONST in lines[i] and 'if(featuresBtn&&featuresPanel){' not in lines[i]:
                block = []
                j = i + 1
                while j < len(lines) and ('featuresBtn' in lines[j] or 'featuresPanel' in lines[j]):
                    block.append(lines[j]); j += 1
                if block:
                    out.append('    if(featuresBtn&&featuresPanel){')
                    out += block
                    out.append('    }')
                    i = j - 1
                    changed = True
            i += 1
        src = '\n'.join(out)
    # guard the bgCanvas mousemove handler
    old_bg = "document.addEventListener('mousemove',e=>{if(!ticking){requestAnimationFrame(()=>{bgCanvas.style.transform"
    if old_bg in src and 'if(bgCanvas)document' not in src:
        src = src.replace(old_bg, "if(bgCanvas)" + old_bg, 1)
        changed = True
    # supabase CDN before auth.js where missing
    if 'auth.js"' in src and 'supabase-js' not in src:
        src = re.sub(r'(<script src="(?:\.\./)?auth\.js">)', SUPA_CDN + r'\n\1', src, count=1)
        changed = True
    return src, changed

fixed = []
for d in ['venues', 'tours', 'cityguide', '.']:
    for fn in sorted(os.listdir(rp(d))):
        if not fn.endswith('.html'): continue
        p = os.path.join(d, fn) if d != '.' else fn
        src = read(p)
        new, ch = fix_js_crashes(src)
        if ch:
            write(p, new); fixed.append(p)
print('js crash fixes applied to', len(fixed), 'pages')

# ================= STAGE 4: one-off repairs (kept in the pipeline) =================
# hub pages: link canonical venue URLs, not .html variants
for f in ['parking.html', 'concessions.html', 'rideshare.html']:
    s = read(f)
    n = re.sub(r'(/venues/[a-z0-9-]+)\.html(#[a-z]*)?"', r'\1\2"', s)
    if n != s: write(f, n); print(f, 'hub links canonicalized')

# bagcheck/mobile-bags: strip the concatenated junk fragment, keep auth scripts
for f in ['bagcheck.html', 'mobile-bags.html', 'mobile-bagcheck.html']:
    if not os.path.exists(rp(f)): continue
    s = read(f)
    if '</htmlconst' in s:
        d1 = s[:s.index('</htmlconst')].rstrip()
        d1 = d1[:d1.rindex('</body>')]
        write(f, d1 + '<script src="auth.js"></script>\n<script src="app-shell.js"></script>\n</body>\n</html>\n')
        print(f, 'junk fragment removed')

# sitemap: every page changes when this pipeline runs, stamp today
import datetime
today = datetime.date.today().isoformat()
sm2 = re.sub(r'<lastmod>[0-9-]+</lastmod>', f'<lastmod>{today}</lastmod>', read('sitemap.xml'))
write('sitemap.xml', sm2)
print('sitemap lastmod ->', today)

# ================= STAGE 5: cvi container alignment =================
# Match baked venue-info sections to the audited module standard
# (desktop: 4% gutters, 1280px cap, 2.5rem padding, card chrome;
#  mobile <=768px: 5% gutters, 1.75rem padding).
ALIGN_CSS = '''
/* ---- container alignment (generated by build_static.py) ---- */
.cvi-feature{background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius-lg,24px);box-shadow:var(--shadow-sm);margin:0 4% 1.5rem;max-width:calc(1280px - 8%);padding:2.5rem;}
@media(max-width:768px){.cvi-feature{margin:0 5% 1.2rem;padding:1.75rem;}}
'''
vcss2 = read('venue-info/venue-info.css')
if 'container alignment (generated' not in vcss2:
    write('venue-info/venue-info.css', vcss2 + ALIGN_CSS)
    print('cvi alignment css appended')

# ================= STAGE 6: social previews + headers =================
# og:image / twitter:card on every indexable page missing them
OG_IMG = '''  <meta property="og:image" content="https://concertocity.com/ConcertoSocialPreview.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="https://concertocity.com/ConcertoSocialPreview.png">
'''
og_added = 0
for d in ['venues', 'tours', '.']:
    for fn in sorted(os.listdir(rp(d))):
        if not fn.endswith('.html') or fn.startswith('mobile'): continue
        p = os.path.join(d, fn) if d != '.' else fn
        s = read(p)
        if 'og:image' in s or 'og:title' not in s or 'noindex' in s[:3000]: continue
        s2 = re.sub(r'(<meta property="og:description"[^>]*>\n?)', r'\1' + OG_IMG, s, count=1)
        if s2 != s: write(p, s2); og_added += 1
print('og:image added to', og_added, 'pages')

# Netlify _headers: security + asset caching (HTML stays on Netlify defaults)
if not os.path.exists(rp('_headers')):
    write('_headers', '''/*
  X-Frame-Options: SAMEORIGIN
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

/img/*
  Cache-Control: public, max-age=31536000, immutable

/logo.png
  Cache-Control: public, max-age=604800

/venue-info/*
  Cache-Control: public, max-age=3600
''')
    print('_headers written')

# ================= STAGE 7: join the alignment contract + fix bags hub =================
# cvi-feature and nearby-section join align.css section 13 (centring contract)
ALIGN_ADDENDUM = '''
/* ---- 13b. Baked venue-info + nearby modules join the centring
   contract above (generated by build_static.py). Same reasoning as
   section 13: width token already correct, only centring needed. */
body.page-venue .cvi-feature,
body.page-venue .nearby-section {
  margin-left: auto;
  margin-right: auto;
}
body.page-venue .cvi-feature { scroll-margin-top: calc(var(--nav-total) + 16px); }
@media (max-width: 768px) {
  body.page-venue .cvi-feature,
  body.page-venue .nearby-section {
    margin-left: var(--gutter-m);
    margin-right: var(--gutter-m);
  }
}
'''
ac = read('align.css')
if '13b. Baked venue-info' not in ac:
    write('align.css', ac + ALIGN_ADDENDUM)
    print('align.css addendum appended')

# bags.html (+ mobile-bags.html): venue links -> on-site venue pages at #bag,
# replacing the retired concerto-bag-policies netlify site
slug_by_norm = {norm(v['id']): v['id'] for v in venues}
def fix_bag_links(src):
    unmatched = []
    def sub(m):
        squashed = m.group(1)
        slug = slug_by_norm.get(norm(squashed))
        if slug: return f'/venues/{slug}#bag'
        unmatched.append(squashed); return m.group(0)
    out = re.sub(r'https://concerto-bag-policies\.netlify\.app/([a-z0-9-]*)', sub, src)
    return out, unmatched
for f in ['bags.html', 'mobile-bags.html']:
    if not os.path.exists(rp(f)): continue
    s = read(f)
    if 'concerto-bag-policies' not in s: continue
    out, un = fix_bag_links(s)
    write(f, out)
    print(f, 'bag links -> on-site,', len(un), 'unmatched', (un[:5] if un else ''))

# ================= STAGE 8: homepage top picks cards =================
# Photos on the cards, 6 picks in a 3-col grid, hover affordance.
idx = read('index.html')
changed8 = False
OLD_TPL = """      return '<a class="pick-card" href="'+MAP_BASE+esc(v.slug||'')+'" rel="noopener noreferrer">'
        +'<div class="pick-card-name">'+esc(it.name)+'</div>'
        +'<div class="pick-card-venue">'+esc(v.venueName)+' &middot; '+esc(v.city)+'</div>'
      +'</a>';"""
NEW_TPL = """      var ph=it.photo?'<img class="pick-card-img" src="/'+esc(String(it.photo).replace(/^\\//,''))+'" alt="'+esc(it.name)+'" loading="lazy" decoding="async" onerror="this.remove()">':'';
      return '<a class="pick-card" href="'+MAP_BASE+esc(v.slug||'')+'" rel="noopener noreferrer">'+ph
        +'<div class="pick-card-body">'
        +'<div class="pick-card-name">'+esc(it.name)+'</div>'
        +'<div class="pick-card-venue">'+esc(v.venueName)+' &middot; '+esc(v.city)+'</div>'
        +'</div>'
      +'</a>';"""
if OLD_TPL in idx:
    idx = idx.replace(OLD_TPL, NEW_TPL, 1)
    idx = idx.replace("var cards=data.map(function(v){", "var cards=data.slice(0,6).map(function(v){", 1)
    changed8 = True
PICKS_CSS = """
/* ---- top picks photo cards (generated by build_static.py) ---- */
.picks-grid{grid-template-columns:repeat(3,1fr);}
.pick-card{padding:0;overflow:hidden;display:flex;flex-direction:column;transition:transform .3s cubic-bezier(0.16,1,0.3,1),box-shadow .3s cubic-bezier(0.16,1,0.3,1);}
.pick-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-md);}
.pick-card-img{width:100%;height:170px;object-fit:cover;display:block;}
.pick-card-body{padding:1.2rem 1.4rem 1.4rem;display:flex;flex-direction:column;gap:6px;}
@media(max-width:768px){.picks-grid{grid-template-columns:1fr 1fr;}.pick-card-img{height:130px;}}
@media(max-width:520px){.picks-grid{grid-template-columns:1fr;}}
"""
if 'top picks photo cards (generated' not in idx and changed8:
    idx = idx.replace('</head>', '<style>' + PICKS_CSS + '</style>\n</head>', 1)
if changed8:
    write('index.html', idx)
    print('homepage top picks cards upgraded')

# ================= STAGE 8b: top picks photo hygiene + photo-first homepage =================
# Drop photo refs pointing at files that don't exist (they 404 in the SPA too),
# and have the homepage prefer picks that have photos.
tp_raw2 = read('data/top_picks.json')
tp_data = json.loads(tp_raw2)
dropped = 0
for v in tp_data:
    for it in v.get('items', []):
        p = (it.get('photo') or '').lstrip('/')
        if p and not os.path.exists(rp(p)):
            it['photo'] = None; dropped += 1
if dropped:
    write('data/top_picks.json', json.dumps(tp_data, indent=2, ensure_ascii=False))
    print('dead photo refs dropped:', dropped)

idx2 = read('index.html')
if 'data.slice(0,6).map' in idx2 and 'photo?0:1' not in idx2:
    idx2 = idx2.replace(
        "var cards=data.slice(0,6).map(function(v){",
        "data=data.slice().sort(function(a,b){var pa=((a.items||[])[0]||{}).photo?0:1,pb=((b.items||[])[0]||{}).photo?0:1;return pa-pb;});\n    var cards=data.slice(0,6).map(function(v){", 1)
    write('index.html', idx2)
    print('homepage picks: photo-first ordering')

# ================= STAGE 9: hero venue/tour search + trust numbers =================
idx9 = read('index.html')

# See all Top Picks button: point at top-picks.html, not partners.html
idx9 = idx9.replace('<a href="partners.html" class="btn btn-outline">See all Top Picks</a>',
                    '<a href="top-picks.html" class="btn btn-outline">See all Top Picks</a>', 1)

# numbers: 300+ -> 340+ (hero trust line + stats band + meta description)
if 'data-count="300"' in idx9:
    idx9 = idx9.replace('data-count="300"', 'data-count="340"')
    idx9 = idx9.replace('<span>300+ venues</span>', '<span>340+ venues</span>')
    idx9 = idx9.replace('for 300+ venues', 'for 340+ venues')
    print('trust numbers bumped to 340+')

SEARCH_HTML = '''
    <div class="hero-search" id="heroSearch">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="heroSearchInput" type="text" placeholder="Search venues and tours" autocomplete="off" spellcheck="false" aria-label="Search venues and tours" role="combobox" aria-expanded="false" aria-controls="heroSearchResults">
      <div class="hero-search-results" id="heroSearchResults" role="listbox" hidden></div>
    </div>
'''
SEARCH_CSS = '''
/* ---- hero search (generated by build_static.py) ---- */
.hero-search{position:relative;width:min(52vw,700px);margin:2.4rem auto 0;display:flex;align-items:center;}
.hero-search svg{position:absolute;left:1.45rem;width:18px;height:18px;color:var(--text-xdim);pointer-events:none;}
.hero-search input{width:100%;font-family:var(--body);font-size:0.92rem;color:var(--text);background:var(--card-bg);border:1px solid var(--border);border-radius:99px;padding:1.35rem 1.7rem 1.35rem 3.3rem;box-shadow:var(--shadow-md);outline:none;transition:border-color .2s,box-shadow .2s,transform .2s;}
.hero-search input:focus{border-color:var(--gold);box-shadow:0 12px 32px rgba(18,30,54,.12);}
.hero-search input::placeholder{color:var(--text-xdim);}
.hero-search-results{position:absolute;top:calc(100% + 10px);left:0;right:0;background:var(--card-bg);border:1px solid var(--border);border-radius:20px;box-shadow:0 16px 40px rgba(18,30,54,.14);overflow:hidden;z-index:60;text-align:left;}
.hero-search-results a{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:0.85rem 1.35rem;text-decoration:none;color:var(--text);font-family:var(--body);font-size:0.92rem;border-bottom:1px solid var(--border);}
.hero-search-results a:last-child{border-bottom:none;}
.hero-search-results a:hover,.hero-search-results a.active{background:var(--bg);}
.hero-search-results .hs-type{font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--gold);flex-shrink:0;}
.hero-search-results .hs-sub{color:var(--text-xdim);font-size:0.78rem;}
.hero-search ~ .hero-actions{margin-top:1.4rem;}
@media(max-width:700px){.hero-search{width:100%;}}
@media(max-width:600px){.hero-search{margin-top:1.8rem;}.hero-search input{font-size:0.88rem;padding:1.1rem 1.3rem 1.1rem 2.9rem;}}
'''
SEARCH_JS = '''
<script>
(function(){
  var inp=document.getElementById('heroSearchInput'), box=document.getElementById('heroSearchResults');
  if(!inp||!box) return;
  var IDX=null, sel=-1;
  function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  function load(){ if(IDX) return Promise.resolve(IDX);
    return fetch('/search-index.json').then(function(r){return r.json();}).then(function(d){IDX=d;return d;}).catch(function(){return {venues:[],tours:[]};}); }
  function scoreOf(hay,q){ hay=hay.toLowerCase();
    if(hay.indexOf(q)===-1) return -1;
    if(hay.indexOf(q)===0) return 0;                      // starts with query
    if(hay.indexOf(' '+q)>-1) return 1;                   // word boundary
    return 2; }                                           // substring
  function match(q){ q=q.toLowerCase();
    var out=[];
    (IDX.tours||[]).forEach(function(t){
      var sA=scoreOf(t.artist||'',q), sN=scoreOf(t.name||'',q);
      var s=Math.min(sA===-1?9:sA, sN===-1?9:sN);
      if(s<9) out.push({s:s, name:t.artist?t.artist:t.name, sub:t.artist?t.name:'', href:'/tours/'+t.slug, type:'Tour'});
    });
    (IDX.venues||[]).forEach(function(v){
      var s=scoreOf(v.name,q);
      if(s>-1) out.push({s:s+0.5, name:v.name, sub:v.type||'', href:'/venues/'+v.slug, type:'Venue'});
    });
    out.sort(function(a,b){return a.s-b.s;});
    return out.slice(0,8); }
  function render(items){ sel=-1;
    if(!items.length){ box.hidden=true; inp.setAttribute('aria-expanded','false'); return; }
    box.innerHTML=items.map(function(it){
      return '<a href="'+esc(it.href)+'"><span>'+esc(it.name)+(it.sub?' <span class="hs-sub">'+esc(it.sub)+'</span>':'')+'</span><span class="hs-type">'+it.type+'</span></a>';
    }).join('');
    box.hidden=false; inp.setAttribute('aria-expanded','true'); }
  var POP=['madison-square-garden','sofi-stadium','sphere','cryptocom-arena','td-garden','moody-center'];
  function defaults(){ var by={}; (IDX&&IDX.venues||[]).forEach(function(v){by[v.slug]=v;});
    var rows=POP.map(function(sl){return by[sl];}).filter(Boolean).map(function(v){return {name:v.name, sub:v.type||'', href:'/venues/'+v.slug, type:'Venue'};});
    rows.push({name:'Browse all venues', sub:'', href:'/venues.html', type:'340+'});
    rows.push({name:'Browse all tours', sub:'', href:'/tours.html', type:'75+'});
    return rows; }
  inp.addEventListener('focus',function(){ load().then(function(){ if(inp.value.trim().length<2) render(defaults()); }); });
  inp.addEventListener('input',function(){ var q=inp.value.trim();
    if(q.length<2){ load().then(function(){ render(defaults()); }); return; }
    load().then(function(){ render(match(q)); }); });
  inp.addEventListener('keydown',function(e){
    var links=box.querySelectorAll('a'); if(box.hidden||!links.length){ return; }
    if(e.key==='ArrowDown'){ e.preventDefault(); sel=Math.min(sel+1,links.length-1); }
    else if(e.key==='ArrowUp'){ e.preventDefault(); sel=Math.max(sel-1,0); }
    else if(e.key==='Enter'){ if(sel>-1){ e.preventDefault(); links[sel].click(); } else if(links.length){ e.preventDefault(); links[0].click(); } return; }
    else if(e.key==='Escape'){ box.hidden=true; return; }
    else { return; }
    for(var i=0;i<links.length;i++){ links[i].classList.toggle('active', i===sel); } });
  box.addEventListener('click',function(e){ var a=e.target.closest('a'); if(a && window.gtag){ try{ gtag('event','search',{search_term:inp.value.trim()}); }catch(err){} } });
  document.addEventListener('click',function(e){ if(!e.target.closest('#heroSearch')) box.hidden=true; });
})();
</script>
'''
if 'hero-search' not in idx9:
    idx9 = idx9.replace('    <div class="hero-actions">', SEARCH_HTML + '    <div class="hero-actions">', 1)
    idx9 = idx9.replace('</head>', '<style>' + SEARCH_CSS + '</style>\n</head>', 1)
    idx9 = idx9.replace('</body>', SEARCH_JS + '</body>', 1)
    idx9 = idx9.replace('      <a href="venues.html" class="btn btn-outline">Find Your Venue</a>\n', '')
    print('hero search installed')
write('index.html', idx9)

# ================= STAGE 10: premium feature visual harmonization =================
# Brand-tune the premium pages' rogue colors (see mapping) and canonicalize
# mobile-bags.html -> mobile-bagcheck.html with redirects for shipped app builds.
PREMIUM_PAGES = ['concertoplus.html','mobile-concertoplus.html','bagcheck.html',
                 'livemode.html','mobile-livemode.html','mobile-bags.html','mobile-bagcheck.html']
COLOR_MAP = [
    # camera backdrop: cold blue-blacks -> brand-navy family (preserves gradient flow)
    ('#0c1820', '#0f1930'), ('#0C1820', '#0F1930'),
    ('#0e1d2e', '#121e36'), ('#0E1D2E', '#121E36'),
    ('#09131f', '#0b1322'), ('#09131F', '#0B1322'),
    # story card + overlay navy -> true brand navy
    ('#0E1A2B', '#121E36'), ('#0e1a2b', '#121e36'),
    # ad-hoc hover navy -> brand-hue lightened navy
    ('#1a2d47', '#1b2b4e'), ('#1A2D47', '#1B2B4E'),
    # verdict/status trio: stock flat-UI -> brand-tuned (pass uses site's existing green)
    ('#27AE60', '#128269'), ('#27ae60', '#128269'), ('rgba(39,174,96', 'rgba(18,130,105'),
    ('#D4820A', '#C07E1F'), ('#d4820a', '#c07e1f'), ('rgba(212,130,10', 'rgba(192,126,31'),
    ('#C0392B', '#B3402E'), ('#c0392b', '#b3402e'), ('rgba(192,57,43', 'rgba(179,64,46'),
    # placeholder tile gradients: stock -> brand family
    ('linear-gradient(135deg,#667eea,#764ba2)', 'linear-gradient(135deg,#121E36,#1B2B4E)'),
    ('linear-gradient(135deg,#f093fb,#f5576c)', 'linear-gradient(135deg,#C9A84C,#E5C365)'),
]
for p in PREMIUM_PAGES:
    if not os.path.exists(rp(p)): continue
    s = read(p); orig = s
    for old, new in COLOR_MAP:
        s = s.replace(old, new)
    if s != orig:
        write(p, s); print(p, 'colors harmonized')

# canonical rename: mobile-bags.html -> mobile-bagcheck.html
if os.path.exists(rp('mobile-bags.html')) and not os.path.exists(rp('mobile-bagcheck.html')):
    os.rename(rp('mobile-bags.html'), rp('mobile-bagcheck.html'))
    print('mobile-bags.html renamed to mobile-bagcheck.html')
for p in ['mobile.html', 'mobile-premium.html', 'mobile-bagcheck.html']:
    if not os.path.exists(rp(p)): continue
    s = read(p)
    n = s.replace('mobile-bags.html', 'mobile-bagcheck.html')
    if n != s: write(p, n); print(p, 'references updated')
_rd = read('_redirects')
if 'mobile-bagcheck' not in _rd:
    write('_redirects', '/mobile-bags.html  /mobile-bagcheck.html  301\n/mobile-bags  /mobile-bagcheck  301\n' + _rd)
    print('redirects added for old mobile-bags path')

# ================= STAGE 11: premium app screens join the hero ceremony =================
# Home/venues heroes are centered ceremony; premium app screens were left-cornered
# with edge-to-edge controls. Center the hero text and constrain every control to a
# centered column, matching the site's compositional language.
APP_COMPOSITION = '''
/* ---- 14. Premium app screens: hero ceremony + contained controls
   (generated by build_static.py). Home and venues pages set the
   compositional language: centered eyebrow / headline / sub, controls
   in a contained centered column. The premium app screens (Concerto+,
   Live Mode, Bag Check) join that contract here. Camera and live-show
   UI (cam-*, show-*, tab-*) intentionally untouched. */
body.page-app .app-eyebrow {
  display: block;
  text-align: center;
}
body.page-app .app-headline {
  text-align: center;
  max-width: var(--measure);
  margin-left: auto;
  margin-right: auto;
}
body.page-app .app-sub {
  text-align: center;
  max-width: 720px;
  margin-left: auto;
  margin-right: auto;
}
body.page-app .search-wrap,
body.page-app .dropdown-wrap,
body.page-app .primary-btn,
body.page-app .action-btn,
body.page-app .divider,
body.page-app .status-line {
  max-width: 720px;
  margin-left: auto;
  margin-right: auto;
}
body.page-app .field-label,
body.page-app .recent-label {
  display: block;
  max-width: 720px;
  margin-left: auto;
  margin-right: auto;
}
body.page-app .explainer-row {
  max-width: calc(1280px - 8%);
  margin-left: auto;
  margin-right: auto;
}
'''
ac11 = read('align.css')
if '14. Premium app screens' not in ac11:
    write('align.css', ac11 + APP_COMPOSITION)
    print('align.css: premium composition contract appended')

# ================= STAGE 12: single shared Supabase client =================
# The premium pages each created a rival GoTrueClient alongside auth.js's,
# racing on the same storage key (the "Multiple GoTrueClient instances"
# console warning, and prime suspect for silent 401s on paid features).
# Every page now registers/reuses one shared client via window._supabaseClient,
# the same pattern auth.js already implements.
OLD_CLIENT = 'try { sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY); } catch(e) { sb = null; }'
NEW_CLIENT = ("try { sb = window._supabaseClient || (window._supabaseClient = "
              "supabase.createClient(SUPABASE_URL, SUPABASE_KEY)); } catch(e) { sb = null; }")
shared = 0
for p in PREMIUM_PAGES:
    if not os.path.exists(rp(p)): continue
    s = read(p)
    if OLD_CLIENT in s:
        write(p, s.replace(OLD_CLIENT, NEW_CLIENT))
        shared += 1
print('shared supabase client on', shared, 'pages')

# ================= STAGE 13: account page repair =================
# account.html wired a signOutBtn that no longer existed (crash killed init(),
# blank page) and loaded auth.js twice (const redeclaration SyntaxError).
acct = read('account.html')
ch13 = False
if 'id="signOutBtn"' not in acct and 'id="resetPwBtn"' in acct:
    acct = re.sub(
        r'(<div class="settings-row">\s*<span class="settings-label">Password</span>\s*<button class="settings-edit" id="resetPwBtn">[^<]*</button>\s*</div>)',
        r'''\1
          <div class="settings-row">
            <span class="settings-label">Session</span>
            <button class="settings-edit" id="signOutBtn">Sign Out</button>
          </div>''', acct, count=1)
    ch13 = 'id="signOutBtn"' in acct
# drop the duplicate trailing auth.js include (keep the one before the inline app script)
if acct.count('<script src="auth.js"></script>') > 1:
    i = acct.rfind('<script src="auth.js"></script>')
    acct = acct[:i] + acct[i:].replace('<script src="auth.js"></script>', '', 1)
    ch13 = True
if ch13:
    write('account.html', acct)
    print('account.html repaired (sign-out row + duplicate auth.js removed)')

# ================= STAGE 14: one account control per viewport =================
# Nav has two account controls: navAuthLink (Sign In -> gold circle via auth.js,
# desktop) and the static .nav-profile-btn (mobile entry point). Index encodes
# the intent (icon hidden >1366px); later page-level "!important inline-flex"
# fixes and missing rules broke it unevenly. Normalize sitewide via align.css.
NAV_ICON_CSS = '''
/* ---- 15. One account control per viewport (generated by build_static.py)
   Desktop (>1366px): #navAuthLink pill (auth.js swaps it to the gold profile
   circle when signed in). Small screens (<=1366px): the static profile icon.
   Overrides stray page-level "display:inline-flex !important" rules. */
.nav-profile-btn { display: none !important; }
@media (max-width: 1366px) {
  .nav-profile-btn { display: inline-flex !important; }
}
'''
ac14 = read('align.css')
if '15. One account control' not in ac14:
    write('align.css', ac14 + NAV_ICON_CSS)
    print('align.css: nav icon contract appended')

# account.html: restore the button styles its markup expects
BTN_CSS = '''<style>
/* button styles (restored by build_static.py; canonical defs from index.html) */
.btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.72rem 1.6rem; border-radius: 99px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; transition: transform 0.2s, box-shadow 0.2s, background 0.2s; text-decoration: none; cursor: pointer; border: none; }
.btn-dark { background: var(--text); color: var(--bg); box-shadow: 0 8px 24px rgba(18,30,54,0.18); }
.btn-dark:hover { transform: translateY(-2px); box-shadow: 0 14px 32px rgba(18,30,54,0.24); }
</style>
'''
acct14 = read('account.html')
if 'canonical defs from index.html' not in acct14 and '.btn-dark {' not in acct14:
    acct14 = acct14.replace('</head>', BTN_CSS + '</head>', 1)
    write('account.html', acct14)
    print('account.html: button styles restored')

# ================= STAGE 15: premium app screens, reference type + button flow =================
# Finish matching the app screens to the site's reference (bags.html):
# hero type at reference scale, gold eyebrows, reference sub measure, and
# action buttons forced to block flow (the 720px cap inside a flex parent
# was letting two buttons wrap side by side).
APP_FINISH = '''
/* ---- 14b. Premium app screens: reference type scale + button flow
   (generated by build_static.py). Values mirror bags.html, the site's
   alignment reference: h1 clamp(2.4rem,5vw,4rem), gold .28em eyebrow,
   1.05rem/300 sub at 600px measure. display:block stops the 720px-capped
   buttons from wrapping two-up inside their flex parent. */
body.page-app .app-headline {
  font-size: clamp(2.4rem, 5vw, 4rem);
  letter-spacing: -0.025em;
}
body.page-app .app-eyebrow {
  color: var(--gold);
  letter-spacing: 0.28em;
  margin-bottom: 1.1rem;
}
body.page-app .app-sub {
  font-size: 1.05rem;
  font-weight: 300;
  line-height: 1.75;
  max-width: 600px;
}
body.page-app .primary-btn,
body.page-app .action-btn {
  display: block;
}
body.page-app .action-btn { margin-top: 0.65rem; }
body.page-app .field-label { margin-top: 1.5rem; }
@media (max-width: 600px) {
  body.page-app .app-headline { font-size: clamp(2rem, 8vw, 2.6rem); }
}
'''
ac15 = read('align.css')
if '14b. Premium app screens' not in ac15:
    write('align.css', ac15 + APP_FINISH)
    print('align.css: reference type + button flow appended')

# ================= STAGE 16: app shell (mobile-*) spacing + alignment =================
# The mobile shells inherited two desktop assumptions:
# 1) align.css section 1's unscoped .page-hero adds 128px of fixed-nav
#    clearance, but the app header is in-flow, producing a dead zone.
# 2) stats strips / filter rows use desktop flex values that wrap ragged-left
#    on phone widths. mobile.html (the reference) avoids both by construction.
SHELL_CSS = '''
/* ---- 16. App shell corrections (generated by build_static.py)
   Scoped to body.page-app + phone widths. The .page-hero fixed-nav
   clearance from section 1 assumed the website's fixed nav; the app
   header is in-flow, so restore mobile.html's tight rhythm. Stats and
   filter rows center instead of desktop ragged-left wrapping. */
body.page-app .page-hero { padding-top: 28px; }
@media (max-width: 600px) {
  body.page-app .stats-strip {
    justify-content: center;
    text-align: center;
    column-gap: 2.25rem;
    row-gap: 1.5rem;
    padding-bottom: 2.25rem;
  }
  body.page-app .stats-strip .stat { align-items: center; }
  body.page-app .view-toggle { margin-left: auto !important; margin-right: auto !important; }
  body.page-app .filter-bar { justify-content: center; }
}
'''
ac16 = read('align.css')
if '16. App shell corrections' not in ac16:
    write('align.css', ac16 + SHELL_CSS)
    print('align.css: app shell corrections appended')

# ================= STAGE 16: mobile app-shell top spacing + chip rows =================
# mobile.html (the reference) starts its hero at 26px. The other mobile shells
# inherited desktop hero padding: calc(nav-h + 48-60px) ~= 116-128px, the big
# dead gap at the top of Venues/Tours/Near Me. Normalize the app shells to the
# reference rhythm and tidy the horizontally-scrolling chip/toggle rows.
MOBILE_FIX = '''
/* ---- 16. Mobile app-shell top spacing + control rows
   (generated by build_static.py). Matches mobile.html's 26px hero start;
   the standalone mobile-*.html shells had inherited ~128px desktop padding. */
body.page-app .page-hero {
  padding-top: 28px;
}
@media (max-width: 600px) {
  body.page-app .page-hero { padding: 24px 5% 20px; }
  body.page-app .stats-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem 2rem;
    justify-content: center;
  }
  body.page-app .filter-bar {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding-bottom: 4px;
    justify-content: flex-start;
  }
  body.page-app .filter-bar::-webkit-scrollbar { display: none; }
  body.page-app .view-toggle { margin-left: auto; margin-right: auto; }
}
'''
ac16 = read('align.css')
if '16. Mobile app-shell' not in ac16:
    write('align.css', ac16 + MOBILE_FIX)
    print('align.css: mobile app-shell spacing appended')

# ================= STAGE 17: link hygiene guard =================
# Catch leaked internal/staging hosts in official links before they ship
# (MSG's bag link once pointed at production1.msg.com, an internal host).
import re as _re17
_bad_host = _re17.compile(r'production\d|staging\.|\.internal|localhost|preview\.')
_leaks = []
for _f in ['bag_policies.json', 'parking.json', 'concessions.json']:
    _d = json.load(open(rp('data', _f)))
    for _k, _v in _d.items():
        for _field, _val in (_v.items() if isinstance(_v, dict) else []):
            if isinstance(_val, str) and _bad_host.search(_val):
                _leaks.append(f'{_f}:{_k}:{_field} -> {_val}')
if _leaks:
    print('WARNING leaked internal hosts in links:')
    for _l in _leaks: print('  ', _l)
else:
    print('link hygiene: no leaked internal hosts')

# ================= STAGE 18: "Near the Venue" tabs w/ filters (replaces City Guide card) =================
import json as _j18, html as _h18
_NB = _j18.load(open(rp('data/nearby.json'))) if os.path.exists(rp('data/nearby.json')) else {}

# Map raw Google types -> friendly filter labels, per tab. Only filters that
# actually match items on a given venue are shown (built from that venue's data).
_FILTERS = {
    'restaurants': [('bar','Bars'),('cafe','Cafés'),('bakery','Bakeries'),
                    ('meal_takeaway','Takeout'),('night_club','Nightlife')],
    'hotels': [('spa','With spa'),('casino','Casino'),('gym','With gym')],
    'more': [('museum','Museums'),('park','Parks'),('art_gallery','Galleries'),
             ('place_of_worship','Landmarks'),('stadium','Stadiums'),('aquarium','Aquariums')],
}

def _price18(p): return '$'*p if isinstance(p,int) and p>0 else ''
def _stars18(it):
    if it.get('rating'):
        return f"&#9733; {it['rating']} ({(it.get('reviews') or 0):,})"
    return ''

def _card18(it, tab):
    name=_h18.escape(str(it.get('name') or ''))
    dist=f"{it['distance_mi']} mi" if it.get('distance_mi') is not None else ''
    meta='  &middot;  '.join(x for x in [dist,_stars18(it),_price18(it.get('price'))] if x)
    q=urllib.parse.quote(f"{it.get('name','')} {it.get('address','')}")
    types=' '.join(it.get('types') or [])
    if tab=='hotels':
        cta=(f'<a class="nv-cta" data-aff="hotel" data-lat="{it.get("lat","")}" '
             f'data-lng="{it.get("lng","")}" data-name="{name}" '
             f'href="https://www.google.com/maps/search/?api=1&amp;query={q}" '
             f'target="_blank" rel="noopener">Book &rarr;</a>')
    else:
        cta=(f'<a class="nv-cta nv-dir" href="https://www.google.com/maps/search/?api=1&amp;query={q}" '
             f'target="_blank" rel="noopener">Directions &rarr;</a>')
    return (f'<div class="nv-item" data-types="{_h18.escape(types)}"><div class="nv-item-main">'
            f'<div class="nv-item-name">{name}</div><div class="nv-item-meta">{meta}</div></div>{cta}</div>')

def _filters_for(tab, items):
    # only show a filter chip if >=2 items on THIS venue match it
    present=[]
    for gtype,label in _FILTERS.get(tab,[]):
        n=sum(1 for it in items if gtype in (it.get('types') or []))
        if n>=2: present.append((gtype,label))
    if not present: return ''
    chips=['<button class="nv-filter nv-fon" data-f="all">All</button>']
    for gtype,label in present:
        chips.append(f'<button class="nv-filter" data-f="{gtype}">{label}</button>')
    return '<div class="nv-filters">'+''.join(chips)+'</div>'

def _section18(slug, venue_name):
    tabs=_NB.get(slug,{}).get('tabs',{})
    order=[('restaurants','Restaurants'),('hotels','Hotels'),('more','More')]
    btns,panels=[],[]
    for i,(key,label) in enumerate(order):
        items=tabs.get(key,{}).get('items',[])
        if key=='restaurants':
            items=[it for it in items if 'lodging' not in (it.get('types') or [])]
        on=' nv-on' if i==0 else ''
        btns.append(f'<button class="nv-tab{on}" data-nv="{key}">{label} near {_h18.escape(venue_name)}</button>')
        if items:
            body=_filters_for(key,items)+''.join(_card18(it,key) for it in items)
        else:
            body=('<div class="nv-empty">This is a destination venue &mdash; plan to travel in. '
                  'Nothing notable within range.</div>')
        panels.append(f'<div class="nv-panel{on}" data-nv-panel="{key}">{body}</div>')
    return (
        '<section class="nv-section reveal" aria-label="Near the venue">'
        f'<div class="nv-head"><span class="tool-eyebrow">City Guide</span>'
        f'<h2 class="tool-section-title">Near {_h18.escape(venue_name)}</h2>'
        f'<p class="tool-section-desc">The best restaurants, hotels, and more near '
        f'{_h18.escape(venue_name)} &mdash; for concertgoers and sports fans, not tourists.</p></div>'
        f'<div class="nv-tabs">{"".join(btns)}</div>'
        f'<div class="nv-panels">{"".join(panels)}</div>'
        '<p class="nv-note">Distances from the venue &middot; ratings via Google &middot; '
        'Concerto may earn a commission on hotel bookings.</p>'
        '<script>(function(){var s=document.currentScript.closest(".nv-section");'
        'function filt(p){var f=p.dataset.f||"all";var pan=p.closest(".nv-panel");'
        'pan.querySelectorAll(".nv-filter").forEach(function(x){x.classList.toggle("nv-fon",x===p)});'
        'pan.querySelectorAll(".nv-item").forEach(function(it){'
        'it.style.display=(f==="all"||(it.dataset.types||"").indexOf(f)>-1)?"":"none"});}'
        's.querySelectorAll(".nv-tab").forEach(function(b){b.addEventListener("click",function(){'
        'var k=b.dataset.nv;s.querySelectorAll(".nv-tab").forEach(function(x){x.classList.toggle("nv-on",x===b)});'
        's.querySelectorAll(".nv-panel").forEach(function(p){p.classList.toggle("nv-on",p.dataset.nvPanel===k)});'
        '});});'
        's.querySelectorAll(".nv-filter").forEach(function(f){f.addEventListener("click",function(){filt(f)});});'
        '})();</script></section>'
    )

_nv=0
for _vf in glob.glob(rp('venues','*.html')):
    _fn=os.path.basename(_vf); _slug=_fn[:-5]
    _s=read(os.path.join('venues',_fn))
    # remove any prior nv-section (idempotent)
    _s=re.sub(r'<section class="nv-section reveal".*?</section>','',_s,flags=re.S)
    _vn=_NB.get(_slug,{}).get('venueName') or _slug.replace('-',' ').title()
    _sec=_section18(_slug,_vn)
    # REPLACE the City Guide tool-section card with our section (balanced div scan)
    _i=_s.find('<div class="tool-section reveal">')
    if _i>=0:
        _depth=0; _j=_i
        while _j<len(_s):
            if _s[_j:_j+4]=='<div': _depth+=1; _j+=4; continue
            if _s[_j:_j+6]=='</div>':
                _depth-=1; _j+=6
                if _depth==0: break
                continue
            _j+=1
        _s=_s[:_i]+_sec+_s[_j:]
        write(os.path.join('venues',_fn),_s); _nv+=1
    else:
        # fallback: insert before app-cta if no city guide card found
        if '<div class="app-cta">' in _s:
            _s=_s.replace('<div class="app-cta">',_sec+'\n      <div class="app-cta">',1)
            write(os.path.join('venues',_fn),_s); _nv+=1
print(f'near-venue tabs (w/ filters) placed in City Guide slot on {_nv} pages')

# ================= STAGE 19: near-venue styling (tabs + filters) =================
NV_CSS = '''
/* ---- 17. Near the Venue tabs + filters (generated by build_static.py) ---- */
.nv-section { max-width: 1280px; margin: 0 auto; padding: 0 4% 1rem; }
.nv-head { margin-bottom: 1.5rem; }
.nv-head .tool-section-title { margin: 0.3rem 0 0.5rem; }
.nv-tabs { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.25rem; }
.nv-tab { padding: 0.6rem 1.1rem; border-radius: 99px; border: 1px solid var(--border-mid);
  background: transparent; color: var(--text-dim); font-family: var(--body);
  font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.18s; white-space: nowrap; }
.nv-tab:hover { border-color: var(--text); color: var(--text); }
.nv-tab.nv-on { background: var(--text); color: var(--bg); border-color: var(--text); }
.nv-panel { display: none; }
.nv-panel.nv-on { display: block; }
.nv-filters { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 1rem; }
.nv-filter { padding: 0.35rem 0.85rem; border-radius: 99px; border: 1px solid var(--border-light, #e5e5e5);
  background: transparent; color: var(--text-dim); font-family: var(--body); font-size: 0.72rem;
  font-weight: 600; letter-spacing: 0.02em; cursor: pointer; transition: all 0.15s; }
.nv-filter:hover { border-color: var(--text-dim); color: var(--text); }
.nv-filter.nv-fon { background: var(--gold); color: #1a1a1a; border-color: var(--gold); }
.nv-item { display: flex; justify-content: space-between; align-items: center; gap: 1rem;
  padding: 1rem 1.25rem; background: var(--card-bg, #fff); border: 1px solid var(--border-light, #eee);
  border-radius: 14px; margin-bottom: 0.6rem; }
.nv-item-name { font-family: var(--body); font-size: 0.98rem; font-weight: 600; color: var(--text); }
.nv-item-meta { font-family: var(--body); font-size: 0.82rem; color: var(--text-dim); margin-top: 0.15rem; }
.nv-cta { font-family: var(--body); font-size: 0.8rem; font-weight: 700; letter-spacing: 0.04em;
  text-decoration: none; white-space: nowrap; color: var(--gold); }
.nv-cta.nv-dir { color: var(--text-dim); }
.nv-cta:hover { color: var(--text); }
.nv-empty { padding: 1.5rem 1.25rem; font-family: var(--body); font-size: 0.92rem;
  color: var(--text-dim); background: var(--card-bg, #fafafa); border: 1px dashed var(--border-mid);
  border-radius: 14px; line-height: 1.6; }
.nv-note { font-family: var(--body); font-size: 0.72rem; color: var(--text-dim); margin-top: 1rem; opacity: 0.8; }
@media (max-width: 600px) {
  .nv-tabs, .nv-filters { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; padding-bottom: 4px; }
  .nv-tabs::-webkit-scrollbar, .nv-filters::-webkit-scrollbar { display: none; }
  .nv-item { padding: 0.85rem 1rem; }
}
'''
_ac=read('align.css')
if '17. Near the Venue tabs + filters' not in _ac:
    write('align.css', _ac + NV_CSS)
    print('align.css: near-venue styling (w/ filters) appended')

# ================= STAGE 20: sticky jump-nav + module ordering =================
# Reorders the intact module blocks to match the nav (City Guide, Live, Know,
# Explore), adds id anchors, and injects a sticky scroll-spy nav. Reorder makes
# DOM order == nav order so scrolling and clicking agree. Non-destructive to
# block internals; validates div-balance before writing.
def _bal2(html, marker):
    i=html.find(marker)
    if i<0: return None
    o=html.rfind('<',0,i+1)
    t=re.match(r'<(\w+)',html[o:]).group(1)
    depth=0; j=o
    while j<len(html):
        if html[j:j+len(t)+1]=='<'+t: depth+=1; j+=len(t)+1; continue
        if html[j:j+len(t)+3]=='</'+t+'>':
            depth-=1; j+=len(t)+3
            if depth==0: return (o,j)
            continue
        j+=1
    return None

_jn=0; _jnskip=0
for _vf in glob.glob(rp('venues','*.html')):
    _fn=os.path.basename(_vf)
    _s=read(os.path.join('venues',_fn))
    # hard reset any prior jump-nav artifacts
    _s=re.sub(r'<nav class="vg-nav".*?</nav>','',_s,flags=re.S)
    _s=re.sub(r'\s+id="vg-(?:guide|live|know|explore)"','',_s)
    # extract the four modules in NAV order
    _order=[('vg-guide','City Guide','class="nv-section reveal"'),
            ('vg-live','Live at {vn}','class="events-section reveal"'),
            ('vg-know','Know Before You Go','class="venue-info-wrap'),
            ('vg-explore','Explore More','class="nearby-section reveal"')]
    _mods={}; _spans=[]; _okbal=True
    for aid,label,mk in _order:
        # take the FIRST occurrence only (dedupe safety)
        bnd=_bal2(_s,mk)
        if bnd:
            seg=_s[bnd[0]:bnd[1]]
            if seg.count('<div')!=seg.count('</div>'): _okbal=False; break
            _mods[aid]=(label,seg); _spans.append(bnd)
    # also strip any DUPLICATE nv-section beyond the first
    _all_nv=[m.start() for m in re.finditer(r'class="nv-section reveal"',_s)]
    if not _okbal or 'vg-guide' not in _mods or 'vg-know' not in _mods:
        _jnskip+=1; continue
    # remove all extracted spans (back to front)
    for bnd in sorted(_spans,reverse=True):
        _s=_s[:bnd[0]]+_s[bnd[1]:]
    # remove any leftover duplicate nv-section blocks
    while True:
        d=_bal2(_s,'class="nv-section reveal"')
        if not d: break
        _s=_s[:d[0]]+_s[d[1]:]
    # find insert point: right after venue-hero
    hi=_s.find('class="venue-hero"'); ho=_s.rfind('<',0,hi+1)
    t='div' if _s[ho:ho+4]=='<div' else 'section'
    depth=0; j=ho
    while j<len(_s):
        if _s[j:j+len(t)+1]=='<'+t: depth+=1; j+=len(t)+1; continue
        if _s[j:j+len(t)+3]=='</'+t+'>':
            depth-=1; j+=len(t)+3
            if depth==0: break
            continue
        j+=1
    vn=_NB.get(_fn[:-5],{}).get('venueName') or _fn[:-5].replace('-',' ').title()
    # reassemble modules in nav order, each tagged with its id
    modules_html=''
    navlinks=''
    for aid,label,mk in _order:
        if aid not in _mods: continue
        lbl,seg=_mods[aid]
        # inject id on the block's opening tag
        m2=re.match(r'(<\w+)',seg)
        seg=seg[:len(m2.group(1))]+f' id="{aid}"'+seg[len(m2.group(1)):]
        modules_html+=seg
        navlinks+=f'<a class="vg-navlink" data-vg="{aid}" href="#{aid}">{_h18.escape(lbl.format(vn=vn))}</a>'
    nav=(f'<nav class="vg-nav" aria-label="Venue sections"><div class="vg-nav-inner">{navlinks}</div>'
         '<script>(function(){var n=document.currentScript.closest(".vg-nav");'
         'var links=[].slice.call(n.querySelectorAll(".vg-navlink"));'
         'links.forEach(function(l){l.addEventListener("click",function(e){e.preventDefault();'
         'var t=document.getElementById(l.dataset.vg);if(t)window.scrollTo({top:t.getBoundingClientRect().top+window.pageYOffset-70,behavior:"smooth"});});});'
         'function spy(){var y=window.pageYOffset+90,act=links[0];'
         'links.forEach(function(l){var s=document.getElementById(l.dataset.vg);if(s&&s.offsetTop<=y)act=l});'
         'links.forEach(function(l){l.classList.toggle("vg-on",l===act)});}'
         'window.addEventListener("scroll",spy,{passive:true});spy();})();</script></nav>')
    _cand=_s[:j]+nav+modules_html+_s[j:]
    body=_cand[_cand.find('</nav>'):_cand.find('<footer') if '<footer' in _cand else len(_cand)]
    if body.count('<div')==body.count('</div>'):
        write(os.path.join('venues',_fn),_cand); _jn+=1
    else:
        _jnskip+=1
print(f'jump-nav + ordering: {_jn} pages, {_jnskip} skipped')

# ================= STAGE 21: sticky jump-nav styling =================
JN_CSS = '''
/* ---- 18. Sticky venue jump-nav (generated by build_static.py) ---- */
.vg-nav { position: sticky; top: 0; z-index: 40; background: rgba(255,255,255,0.92);
  backdrop-filter: saturate(180%) blur(12px); -webkit-backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--border-light, #eee); margin-bottom: 1rem; }
.vg-nav-inner { max-width: 1280px; margin: 0 auto; padding: 0 4%; display: flex; gap: 0.4rem;
  overflow-x: auto; scrollbar-width: none; -webkit-overflow-scrolling: touch; }
.vg-nav-inner::-webkit-scrollbar { display: none; }
.vg-navlink { flex: 0 0 auto; padding: 0.9rem 1.1rem; font-family: var(--body); font-size: 0.82rem;
  font-weight: 600; letter-spacing: 0.01em; color: var(--text-dim); text-decoration: none;
  border-bottom: 2px solid transparent; transition: color 0.15s, border-color 0.15s; white-space: nowrap; }
.vg-navlink:hover { color: var(--text); }
.vg-navlink.vg-on { color: var(--text); border-bottom-color: var(--gold); }
/* offset anchor jumps so sticky nav doesn't cover section tops */
#vg-guide, #vg-live, #vg-know, #vg-explore { scroll-margin-top: 70px; }
'''
_ac=read('align.css')
if '18. Sticky venue jump-nav' not in _ac:
    write('align.css', _ac + JN_CSS)
    print('align.css: sticky jump-nav styling appended')
