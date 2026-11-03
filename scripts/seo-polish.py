#!/usr/bin/env python3
"""Last pass over the built pages, for search and AI answers (HeyCatch SEO audit, Nov 2 2026).

1. Titles: every indexable page gets a unique title of 30-60 characters. " | Concerto" is kept
   when it fits and dropped when it would push the page's own words past 60.
2. Definitions: venue, tour, setlist and state pages open with a plain "X is ..." line.
3. Structured data: Organization on every page that lacks it; Article on the founder letter.

Runs after every generator and before the sitemap. Safe to run twice: each step checks first.
"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUF = ' | Concerto'
LO, HI = 30, 60
SKIP_DIRS = {'scripts', 'node_modules', 'netlify', 'supabase', '_expo', 'assets', 'console', 'decks', 'partners-kit'}

venues = {v['id']: v for v in json.loads((ROOT / 'data/venues.json').read_text())}
tours = {t['tourId']: t for t in json.loads((ROOT / 'data/tours.json').read_text())}

KIND = {'arena': 'an arena', 'stadium': 'a stadium', 'theater': 'a theater', 'club': 'a live music club',
        'amphitheater': 'an amphitheater', 'festival': 'a music festival'}

# Company pages whose titles were under 30 characters.
FIXED = {
    'faq.html': 'Concerto FAQ: Venue Guides, Setlists & Concerto+',
    'investors.html': 'Investors: Concerto, the Concert Companion App',
    'press.html': 'Press & Media: Concerto, the Concert Companion App',
    'about.html': 'About Concerto: The Concert Companion App',
    'contact.html': 'Contact Concerto: Support, Press & Partners',
    'founder.html': 'From the Founder: Why I Built Concerto',
}


def tour_parts(t):
    artist, name = t['artist'].strip(), t['tourName'].strip()
    if name.lower().startswith(artist.lower()):
        name = name[len(artist):].lstrip(' :-–') or name
    return artist, name


def first_fit(cands):
    for c in cands:
        if LO <= len(c) <= HI:
            return c
    short = [c for c in cands if len(c) <= HI]
    return (max(short, key=len) if short else min(cands, key=len))


def with_suffix(*owns):
    out = []
    for o in owns:
        out += [o + SUF, o]
    return out


def title_for(rel, cur):
    own = cur[:-len(SUF)] if cur.endswith(SUF) else cur
    if rel in FIXED:
        return FIXED[rel]
    parts = rel.split('/')
    if parts[0] == 'tour' and len(parts) == 2:
        t = tours.get(parts[1][:-5])
        if t:
            a, n = tour_parts(t)
            base = f'{a} {n}'
            tw = '' if 'tour' in n.lower() else ' Tour'
            return first_fit(with_suffix(own, f'{base}{tw} Dates & Setlist', f'{base}{tw} Dates',
                                         f'{a} Tour Dates & Setlist', f'{a}: {n}'))
    if parts[0] == 'setlist' and len(parts) == 2:
        t = tours.get(parts[1][:-5])
        if t:
            a, n = tour_parts(t)
            return first_fit(with_suffix(own, f'{a} {n} Setlist', f'{a} Setlist: {n}', f'{a} Tour Setlist', f'{a} Setlist'))
    if parts[0] == 'venue' and len(parts) == 2:
        v = venues.get(parts[1][:-5])
        if v:
            nm = v['name']
            no_year = re.sub(r'\s*\b20\d\d\b', '', own)
            no_abbr = re.sub(r'\s*\([^)]*\)', '', no_year)
            return first_fit(with_suffix(own, no_year, no_abbr, f'{nm} Bag Policy & Venue Guide',
                                         f'{nm} Bag Policy', f'{nm} Venue Guide', nm))
    if parts[0] == 'concert-venues' and len(parts) == 2:
        m = re.match(r'Concert Venues in (.+?):', own)
        place = m.group(1) if m else ''
        return first_fit(with_suffix(own, f'Concert Venues in {place}: Bag Policy & Parking',
                                     f'{place} Concert Venues: Bag Policy & Parking',
                                     f'Concert Venues in {place}: Venue Guides', f'Concert Venues in {place}'))
    if len(cur) < LO and not cur.endswith(SUF):
        return cur + SUF
    return first_fit(with_suffix(own)) if len(cur) > HI else cur


def set_title(src, new):
    t = html.escape(new, quote=False)
    q = html.escape(new, quote=True)
    src = re.sub(r'<title>.*?</title>', lambda m: f'<title>{t}</title>', src, count=1, flags=re.S)
    for attr in (r'property="og:title"', r'name="twitter:title"'):
        src = re.sub(r'(<meta ' + attr + r' content=")[^"]*(")', lambda m: m.group(1) + q + m.group(2), src, count=1)
    return src


def a_an(word):
    return ('an ' if word[:1].lower() in 'aeiou' else 'a ') + word


def definitions(rel, src):
    parts = rel.split('/')
    if len(parts) != 2:
        return src
    slug = parts[1][:-5]
    if parts[0] == 'venue' and slug in venues:
        v = venues[slug]
        place = ', '.join(x for x in (v.get('city'), v.get('state') or v.get('country')) if x)
        line = f"{v['name']} is {KIND.get(v.get('type'), 'a live music venue')} in {place}."
        return re.sub(r'(</h1><p class="c-lead">)([^<]*)(</p>)',
                      lambda m: m.group(0) if ' is ' in m.group(2) else m.group(1) + html.escape(line, quote=False) + m.group(3),
                      src, count=1)
    if parts[0] == 'tour' and slug in tours:
        a, n = tour_parts(tours[slug])
        what = 'a concert residency' if re.search(r'sphere|residency|las vegas', n, re.I) else 'a concert tour'
        line = f'{n} is {what} by {a}.'
        return re.sub(r'(</h1><p class="c-lead">)([^<]*)(</p>)',
                      lambda m: m.group(0) if ' is ' in m.group(2) else m.group(1) + html.escape(line, quote=False) + m.group(3),
                      src, count=1)
    if parts[0] == 'setlist' and slug in tours:
        a, n = tour_parts(tours[slug])
        return re.sub(r'(</h1><p class="c-lead">)(\d+) songs\. Reported setlist from',
                      lambda m: f'{m.group(1)}The setlist for {html.escape(n)} by {html.escape(a)} is {m.group(2)} songs, reported from',
                      src, count=1)
    if parts[0] == 'concert-venues':
        m = re.search(r'Venue guides · ([^<]+)</p>', src)
        if m:
            place = m.group(1).strip()
            return re.sub(r'(<p class="c-lead">)(\d[\d,]*) venue guides: ',
                          lambda x: f'{x.group(1)}This is Concerto’s guide to {x.group(2)} concert venues in {place}, with ',
                          src, count=1)
    return src


ORG = None
def org_block():
    global ORG
    if ORG is None:
        s = (ROOT / 'index.html').read_text()
        m = re.search(r'\{[^{}]*"@type": *"Organization".*?"sameAs": *\[[^\]]*\][^{}]*\}', s, re.S)
        org = json.loads(m.group(0)) if m else {'@type': 'Organization', '@id': 'https://concertocity.com/#org',
                                                   'name': 'Concerto', 'url': 'https://concertocity.com'}
        org['@context'] = 'https://schema.org'
        org['founder'] = {'@type': 'Person', 'name': 'Jayce Wells', 'sameAs': ['https://www.linkedin.com/in/jayce-wells']}
        ORG = org
    return ORG


def structured(rel, src):
    if '"Organization"' not in src and '</head>' in src:
        src = src.replace('</head>', '<script type="application/ld+json">' + json.dumps(org_block(), ensure_ascii=False) + '</script></head>', 1)
    if rel == 'founder.html' and '"Article"' not in src:
        art = {'@context': 'https://schema.org', '@type': 'Article', 'headline': 'From the Founder: Why I Built Concerto',
               'url': 'https://concertocity.com/founder',
               'author': {'@type': 'Person', 'name': 'Jayce Wells', 'jobTitle': 'Founder', 'sameAs': ['https://www.linkedin.com/in/jayce-wells']},
               'publisher': {'@id': 'https://concertocity.com/#org'}, 'image': 'https://concertocity.com/img/app-icon.png'}
        src = src.replace('</head>', '<script type="application/ld+json">' + json.dumps(art, ensure_ascii=False) + '</script></head>', 1)
    return src


PRIV_START = '# ── BEGIN private files (scripts/seo-polish.py) ──'
PRIV_END = '# ── END private files ──'
def private_files():
    """The site publishes the repo root, so build scripts, notes and SQL were reachable (and
    scripts/handbuilt/ held duplicate copies of two partner pages). Answer 404 for all of them."""
    rules = [f'/{d}/*  /404.html  404!' for d in ('scripts', 'supabase', 'netlify')]
    for f in sorted(ROOT.iterdir()):
        if f.is_file() and (f.suffix in ('.md', '.py') or f.name in ('package.json', 'package-lock.json', 'VENUE-ENTRY-EXAMPLE.json')):
            rules.append(f'/{f.name}  /404.html  404!')
    block = '\n'.join([PRIV_START] + rules + [PRIV_END])
    rp = ROOT / '_redirects'
    r = rp.read_text()
    r = re.sub(re.escape(PRIV_START) + r'.*?' + re.escape(PRIV_END) + r'\n*', '', r, flags=re.S)
    rp.write_text(block + '\n\n' + r)


def main():
    private_files()
    pages = []
    for p in sorted(ROOT.rglob('*.html')):
        rel = p.relative_to(ROOT).as_posix()
        if rel.split('/')[0] in SKIP_DIRS or rel.startswith('.'):
            continue
        src = p.read_text()
        if re.search(r'<meta name="robots" content="[^"]*noindex', src):
            continue
        pages.append((p, rel, src))

    seen, changed = {}, 0
    for p, rel, src in pages:
        m = re.search(r'<title>(.*?)</title>', src, re.S)
        if not m:
            continue
        cur = html.unescape(m.group(1).strip())
        new = title_for(rel, cur)
        if new.lower() in seen:  # never two pages with one title
            new = cur if cur.lower() not in seen else f'{new[:HI - 4]} ({len(seen)})'
        seen[new.lower()] = rel
        out = definitions(rel, structured(rel, set_title(src, new) if new != cur else src))
        if out != src:
            p.write_text(out); changed += 1
    n = len(seen)
    ok = sum(LO <= len(t) <= HI for t in seen)
    print(f'seo polish: {changed} pages updated; {ok} of {n} titles are 30-60 characters')


if __name__ == '__main__':
    main()
