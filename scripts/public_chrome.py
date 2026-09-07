"""Concerto public web chrome: one header, one footer, baked into every page.

Both generators (build-public-site.py, build-public-features.py) and the
stamping script for hand-written pages (apply-public-chrome.py) import this,
so the navigation is real HTML in the initial response on every URL. The JS in
js/public-v6.js only wires up the menu button and never rebuilds the header.
"""
import html

APP = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414'
SITE = 'https://concertocity.com'

NAV = [
    ('Venues', '/venues'),
    ('Tours', '/tours'),
    ('Setlists', '/setlists'),
    ('Near Me', '/near-me'),
    ('Concerto+', '/premium'),
    ('Perks', '/perks'),
    ('Partners', '/partners'),
]
MENU_EXTRA = [('About', '/about'), ('Help', '/help'), ('Search', '/search')]

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
        ('Discover', [('Venues', '/venues'), ('Tours', '/tours'), ('Setlists', '/setlists'),
                      ('Near Me', '/near-me'), ('Perks', '/perks')]),
        ('Product', [('Your Night', '/your-night'), ('Concerto+', '/premium'), ('AI Bag Check', '/bagcheck'),
                     ('Bag policies', '/bags'), ('Parking', '/parking'), ('Get the App', APP)]),
        ('Company', [('About', '/about'), ('Press & Media', '/press'), ('Investors', '/investors'),
                     ('Contact', '/contact')]),
        ('Work With Us', [('Partners', '/partners'), ('Creators', '/creators'),
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
    """Path to a cropped app capture. Falls back to the venue screen when a
    feature does not have its own real capture yet (drop one into
    img/product/source/<name>.png and run scripts/build-product-screens.py)."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for candidate in (name, 'venue', 'home'):
        if (root / SCREENS_DIR / f'{candidate}.webp').exists():
            return f'/{SCREENS_DIR}/{candidate}.webp'
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


def page_end():
    return footer_html() + '<script src="/js/public-v6.js" defer></script></body></html>'
