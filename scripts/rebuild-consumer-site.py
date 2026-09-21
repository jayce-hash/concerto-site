"""Regenerate consumer pages, then refresh shared chrome on all public pages."""
import re
import subprocess
import sys
from pathlib import Path
from public_chrome import header_html, footer_html, HEADER_START, HEADER_END, FOOTER_START, FOOTER_END
from night_components import component

root = Path(__file__).resolve().parent.parent
for generator in ('build-public-site.py', 'build-public-features.py', 'build-company-pages.py', 'build-support-pages.py'):
    subprocess.run([sys.executable, str(root / 'scripts' / generator)], check=True, cwd=root)
pages = list(root.glob('*.html'))
for directory in ('venue', 'tour', 'setlist'):
    pages.extend((root / directory).glob('*.html'))
for path in pages:
    source = path.read_text()
    if HEADER_START not in source:
        continue
    canonical = re.search(r'<link rel="canonical" href="https://concertocity.com([^"]*)"', source)
    route = canonical.group(1) if canonical else '/' + path.stem
    source = re.sub(re.escape(HEADER_START) + r'.*?' + re.escape(HEADER_END), lambda _: header_html(route), source, flags=re.S)
    source = re.sub(re.escape(FOOTER_START) + r'.*?' + re.escape(FOOTER_END), lambda _: footer_html(), source, flags=re.S)
    # No screenshots on the public site: every app capture becomes a component built
    # from the same data the app reads. Matches the figure, the device frame, or a bare img.
    def _swap(m):
        return component(m.group('key'))
    source = re.sub(r'<figure class="product-capture">\s*<img src="/img/product/screens/(?P<key>[a-z-]+)\.[0-9a-f]+\.webp"[^>]*>\s*(?:<figcaption>.*?</figcaption>)?\s*</figure>', _swap, source, flags=re.S)
    source = re.sub(r'<div class="device-stage">\s*<div class="device">\s*<div class="iphone-screen">\s*<img src="/img/product/screens/(?P<key>[a-z-]+)\.[0-9a-f]+\.webp"[^>]*>\s*</div>\s*</div>\s*(?:<div class="device-badge">.*?</div>\s*)?</div>', _swap, source, flags=re.S)
    source = re.sub(r'<div class="device">\s*<div class="iphone-screen">\s*<img src="/img/product/screens/(?P<key>[a-z-]+)\.[0-9a-f]+\.webp"[^>]*>\s*</div>\s*</div>', _swap, source, flags=re.S)
    source = re.sub(r'<img src="/img/product/screens/(?P<key>[a-z-]+)\.[0-9a-f]+\.webp"[^>]*>', _swap, source)
    if 'id="main-content"' not in source:
        source = re.sub(r'<main\b', '<main id="main-content"', source, count=1)
    path.write_text(source)
print('Consumer templates and shared public chrome rebuilt.')
