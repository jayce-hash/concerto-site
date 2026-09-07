#!/usr/bin/env python3
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parent
SITE='https://concertocity.com'

HUBS=[
 '/', '/venues', '/tours', '/setlists', '/near-me', '/your-night', '/perks', '/premium',
 '/about', '/partners', '/partners/restaurants', '/partners/hotels',
 '/partners/venues', '/partners/artists', '/creators', '/press', '/investors',
 '/contact', '/faq', '/help', '/bagcheck', '/bags', '/parking', '/rideshare',
 '/concessions', '/privacy', '/terms'
]

FILE_FOR={
 '/':'index.html','/venues':'venues.html','/tours':'tours.html','/setlists':'setlists.html',
 '/near-me':'near-me.html','/your-night':'your-night.html','/perks':'perks.html','/premium':'premium.html','/about':'about.html',
 '/partners':'partners.html','/partners/restaurants':'partner-restaurants.html',
 '/partners/hotels':'partner-hotels.html','/partners/venues':'partner-venues.html',
 '/partners/artists':'partner-artists.html','/creators':'creators.html','/press':'press.html',
 '/investors':'investors.html','/contact':'contact.html','/faq':'faq.html','/help':'help.html',
 '/bagcheck':'bagcheck.html','/bags':'bags.html','/parking':'parking.html','/rideshare':'rideshare.html',
 '/concessions':'concessions.html','/privacy':'privacy.html','/terms':'terms.html'
}

venues=json.loads((ROOT/'data/venues.json').read_text())
venue_info=json.loads((ROOT/'data/venue_info.json').read_text())
tours=json.loads((ROOT/'data/tours.json').read_text())
setlists=json.loads((ROOT/'setlists.json').read_text())

def max_verified(d):
    vals=[]
    for v in d.values() if isinstance(d,dict) else []:
        if isinstance(v,dict) and v.get('verified'): vals.append(v['verified'])
    return max(vals) if vals else None

def row(loc,lastmod=None):
    x=['  <url>',f'    <loc>{escape(SITE+loc)}</loc>']
    if lastmod: x.append(f'    <lastmod>{escape(lastmod)}</lastmod>')
    x.append('  </url>')
    return '\n'.join(x)

rows=[]
for loc in HUBS:
    f=FILE_FOR[loc]
    if (ROOT/f).exists(): rows.append(row(loc))

for v in sorted(venues,key=lambda x:x['id']):
    slug=v['id']; p=ROOT/'venue'/f'{slug}.html'
    if p.exists(): rows.append(row(f'/venue/{slug}',max_verified(venue_info.get(slug,{}))))

for t in sorted(tours,key=lambda x:x['tourId']):
    slug=t['tourId']; p=ROOT/'tour'/f'{slug}.html'
    if p.exists(): rows.append(row(f'/tour/{slug}',(setlists.get(slug) or {}).get('updated')))

for slug,meta in sorted(setlists.items()):
    p=ROOT/'setlist'/f'{slug}.html'
    if p.exists(): rows.append(row(f'/setlist/{slug}',meta.get('updated')))

xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+'\n'.join(rows)+'\n</urlset>\n'
(ROOT/'sitemap.xml').write_text(xml)
print(f'sitemap.xml: {len(rows)} canonical 200 URLs')
print(f'  hubs/content: {sum(1 for u in HUBS if (ROOT/FILE_FOR[u]).exists())}')
print(f'  venues: {sum(1 for v in venues if (ROOT/"venue"/f"{v["id"]}.html").exists())}')
print(f'  tours: {sum(1 for t in tours if (ROOT/"tour"/f"{t["tourId"]}.html").exists())}')
print(f'  setlists: {sum(1 for k in setlists if (ROOT/"setlist"/f"{k}.html").exists())}')
