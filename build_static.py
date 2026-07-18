#!/usr/bin/env python3
"""
Concerto static build. Bakes JSON data into pages, upgrades schema,
adds nearby-venue links, converts images to WebP, adds lazy loading,
skip links, analytics hook, and generates static city guide pages.

Idempotent: safe to re-run after data/*.json changes.
Run from the site root:  python3 build_static.py
"""
import json, math, os, re, sys, html.parser

ROOT = os.path.dirname(os.path.abspath(__file__))
def rp(*p): return os.path.join(ROOT, *p)

def read(p):  return open(rp(p), encoding='utf-8').read()
def write(p, s): open(rp(p), 'w', encoding='utf-8').write(s)

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
for f in ['bagcheck.html', 'mobile-bags.html']:
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
.hero-search{position:relative;max-width:680px;margin:2.4rem auto 0;display:flex;align-items:center;}
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
  function match(q){ q=q.toLowerCase();
    var vs=(IDX.venues||[]).filter(function(v){return v.name.toLowerCase().indexOf(q)>-1;}).slice(0,5)
      .map(function(v){return {name:v.name, sub:v.type||'', href:'/venues/'+v.slug, type:'Venue'};});
    var ts=(IDX.tours||[]).filter(function(t){return (t.name+' '+(t.artist||'')).toLowerCase().indexOf(q)>-1;}).slice(0,3)
      .map(function(t){return {name:t.artist?t.artist:t.name, sub:t.artist?t.name:'', href:'/tours/'+t.slug, type:'Tour'};});
    return vs.concat(ts).slice(0,8); }
  function render(items){ sel=-1;
    if(!items.length){ box.hidden=true; inp.setAttribute('aria-expanded','false'); return; }
    box.innerHTML=items.map(function(it){
      return '<a href="'+esc(it.href)+'"><span>'+esc(it.name)+(it.sub?' <span class="hs-sub">'+esc(it.sub)+'</span>':'')+'</span><span class="hs-type">'+it.type+'</span></a>';
    }).join('');
    box.hidden=false; inp.setAttribute('aria-expanded','true'); }
  inp.addEventListener('focus',function(){ load(); });
  inp.addEventListener('input',function(){ var q=inp.value.trim();
    if(q.length<2){ box.hidden=true; return; }
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
