"""Keep private app utilities out of search after every Expo web sync."""
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
files = [root / (name + '.html') for name in ('account', 'settings', 'plan', 'login', 'signup')]
files += list((root / 'show').glob('*.html'))
for path in files:
    if not path.is_file():
        continue
    source = path.read_text()
    source = re.sub(r'<meta\b(?=[^>]*\bname=[\"\']robots[\"\'])[^>]*>', '', source, flags=re.I)
    source = source.replace('</head>', '<meta name="robots" content="noindex,follow">\n</head>', 1)
    path.write_text(source)
print('Private app utilities marked noindex.')
