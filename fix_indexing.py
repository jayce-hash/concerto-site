#!/usr/bin/env python3
"""
One-shot fix: GSC indexing report (7/23/26) + Passport retirement.

Run from the site repo root:  python3 fix_indexing.py
Then:                         python3 build_sitemap.py
                              git add -A && git commit && git push

Safe to run twice -- every edit checks before it writes.

PART 1 -- GSC "Why pages aren't indexed"
  - Legacy hubs in the sitemap at extensionless URLs but canonical to
    .html: top-picks, partners, features, setlists rewritten;
    picks/featuredtours/tourinfo lose their .html canonical targets.
  - bagcheck: full SEO block (empty head despite sitting in the
    sitemap); search/plan/settings/account: noindex + real titles.
  - /venue/* and /tour/* app shells, +not-found, _sitemap, (tabs)/*
    export artifacts: noindex.
  - Dead /cityguide/* 200 rewrite removed from _redirects (folder is
    gone; the rule 404'd everything AND shadowed netlify.toml's 301).
  - events/concertoplus/shop .html deleted so their 301s actually
    fire (Netlify serves real files before redirects).

PART 2 -- Passport is retired
  - passport.html + mobile-livemode.html deleted; /passport,
    /livemode -> /features 301; /mobile-livemode -> /mobile-account.
  - 'passport' removed from LEGACY_HUBS in build_sitemap.py.
  - All 76 tour-page footers: "AI Bag Check, Passport, real-time
    setlists" -> "AI Bag Check, real-time setlists".
  - mobile.html: Passport card + Passport Recaps feature row removed.
  - mobile-account.html / mobile-premium.html: Passport stripped from
    titles, metas, JSON-LD, marquee, and the feature-card grid.
  - NOT covered here: the Expo APP still markets Passport (its FAQ
    and premium copy live in the app source). Remove it there and
    re-export -- see instructions.

PART 3 -- Account page dev notice
  - "Purchases need a full app build, not Expo Go..." hammer banner:
    the JSX ternary's fallback branch is patched to null in every
    _expo entry bundle that contains it. Fix it at the source too
    (gate the notice on __DEV__) so the next export doesn't bring it
    back.
"""
import glob
import os
import re
import sys

if not os.path.exists('build_sitemap.py'):
    sys.exit('Run this from the site repo root.')

MARK = '<meta http-equiv="X-UA-Compatible" content="IE=edge"/>'
SITE = 'https://concertocity.com'
changed = []


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def write(p, h):
    with open(p, 'w', encoding='utf-8') as f:
        f.write(h)
    changed.append(p)


def edit(p, fn):
    """Apply fn to file contents; record only if changed."""
    if not os.path.exists(p):
        return
    h = read(p)
    new = fn(h)
    if new != h:
        write(p, new)


# ════════════════════════════════════════════════════════════════════
# PART 1 -- indexing fixes
# ════════════════════════════════════════════════════════════════════

CANON = {
    'top-picks.html':     f'{SITE}/top-picks',
    'partners.html':      f'{SITE}/partners',
    'features.html':      f'{SITE}/features',
    'setlists.html':      f'{SITE}/setlists',
    'picks.html':         f'{SITE}/top-picks',
    'featuredtours.html': f'{SITE}/tours',
    'tourinfo.html':      f'{SITE}/tourinfo',
}
for f, target in CANON.items():
    edit(f, lambda h, t=target: re.sub(
        r'(rel="canonical"\s+href=")[^"]*(")', rf'\g<1>{t}\g<2>', h))


def inject(path, block):
    if not os.path.exists(path):
        return
    h = read(path)
    if MARK not in h or 'name="robots"' in h or 'rel="canonical"' in h:
        return
    write(path, h.replace(MARK, MARK + block, 1))


bag_t = 'AI Bag Check — Will My Bag Get In? | Concerto'
bag_d = ("Snap a photo of your bag and Concerto checks it against the "
         "venue's verified bag policy before you leave home.")
inject('bagcheck.html',
       f'<title>{bag_t}</title>'
       f'<meta name="description" content="{bag_d}">'
       f'<link rel="canonical" href="{SITE}/bagcheck">'
       f'<meta name="apple-itunes-app" content="app-id=6744903414">'
       f'<meta property="og:type" content="website">'
       f'<meta property="og:site_name" content="Concerto">'
       f'<meta property="og:title" content="{bag_t}">'
       f'<meta property="og:description" content="{bag_d}">'
       f'<meta property="og:url" content="{SITE}/bagcheck">'
       f'<meta property="og:image" content="{SITE}/ConcertoSocialPreview.png">'
       f'<meta name="twitter:card" content="summary_large_image">'
       f'<meta name="twitter:image" content="{SITE}/ConcertoSocialPreview.png">')

for f, t in [('search.html', 'Search | Concerto'),
             ('plan.html', 'Night Planner | Concerto'),
             ('settings.html', 'Settings | Concerto'),
             ('account.html', 'Account | Concerto')]:
    inject(f, f'<title>{t}</title><meta name="robots" content="noindex">')

for f in ['venue/[slug].html', 'tour/[slug].html', 'venues/[slug].html',
          'tours/[slug].html', '+not-found.html', '_sitemap.html',
          '(tabs)/index.html', '(tabs)/venues.html', '(tabs)/tours.html',
          '(tabs)/near-me.html', '(tabs)/account.html']:
    inject(f, '<meta name="robots" content="noindex">')

# ════════════════════════════════════════════════════════════════════
# PART 2 -- Passport retirement
# ════════════════════════════════════════════════════════════════════

for f in ['events.html', 'concertoplus.html', 'shop.html',
          'livemode.html', 'passport.html', 'mobile-livemode.html']:
    if os.path.exists(f):
        os.remove(f)
        changed.append(f + '  (DELETED)')

# build_sitemap.py: passport out of LEGACY_HUBS
edit('build_sitemap.py', lambda h: re.sub(r"'passport',\s*", '', h))

# 76 tour-page footers
for f in glob.glob('tours/*.html'):
    edit(f, lambda h: h.replace(
        'AI Bag Check, Passport, real-time setlists',
        'AI Bag Check, real-time setlists'))

# mobile.html: Passport card + Passport Recaps row
edit('mobile.html', lambda h: re.sub(
    r'<a href="mobile-livemode\.html" class="card">.*?</a>\s*',
    '', h, flags=re.S))
edit('mobile.html', lambda h: re.sub(
    r'<div class="pf"><div class="pf-dot"></div><div class="pf-text">'
    r'<strong>Passport Recaps</strong>.*?</div></div>\s*',
    '', h, flags=re.S))

# mobile-account.html
edit('mobile-account.html', lambda h: h.replace(
    'AI Bag Check, Passport, and Concerto+ AI Itinerary',
    'AI Bag Check and Concerto+ AI Itinerary'))

# mobile-premium.html: titles/metas, JSON-LD, marquee, feature card
def fix_mobile_premium(h):
    h = h.replace(', Passport Recaps &amp; Concert', ' &amp; Concert')
    h = h.replace(', Passport Recaps & Concert', ' & Concert')
    h = h.replace('AI Bag Check, Passport recaps and story cards, and '
                  'Concerto+ AI itineraries',
                  'AI Bag Check and Concerto+ AI itineraries')
    h = h.replace('AI Bag Check, Passport, and Concerto+ AI Itineraries',
                  'AI Bag Check and Concerto+ AI Itineraries')
    h = h.replace('AI Bag Check &bull; Passport &bull;',
                  'AI Bag Check &bull;')
    h = re.sub(r'<a[^>]*id="feat-livemode"[^>]*>.*?</a>\s*', '',
               h, flags=re.S)
    return h

edit('mobile-premium.html', fix_mobile_premium)

# _redirects: kill dead cityguide rule, add retirement 301s
def fix_redirects(h):
    h = re.sub(r'# City guide SPA \(unchanged\)\n'
               r'/cityguide/\*\s+/cityguide/index\.html\s+200\n\n?', '', h)
    if '/passport' not in h:
        block = ('# Retired surfaces -- files deleted so these actually '
                 'fire. Passport\n# (formerly Live Mode) is retired '
                 'entirely; /features carries the story.\n'
                 '/passport               /features          301\n'
                 '/passport.html          /features          301\n'
                 '/livemode               /features          301\n'
                 '/livemode.html          /features          301\n'
                 '/shop                   /premium           301\n'
                 '/shop.html              /premium           301\n'
                 '/mobile-livemode        /mobile-account    301\n'
                 '/mobile-livemode.html   /mobile-account.html   301\n\n')
        h = h.replace('# Real 404 for anything else.',
                      block + '# Real 404 for anything else.', 1)
    return h

edit('_redirects', fix_redirects)

# ════════════════════════════════════════════════════════════════════
# PART 3 -- dev-build purchase notice out of the web bundles
# ════════════════════════════════════════════════════════════════════

NOTICE_RE = re.compile(
    r':\(0,[\w$]+\.jsxs\)\([\w$]+\.default,\{style:[\w$]+\.devBuildNotice,'
    r'children:\[.*?App Store build\."\}\)\]\}\)', re.S)

patched = 0
for f in glob.glob('_expo/static/js/web/entry-*.js'):
    h = read(f)
    if 'devBuildNotice' not in h:
        continue
    new, n = NOTICE_RE.subn(':null', h)
    if n:
        write(f, new)
        patched += n

print(f'{len(changed)} files touched ({patched} bundle notice(s) patched):')
for c in changed:
    print('  ', c)
print('\nNext:  python3 build_sitemap.py')
print('       git add -A && git commit -m "GSC fixes + Passport retirement"'
      ' && git push')
