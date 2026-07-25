#!/usr/bin/env python3
"""
One-time rollout: adds Apple's Smart App Banner meta tag to every HTML
page on the site that doesn't already have it. Safari then shows a
native "Open in the Concerto app / GET" banner at the top of every
page -- the single highest-leverage app-download surface the site has,
because it rides on organic search traffic you already earn.

Run from the site root:   python3 add_smart_banner.py
Idempotent: safe to run again anytime; already-tagged pages are skipped.
Future pages: build_static.py now also injects the tag, so regenerated
venue/tour pages stay covered automatically.
"""
import pathlib, re

META = '  <meta name="apple-itunes-app" content="app-id=6744903414">\n'
root = pathlib.Path('.')
touched = skipped = 0
for p in sorted(root.rglob('*.html')):
    if 'node_modules' in p.parts:
        continue
    src = p.read_text(encoding='utf-8', errors='ignore')
    if 'apple-itunes-app' in src:
        skipped += 1
        continue
    m = re.search(r'<meta name="viewport"[^>]*>\n?', src)
    if not m:
        m = re.search(r'<head[^>]*>\n?', src)
    if not m:
        skipped += 1
        continue
    idx = m.end()
    p.write_text(src[:idx] + META + src[idx:], encoding='utf-8')
    touched += 1
print(f'smart banner added to {touched} pages, {skipped} skipped (already tagged or no head)')
