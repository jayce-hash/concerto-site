#!/usr/bin/env python3
"""Pre-launch SEO audit of the generated site. Run before touching Search Console."""
import re, json, os, sys
from pathlib import Path
from collections import Counter, defaultdict
ROOT=Path(__file__).resolve().parent.parent; SITE='https://concertocity.com'
issues=defaultdict(list)
rules=[l.split('#')[0].split() for l in (ROOT/'_redirects').read_text().splitlines() if l.split('#')[0].strip()]
def match(p):
    for r in rules:
        f=r[0]
        if f==p: return r
        if f.endswith('/*'):
            b=f[:-2]
            if p==b or p.startswith(b+'/'): return r
    return None
def isfile(p): f=ROOT/p.lstrip('/'); return f.is_file()
def resolve(p,hops=0):
    """Return ('200',file) | ('301',target) | ('404',None) | ('CHAIN',...)."""
    r=match(p); forced=bool(r and r[2].endswith('!'))
    if not forced and isfile(p): return ('200',p)
    if not r: return ('404',None)
    f,t,code=r[0],r[1],r[2].rstrip('!')
    if f.endswith('/*'):
        b=f[:-2]; splat='' if p==b else p[len(b)+1:]; t=t.replace(':splat',splat)
    if code=='200': return ('200',t) if isfile(t) else ('404',None)
    if code=='404': return ('404',None)
    return ('301',t)
def chain(p):
    hops=[]; cur=p
    for _ in range(6):
        st,t=resolve(cur)
        if st!='301': return st,hops
        hops.append(t); cur=t.split('?')[0]
    return 'LOOP',hops
def head(html): return html.split('</head>')[0]
def canonical(html):
    m=re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"',head(html)) or re.search(r'<link[^>]*href="([^"]+)"[^>]*rel="canonical"',head(html)); return m.group(1) if m else None
def robots(html):
    m=re.search(r'<meta[^>]*name="robots"[^>]*content="([^"]+)"',head(html)) or re.search(r'<meta[^>]*content="([^"]+)"[^>]*name="robots"',head(html)); return (m.group(1) if m else '').replace(' ','').lower()
def title(html): m=re.search(r'<title>(.*?)</title>',html,re.S); return m.group(1).strip() if m else ''
def text_words(html):
    b=html.split('<main',1)[1] if '<main' in html else html
    b=b.split('<!-- CONCERTO_CHROME_FOOTER_START')[0]
    b=re.sub(r'<script.*?</script>','',b,flags=re.S); b=re.sub(r'<[^>]+>',' ',b); return len(b.split())

# ---- inventory
pages={}
for d in ['.','venue','tour','setlist']:
    for f in sorted((ROOT/d).glob('*.html')):
        rel=str(f.relative_to(ROOT)); pages[rel]=f.read_text()
sitemap=(ROOT/'sitemap.xml').read_text(); locs=re.findall(r'<loc>([^<]+)</loc>',sitemap)
print(f'pages on disk: {len(pages)} | sitemap urls: {len(locs)}')

# ---- sitemap checks
seen=set()
for u in locs:
    if not u.startswith(SITE): issues['sitemap: non-canonical host'].append(u)
    p=u[len(SITE):] or '/'
    if u in seen: issues['sitemap: duplicate'].append(u)
    seen.add(u)
    if p.endswith('.html') or p.endswith('/') and p!='/': issues['sitemap: non-canonical form'].append(u)
    st,hops=chain(p)
    if st!='200': issues[f'sitemap: not 200 ({st})'].append(f'{u} -> {hops}')
    else:
        _,f=resolve(p); html=pages.get(f.lstrip('/'))
        if html is None: issues['sitemap: file missing'].append(u); continue
        if 'noindex' in robots(html): issues['sitemap: noindex page listed'].append(u)
        c=canonical(html)
        if c!=u: issues['sitemap: canonical mismatch'].append(f'{u} canonical={c}')
# ---- every indexable page must be in the sitemap; every page must have a self canonical
titles=Counter(); descs=Counter()
for rel,html in pages.items():
    rb=robots(html); c=canonical(html); t=title(html); titles[t]+=1
    m=re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"',head(html)) or re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="description"',head(html)); d=m.group(1) if m else ''
    descs[d]+=1
    route='/' if rel=='index.html' else '/'+rel[:-5]
    if 'noindex' in rb:
        if SITE+route in locs: issues['noindex page in sitemap'].append(rel)
        continue
    if not c: issues['missing canonical'].append(rel); continue
    if not c.startswith(SITE): issues['canonical wrong host'].append(f'{rel} {c}')
    cp=c[len(SITE):] or '/'
    st,_=chain(cp)
    if st!='200': issues['canonical target not 200'].append(f'{rel} -> {c} ({st})')
    if SITE+cp not in locs and not rel.startswith(('partner-','contact-')): issues['indexable page missing from sitemap'].append(f'{rel} canonical={c}')
    if not t: issues['missing title'].append(rel)
    if not d: issues['missing meta description'].append(rel)
    w=text_words(html)
    if w<120: issues['thin page (<120 words)'].append(f'{rel} ({w} words)')
    if not re.search(r'<h1[ >]',html): issues['missing h1'].append(rel)
    if len(re.findall(r'<h1[ >]',html))>1: issues['multiple h1'].append(rel)
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',html,re.S):
        try: json.loads(m.replace('<\\/','</'))
        except Exception as e: issues['invalid ld+json'].append(f'{rel}: {e}')
    if 'react-native-stylesheet' in html or '_expo/static' in html: issues['expo shell indexable'].append(rel)
for t,n in titles.items():
    if n>1 and t: issues['duplicate title'].append(f'{n}x "{t[:70]}"')
for rel,html in pages.items():
    if not title(html) and 'noindex' not in robots(html): issues['missing title'].append(rel)
for d,n in descs.items():
    if n>1 and d: issues['duplicate description'].append(f'{n}x "{d[:70]}"')
# ---- redirect hygiene
for r in rules:
    f,t,code=r[0],r[1],r[2]
    if code.startswith('301') and not t.startswith('http') and '*' not in f and ':splat' not in t:
        st,hops=chain(t)
        if st=='301': issues['redirect chain'].append(f'{f} -> {t} -> {hops}')
        if st=='404': issues['redirect to 404'].append(f'{f} -> {t}')
# .html duplicates of canonical routes
missing_html_rules=[]
for rel in pages:
    if rel=='index.html': continue
    st,hops=chain('/'+rel)
    if not hops and 'noindex' not in robots(pages[rel]):
        missing_html_rules.append(rel)
if missing_html_rules: issues['.html duplicate of canonical route reachable (needs 301)'] = missing_html_rules
st,hops=chain('/index.html')
if not hops: issues['.html duplicate of canonical route reachable (needs 301)'].append('index.html')
# retired routes should not be 200
for p in ['/top-picks','/events','/passport','/livemode','/shop','/login','/signup','/cityguides','/cityguide/madison-square-garden','/venues/madison-square-garden','/tours/ac-dc-power-up-tour','/setlists/ariana-grande-the-eternal-sunshine-tour-na','/tours/fifa-world-cup-2026','/mobile-bags','/concertoplus']:
    st,hops=chain(p)
    if not hops: issues['retired route not redirecting'].append(f'{p} ({st})')
    elif st!='200': issues['retired route redirects to non-200'].append(f'{p} -> {hops} ({st})')
    elif len(hops)>1: issues['retired route redirect chain'].append(f'{p} -> {hops}')
# genuine 404 for junk
for p in ['/this-does-not-exist','/venue/not-a-venue','/tour/not-a-tour','/setlist/not-a-setlist']:
    st,_=chain(p)
    if st!='404': issues['should be 404'].append(f'{p} ({st})')
# ---- report
total=sum(len(v) for v in issues.values())
for k,v in issues.items():
    print(f'\n## {k} ({len(v)})'); [print('  -',x) for x in v[:8]]; 
    if len(v)>8: print(f'  ... {len(v)-8} more')
print(f'\n{total} issues' if total else '\nCLEAN: no SEO issues found')
sys.exit(1 if total else 0)
