#!/usr/bin/env python3
"""About, Creators, Contact, and FAQ on the V6 system. FAQ answers live in
scripts/faq.json (edit there); the contact form is kept verbatim in
scripts/forms/contact.html. Help stays hand-written in help.html."""
import html, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from public_chrome import header_html, page_end, HEAD_ASSETS, product_screen, photo_slot, APP, SITE

def e(x): return html.escape(str(x or ''), quote=True)
def head(title, desc, canonical, extra=''):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="apple-itunes-app" content="app-id=6744903414"><title>{e(title)}</title><meta name="description" content="{e(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{SITE+canonical}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{SITE+canonical}"><meta property="og:image" content="{SITE}/ConcertoSocialPreview.png"><meta property="og:site_name" content="Concerto"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE}/ConcertoSocialPreview.png"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png">{HEAD_ASSETS}{extra}</head><body class="public-site">') + header_html(canonical)

venues = json.loads((ROOT / 'data/venues.json').read_text()); tours = json.loads((ROOT / 'data/tours.json').read_text())
setlists = json.loads((ROOT / 'setlists.json').read_text()); live = sum(1 for k, v in setlists.items() if v.get('songs'))

from company_pages import build_support_pages
build_support_pages(head)

# ---------------------------------------------------------------- FAQ
qa = json.loads((ROOT / 'scripts/faq.json').read_text())
items = ''.join(f'<details class="card"><summary>{q}</summary><p>{a}</p></details>' for q, a in qa)
ld = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': html.unescape(q), 'acceptedAnswer': {'@type': 'Answer', 'text': html.unescape(a)}} for q, a in qa]}
extra = '<script type="application/ld+json">' + json.dumps(ld).replace('</', '<\\/') + '</script>'
faq = head('FAQ | Concerto', 'How Concerto works, what stays free, how Your Night and Perks fit in, what Concerto+ adds, and what verified means.', '/faq', extra) + f'''<main>
<section class="page-hero-v4 compact"><div class="site-shell"><p class="eyebrow">FAQ</p><h1>Answers without the scavenger hunt.</h1><p class="lead">How Concerto works, what stays free, what Your Night is, and what Concerto+ adds. For step-by-step help, use the Help Center.</p><div class="hero-actions"><a class="btn-secondary" href="/help">Help Center</a><a class="btn-secondary" href="/contact">Contact</a></div></div></section>
<section class="section"><div class="shell"><div class="faq-list">{items}</div></div></section>
<section class="cta-band"><div class="site-shell"><p class="eyebrow">Still stuck</p><h2>Talk to a real person.</h2><p>Fan support answers at support@concertocity.com. Partners and media have their own channels on the Contact page.</p><div class="hero-actions"><a class="btn-primary" href="/contact">Contact Concerto</a></div></div></section>
</main>''' + page_end()
(ROOT / 'faq.html').write_text(faq)
print('built about, creators, contact, faq')

# Public search belongs to the website, not the exported app shell.
search = head('Search Concerto', 'Find venue guides, artists, tours, and available setlists.', '/search').replace('index,follow,max-image-preview:large', 'noindex,follow')
search += '''<main><section class="search-hero"><div class="site-shell"><p class="eyebrow">Search Concerto</p><h1>Where’s the show?</h1><p>Find a venue, artist, tour, city, or available setlist.</p><div class="site-search-box"><input data-site-search type="search" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Venue, artist, tour, or city" aria-label="Search Concerto"></div></div></section><section class="search-results-section"><div class="site-shell"><div data-site-search-results class="site-search-results" aria-live="polite"><div class="search-empty">Try an artist, tour, venue, or city.</div></div></div></section></main>'''
(ROOT / 'search.html').write_text(search + page_end())
