#!/usr/bin/env python3
"""Build public membership and company pages with category-specific inquiry forms."""
import html, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from public_chrome import header_html, page_end, HEAD_ASSETS, product_screen, photo_slot, APP, SITE

def e(x): return html.escape(str(x or ''), quote=True)
import json as _json
tours=_json.loads((ROOT/'data/tours.json').read_text()); venues=_json.loads((ROOT/'data/venues.json').read_text())
_sl=_json.loads((ROOT/'setlists.json').read_text()); live=sum(1 for v in _sl.values() if v.get('songs'))

def head(title, desc, canonical, extra=''):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="apple-itunes-app" content="app-id=6744903414"><title>{e(title)}</title><meta name="description" content="{e(desc)}">'
            f'<meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{SITE+canonical}">'
            f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:type" content="website">'
            f'<meta property="og:url" content="{SITE+canonical}"><meta property="og:image" content="{SITE}/ConcertoSocialPreview.png"><meta property="og:site_name" content="Concerto">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE}/ConcertoSocialPreview.png">'
            f'<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png">'
            f'{HEAD_ASSETS}{extra}</head><body class="public-site">') + header_html(canonical)

from consumer_pages import premium_page
from company_pages import build_company_pages
(ROOT / "premium.html").write_text(premium_page(head))
build_company_pages(head)
print("Built aligned partners, Perks, premium, investors, and press")
