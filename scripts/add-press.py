#!/usr/bin/env python3
"""Add an article about Concerto to the press page.

  python3 scripts/add-press.py "Hypebot" "Headline of the article" "https://..." 2026-10-14

Newest articles show first. Push the site afterward to publish it."""
import json, sys, datetime
from pathlib import Path
if len(sys.argv) != 5:
    sys.exit(__doc__)
outlet, title, url, date = (a.strip() for a in sys.argv[1:])
if not url.startswith('https://'): sys.exit('The link must start with https://')
datetime.date.fromisoformat(date)  # must be YYYY-MM-DD
f = Path(__file__).resolve().parent.parent / 'data' / 'press.json'
items = json.loads(f.read_text()) if f.exists() else []
items = [i for i in items if i['url'] != url] + [{'outlet': outlet, 'title': title, 'url': url, 'date': date}]
items.sort(key=lambda i: i['date'], reverse=True)
f.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
print(f'Added: {outlet} - {title} ({date}). {len(items)} article(s) on the press page.')
