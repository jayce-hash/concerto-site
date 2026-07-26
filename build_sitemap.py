#!/usr/bin/env python3
"""
Regenerate sitemap.xml to match the V2 URL structure.

Run from the site repo root:  python3 build_sitemap.py

Why this exists: the old sitemap listed content pages as /about.html
while their canonical tags say /about. Google treats those as two
URLs, follows the sitemap, then finds a canonical pointing somewhere
else -- wasted crawl budget and split signals. It also listed
cityguides.html, which no longer exists, and shop.html and
livemode.html, which are legacy surfaces.

Everything here is derived from what is actually on disk, so the
sitemap can't drift from reality again.
"""
import os
import re
from datetime import date

SITE = 'https://concertocity.com'
TODAY = date.today().isoformat()

# Priority and change frequency by page role. These are hints, not
# instructions -- Google largely infers its own -- but they cost
# nothing and keep the important pages legible.
HUBS = [
    ('/',          '1.0', 'daily'),
    ('/venues',    '0.9', 'weekly'),
    ('/tours',     '0.9', 'daily'),
    # events.tsx was retired; /events 301s here, so /near-me is the
    # single canonical Near Me URL.
    ('/near-me',   '0.8', 'daily'),
    ('/premium',   '0.8', 'monthly'),
    ('/about',     '0.6', 'monthly'),
    ('/faq',       '0.6', 'monthly'),
    ('/bagcheck',  '0.6', 'monthly'),
    ('/privacy',   '0.3', 'yearly'),
    ('/terms',     '0.3', 'yearly'),
]

# Legacy hub pages: still live, still indexed, still earning traffic.
# They keep their old design for now, but excluding them from the
# sitemap would throw away real ranking history for no reason.
LEGACY_HUBS = ['bags', 'parking', 'rideshare', 'concessions',
               'how-it-works', 'setlists', 'top-picks', 'partners',
               'passport', 'features']

# Deliberately EXCLUDED:
#   search, plan, settings, account -> app utility screens; account is
#     behind auth and has nothing to index
#   concertoplus                    -> 301s to /premium
#   mobile-*, livemode              -> the webview era, retiring at
#     native launch
#   login, signup                   -> auth screens
#   404, +not-found, _sitemap       -> not content
EXCLUDE_PREFIXES = ('mobile-', '_', '+', '404', 'login', 'signup',
                    'concertoplus', 'livemode', 'account', 'search',
                    'plan', 'settings', 'shop', 'tourinfo', 'picks',
                    'featuredtours', 'index')


def slugs(folder):
    if not os.path.isdir(folder):
        return []
    out = []
    for f in sorted(os.listdir(folder)):
        if not f.endswith('.html'):
            continue
        s = f[:-5]
        if s.startswith('[') or s.startswith('_'):
            continue  # dynamic route shells aren't pages
        out.append(s)
    return out


def url(loc, priority, freq):
    return (f'  <url>\n'
            f'    <loc>{SITE}{loc}</loc>\n'
            f'    <lastmod>{TODAY}</lastmod>\n'
            f'    <changefreq>{freq}</changefreq>\n'
            f'    <priority>{priority}</priority>\n'
            f'  </url>')


rows = []

for loc, pri, freq in HUBS:
    target = 'index.html' if loc == '/' else loc.lstrip('/') + '.html'
    if os.path.exists(target):
        rows.append(url(loc, pri, freq))

for name in LEGACY_HUBS:
    if os.path.exists(f'{name}.html'):
        rows.append(url(f'/{name}', '0.5', 'monthly'))

venues = slugs('venues')
for s in venues:
    rows.append(url(f'/venues/{s}', '0.7', 'weekly'))

tours = slugs('tours')
for s in tours:
    rows.append(url(f'/tours/{s}', '0.7', 'weekly'))

xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
       + '\n'.join(rows) + '\n</urlset>\n')

with open('sitemap.xml', 'w', encoding='utf-8') as f:
    f.write(xml)

print(f'sitemap.xml: {len(rows)} URLs')
print(f'  hubs + content : {len(rows) - len(venues) - len(tours)}')
print(f'  venue guides   : {len(venues)}')
print(f'  tour guides    : {len(tours)}')
print('  all extensionless, matching the canonical tags')
