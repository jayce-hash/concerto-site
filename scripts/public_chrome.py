"""Concerto public web chrome: one header, one footer, baked into every page.

Both generators (build-public-site.py, build-public-features.py) and the
stamping script for hand-written pages (apply-public-chrome.py) import this,
so the navigation is real HTML in the initial response on every URL. The JS in
js/public-v6.js only wires up the menu button and never rebuilds the header.
"""
import html

# Apple App Analytics campaign attribution. pt is the account-level provider
# token (App Store Connect > Analytics > Campaigns); ct is a freeform string
# identifying where the click came from and does not need to be pre-created in
# the App Store Connect UI, Apple attributes any pt/ct pair it sees on install.
# Bare APP (no ct) is the fallback for places we haven't tagged individually;
# app_link_campaign() lets a specific page type report separately so we can
# see which pages actually drive installs.
_APP_BASE = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414'
_PT = '127753814'
APP = f'{_APP_BASE}?pt={_PT}&ct=website-default&mt=8'
SITE = 'https://concertocity.com'


def app_link_campaign(ct):
    """App Store link tagged for a specific page type, e.g. 'website-venue',
    'website-tour', 'website-home'. Use on the primary "Get the App" CTA of a
    template; secondary/incidental links can keep using the bare APP constant."""
    return f'{_APP_BASE}?pt={_PT}&ct={ct}&mt=8'

NAV = [
    ('How It Works', '/your-night'),
    ('Venues', '/venues'),
    ('Tours', '/tours'),
    ('Concerto+', '/premium'),
]
MENU_EXTRA = [('Search', '/search'), ('Help', '/help')]

HEADER_START = '<!-- CONCERTO_CHROME_HEADER_START -->'
HEADER_END = '<!-- CONCERTO_CHROME_HEADER_END -->'
FOOTER_START = '<!-- CONCERTO_CHROME_FOOTER_START -->'
FOOTER_END = '<!-- CONCERTO_CHROME_FOOTER_END -->'

HEAD_ASSETS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800'
    '&family=Playfair+Display:wght@500;600&display=swap" rel="stylesheet">'
    '<link rel="stylesheet" href="/css/public-v6.css">'
    '<script src="/analytics.js" defer></script>'
)


def _e(x):
    return html.escape(str(x or ''), quote=True)


def is_active(href, path):
    path = (path or '/').replace('.html', '').rstrip('/') or '/'
    if path == href:
        return True
    prefixes = {
        '/venues': '/venue/',
        '/tours': '/tour/',
        '/setlists': '/setlist/',
        '/partners': '/partners/',
    }
    p = prefixes.get(href)
    return bool(p and path.startswith(p))


def header_html(path='/'):
    def link(label, href, cls=''):
        active = is_active(href, path)
        classes = ' '.join(c for c in [cls, 'active' if active else ''] if c)
        attrs = f' class="{classes}"' if classes else ''
        cur = ' aria-current="page"' if active else ''
        return f'<a{attrs} href="{href}"{cur}>{_e(label)}</a>'

    main_links = ''.join(link(l, h) for l, h in NAV)
    menu_links = ''.join(link(l, h) for l, h in NAV + MENU_EXTRA)
    return (
        f'{HEADER_START}'
        '<header class="site-header">'
        '<div class="site-shell wide header-inner">'
        '<a class="site-logo" href="/" aria-label="Concerto home">'
        '<img src="/img/lockup.png" alt="Concerto" width="250" height="52"></a>'
        f'<nav class="site-nav" aria-label="Main">{main_links}</nav>'
        '<div class="header-actions">'
        '<a class="header-text-link" href="/search">Search</a>'
        f'<a class="header-cta" href="{APP}" target="_blank" rel="noopener">Get the App</a>'
        '<button class="menu-btn" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="site-menu">'
        '<span class="menu-bar"></span><span class="menu-bar"></span></button>'
        '</div></div>'
        f'<nav class="mobile-nav" id="site-menu" aria-label="Menu" hidden>'
        f'<div class="site-shell mobile-nav-inner">{menu_links}'
        f'<a class="header-cta" href="{APP}" target="_blank" rel="noopener">Get the App</a>'
        '</div></nav>'
        '</header>'
        f'{HEADER_END}'
    )


def footer_html():
    cols = [
        ('Concerto', [('How It Works', '/your-night'), ('Concerto+', '/premium'), ('AI Bag Check', '/bagcheck'),
                      ('Get the App', APP)]),
        ('Library', [('Venues', '/venues'), ('Tours', '/tours'), ('Setlists', '/setlists'),
                     ('Near Me', '/near-me'), ('Search', '/search')]),
        ('Company', [('About', '/about'), ('Press', '/press'), ('Investors', '/investors'),
                     ('Creators', '/creators'), ('Contact', '/contact')]),
        ('Partners & Help', [('Partners', '/partners'), ('Partner Console', '/console/'),
                             ('Help Center', '/help'), ('FAQ', '/faq')]),
    ]

    def col(title, items):
        links = ''.join(
            f'<a href="{h}"{" target=_blank rel=noopener" if h.startswith("http") else ""}>{_e(l)}</a>'
            for l, h in items)
        return f'<div class="footer-col"><h3>{title}</h3>{links}</div>'

    return (
        f'{FOOTER_START}'
        '<footer class="site-footer">'
        '<div class="site-shell footer-top">'
        '<div class="footer-brand">'
        '<img src="/img/lockup.png" alt="Concerto" width="250" height="52">'
        '<p class="footer-kicker">From the Concert to the City®</p>'
        '<h2>One show. One connected night.</h2>'
        '<p>Concerto connects the concert, venue, and city around it with trusted information and a plan that travels with you.</p>'
        f'<a class="footer-app" href="{APP}" target="_blank" rel="noopener">Get Concerto for iPhone</a>'
        '</div>'
        f'<div class="footer-nav">{"".join(col(t, i) for t, i in cols)}</div>'
        '</div>'
        '<div class="site-shell footer-bottom">'
        '<span>© 2026 Concerto LLC. Independent from artists, venues, teams, and promoters.</span>'
        '<div class="footer-bottom-links">'
        '<a href="https://instagram.com/theconcertoapp" target="_blank" rel="noopener">Instagram</a>'
        '<a href="https://www.tiktok.com/@theconcertoapp" target="_blank" rel="noopener">TikTok</a>'
        '<a href="https://www.youtube.com/@theconcertoapp" target="_blank" rel="noopener">YouTube</a>'
        '<a href="/privacy">Privacy</a><a href="/terms">Terms</a>'
        '</div></div>'
        '</footer>'
        f'{FOOTER_END}'
    )


SCREENS_DIR = 'img/product/screens'


def product_screen(name):
    """Path to a cropped app capture, resolved through img/product/screens/manifest.json
    (content-hashed filenames, so a replaced capture is a new URL and never served stale).
    Falls back to the venue screen, then home, when a feature has no capture yet."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    try:
        manifest = json.loads((root / SCREENS_DIR / 'manifest.json').read_text())
    except Exception:
        manifest = {}
    for candidate in (name, 'venue', 'home'):
        if candidate in manifest:
            return f'/{SCREENS_DIR}/{manifest[candidate]}'
    return f'/{SCREENS_DIR}/{name}.webp'


PHOTO_DIR = 'img/photo'


def photo_slot(name, alt, cls='photo-band'):
    """Editorial photograph slot. Drop img/photo/<name>.jpg (or .webp) in place and
    rerun the build; until the file exists the slot renders nothing, so no page
    ever shows an empty placeholder."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for ext in ('webp', 'jpg', 'jpeg', 'png'):
        f = root / PHOTO_DIR / f'{name}.{ext}'
        if f.exists():
            return f'<figure class="{cls}"><img src="/{PHOTO_DIR}/{name}.{ext}" alt="{_e(alt)}" loading="lazy" decoding="async"></figure>'
    return ''


def app_link(kind, slug, label='Open in Concerto', cls='btn-primary'):
    """Deep link that opens the app on this venue/tour when installed, else the App Store.
    Safari will not fire a universal link to the page you are already on, so the site
    tries the concerto:// scheme first (js/public-v6.js handles the fallback). The App
    Store fallback carries a kind-specific campaign tag (website-venue / website-tour)
    so App Store Connect shows which page type actually drives installs."""
    store_url = app_link_campaign(f'website-{kind}') if kind in ('venue', 'tour') else APP
    return (f'<a class="{cls}" href="{store_url}" data-app-link="concerto://{kind}/{_e(slug)}" '
            f'data-web-link="{SITE}/{kind}/{_e(slug)}" rel="noopener">{_e(label)}</a>')


def smart_banner(kind=None, slug=None):
    arg = f', app-argument=concerto://{kind}/{slug}' if kind and slug else ''
    return f'<meta name="apple-itunes-app" content="app-id=6744903414{arg}">'


def page_end():
    return footer_html() + '<script src="/js/public-v6.js" defer></script></body></html>'
