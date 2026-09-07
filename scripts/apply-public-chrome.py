#!/usr/bin/env python3
"""Stamp the shared header and footer into hand-written public pages.

Generated pages (index, hubs, venue/tour/setlist detail, feature pages) get
their chrome from the generators. Company, partner, legal, and support pages
are written by hand, so this script:

  - removes legacy navigation and footers (nav.nav, .v2nav, .v2menu, footer)
  - removes the retired global-footer.css / global-footer.js includes
  - fixes literal "\\n" text that had leaked into a few <head> blocks
  - makes sure public-v6.css, the fonts, and analytics.js are in <head>
  - inserts (or refreshes) the header right after <body> and the footer
    right before the public-v6.js script tag, between marker comments so
    it is safe to run again and again

Run it after editing any of the pages listed in PAGES, or after changing
public_chrome.py, and both generators will already be in sync.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from public_chrome import header_html, footer_html, HEAD_ASSETS, HEADER_START, HEADER_END, FOOTER_START, FOOTER_END

PAGES = {
    'partners-thank-you.html': '/partners/thank-you', 'contact-thank-you.html': '/contact/thank-you', 'help.html': '/help',
    'privacy.html': '/privacy', 'terms.html': '/terms', 'search.html': '/search', '404.html': '/404',
}
# Expo utility pages are not public-web templates; only their broken head text is repaired.
REPAIR_ONLY = ['account.html', 'plan.html', 'settings.html']


def strip_legacy(body):
    body = re.sub(r'<nav[^>]*class="[^"]*\bnav\b[^"]*"[^>]*>.*?</nav>\s*', '', body, flags=re.S)
    body = re.sub(r'<nav[^>]*class="[^"]*\bv2nav\b[^"]*"[^>]*>.*?</nav>\s*', '', body, flags=re.S)
    body = re.sub(r'<div[^>]*class="[^"]*\bv2menu\b[^"]*"[^>]*>.*?</div>\s*', '', body, flags=re.S)
    body = re.sub(r'<footer\b(?![^>]*site-footer).*?</footer>\s*', '', body, flags=re.S)
    body = re.sub(rf'{re.escape(HEADER_START)}.*?{re.escape(HEADER_END)}', '', body, flags=re.S)
    body = re.sub(rf'{re.escape(FOOTER_START)}.*?{re.escape(FOOTER_END)}', '', body, flags=re.S)
    body = re.sub(r'<header class="site-header">.*?</header>\s*', '', body, flags=re.S)
    body = re.sub(r'<footer class="site-footer">.*?</footer>\s*', '', body, flags=re.S)
    return body


def fix_head(head):
    head = head.replace('\\n', '')
    head = re.sub(r'<link[^>]*global-footer\.css[^>]*>\s*', '', head)
    head = re.sub(r'<script[^>]*src="/?analytics\.js"[^>]*>\s*</script>\s*', '', head)
    # Fonts + public-v6.css + analytics, once, in a known order.
    head = re.sub(r'<link[^>]*rel="preconnect"[^>]*>\s*', '', head)
    head = re.sub(r'<link[^>]*fonts\.googleapis\.com/css2[^>]*>\s*', '', head)
    head = re.sub(r'<link[^>]*href="/css/public-v6\.css"[^>]*>\s*', '', head)
    return head + HEAD_ASSETS


def process(path, canonical, repair_only=False):
    p = ROOT / path
    if not p.exists():
        return False
    s = p.read_text()
    m = re.search(r'<head[^>]*>(.*?)</head>', s, flags=re.S)
    if not m:
        return False
    head = m.group(1)
    if repair_only:
        h = head.replace('\\n', '')
        h = re.sub(r'<link[^>]*global-footer\.css[^>]*>\s*', '', h)
        s = s[:m.start(1)] + h + s[m.end(1):]
        s = re.sub(r'<script[^>]*src="/?js/global-footer\.js"[^>]*>\s*</script>\s*', '', s)
        p.write_text(s)
        return True
    s = s[:m.start(1)] + fix_head(head) + s[m.end(1):]

    s = re.sub(r'<script[^>]*src="/?js/global-footer\.js"[^>]*>\s*</script>\s*', '', s)
    bm = re.search(r'<body[^>]*>', s)
    if not bm:
        return False
    if 'public-site' not in bm.group(0):
        s = s[:bm.start()] + bm.group(0).replace('<body', '<body class="public-site"', 1) + s[bm.end():]
        bm = re.search(r'<body[^>]*>', s)
    body_start = bm.end()
    body = strip_legacy(s[body_start:])
    # Drop the inline legacy nav script on privacy/terms; keep the FAQ accordion behaviour if present.
    body = re.sub(r"<script>\s*\(function\(\)\{\s*/\* nav hairline on scroll \*/.*?\}\)\(\);\s*</script>\s*", '', body, flags=re.S)
    body = re.sub(r'<script[^>]*src="/js/public-v6\.js"[^>]*>\s*</script>\s*', '', body)
    body = re.sub(r'</body>\s*</html>\s*$', '', body, flags=re.S)
    tail = footer_html() + '<script src="/js/public-v6.js" defer></script></body></html>\n'
    s = s[:body_start] + header_html(canonical) + body.rstrip() + tail
    p.write_text(s)
    return True


if __name__ == '__main__':
    done = [f for f, c in PAGES.items() if process(f, c)]
    repaired = [f for f in REPAIR_ONLY if process(f, '', repair_only=True)]
    print(f'Stamped header/footer into {len(done)} pages; repaired head text in {len(repaired)} app pages.')
