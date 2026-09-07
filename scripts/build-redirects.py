#!/usr/bin/env python3
"""Regenerate the managed block in _redirects: every .html file gets a forced 301
to its canonical extensionless route, so Google never sees two URLs for one page.
Netlify serves a static file before any unforced rule, which is why these need '!'.
Run after the page generators (the push script does)."""
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
START='# ── BEGIN generated: .html -> canonical (scripts/build-redirects.py) ──'
END='# ── END generated ──'
NOINDEX_UTILITY={'account','plan','settings','search','404','partners-thank-you','contact-thank-you'}
lines=['/index.html / 301!']
for d in ['.','venue','tour','setlist']:
    for f in sorted((ROOT/d).glob('*.html')):
        stem=f.stem
        if d=='.' and (stem=='index' or stem in NOINDEX_UTILITY or stem.startswith('[')): continue
        if stem.startswith('['): continue
        route='/'+stem if d=='.' else f'/{d}/{stem}'
        if d=='.' and stem.startswith('partner-'): route='/partners/'+stem[len('partner-'):]
        lines.append(f'/{stem}.html {route} 301!' if d=='.' else f'/{d}/{stem}.html {route} 301!')
block='\n'.join([START]+lines+[END])
s=(ROOT/'_redirects').read_text()
if START in s: s=re.sub(re.escape(START)+r'.*?'+re.escape(END),block,s,flags=re.S)
else: s=s.replace('# ── Concerto public web architecture',block+'\n\n# ── Concerto public web architecture',1)
(ROOT/'_redirects').write_text(s)
print(f'_redirects: {len(lines)} .html -> canonical rules')
