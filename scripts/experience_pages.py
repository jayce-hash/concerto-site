"""The public experience: a concert-night story, with real, unframed app captures."""
import html
import json
from pathlib import Path
from public_chrome import APP, page_end, app_link_campaign
from night_components import component, EXAMPLE

ROOT = Path(__file__).resolve().parent.parent
def e(value): return html.escape(str(value), quote=True)

def capture(key, alt, fallback='your-night'):
    # Feature pages still call this; it now returns the data component for the key.
    return component(key)

def _cta(ct, label='Get Concerto for iPhone'):
    return f'<a class="btn-primary" href="{app_link_campaign(ct)}">{label}</a>'

def _rail(keys, label):
    cards=''.join(component(k) for k in keys)
    return f'<div class="moment-rail" role="region" aria-label="{e(label)}" tabindex="0">{cards}</div>'

def _pillars(items):
    return '<div class="pillars">'+''.join(f'<div><span class="pillar-verb">{e(v)}</span><p>{e(t)}</p></div>' for v,t in items)+'</div>'

def _grid(items):
    return '<div class="feature-grid">'+''.join(f'<div><h3>{e(h)}</h3><p>{e(t)}</p></div>' for h,t in items)+'</div>'

def _proof(items):
    return '<div class="proof">'+''.join(f'<div><b>{e(h)}</b><p>{e(t)}</p></div>' for h,t in items)+'</div>'

def close(title='Your next show starts here.', ct='website-footer'):
    return f'<section class="last-call"><div class="site-shell"><h2>{title}</h2><div class="last-call-actions">{_cta(ct)}<img class="qr" src="/img/appstore-qr.png" width="96" height="96" alt="QR code for Concerto on the App Store" loading="lazy"></div><p class="small-print">Free to download. Concerto+ available in the app.</p></div></section>'

from site_v7 import home_page as _home, your_night_page as _yn, premium_page as _plus
def home_page(head, schema): return _home(head, schema)
def your_night_page(head): return _yn(head)
def premium_page(head): return _plus(head)
