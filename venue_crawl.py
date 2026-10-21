#!/usr/bin/env python3
"""Concerto venue crawler: finds what each venue's OWN website says about one topic.

It collects evidence only. It never edits venue_info.json. For each venue it:
  1. starts from the official links already in venue_info.json,
  2. follows a few likely pages on that same website (parking, getting here, FAQ, accessibility...),
  3. saves the paragraphs that mention the topic, each with the exact page it came from.

You (or Claude) then turn that evidence into Concerto's short answers and review them.

Polite by design: it obeys each site's robots.txt, waits between requests, visits at most
--pages pages per venue, and identifies itself as Concerto.

Usage (from the concerto-website folder):
  python3 venue_crawl.py --section rideshare --limit 25
  python3 venue_crawl.py --section rideshare --limit 25 --js     # also render JavaScript-heavy pages
  python3 venue_crawl.py --section all --limit 0                  # every venue, every unconfirmed section, one visit each

Output: venue-evidence-<section>.jsonl and venue-evidence-<section>.csv in the current folder.
"""
import argparse, csv, json, re, sys, time
from collections import Counter
from urllib.parse import urljoin, urlparse, urldefrag
from urllib import robotparser

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit('Missing tools. Run:  python3 -m pip install requests beautifulsoup4')

UA = 'ConcertoVenueResearch/1.0 (+https://concertocity.com; support@concertocity.com)'

# What counts as a mention of each topic, and which pages are worth opening to find it.
TOPICS = {
    'rideshare': r'\b(uber|lyft|ride ?share|ride-share|rideshare|taxi|taxis|cab|pick[- ]?up|drop[- ]?off)\b',
    'parking': r'\b(parking|park(ing)? (lot|garage|deck)|valet|spothero|parkwhiz|ada parking)\b',
    'reEntry': r'\b(re-?entry|re-?enter|readmission|leave and return|in-and-out|in and out)\b',
    'ticketPickup': r'\b(will call|will-call|box office|ticket pick ?up|mobile tickets?|print(ed)? tickets?)\b',
    'gates': r'\b(doors open|gates open|entrance|entry gate|gate [a-z0-9]|door [a-z0-9]|entry point)\b',
    'accessibility': r'\b(ada|accessible|accessibility|wheelchair|assistive listening|service animal|sensory)\b',
    'concessions': r'\b(concessions?|food and (drink|beverage)|bars?|cashless|outside food|refillable|water bottle)\b',
    'bagPolicy': r'\b(bag policy|clear bag|bags? (up to|no larger|must be)|backpacks?|purses?|clutch|fanny pack)\b',
}
PAGE_HINTS = re.compile(r'(getting[- ]?here|directions|transport|parking|rideshare|uber|lyft|plan[- ]?your[- ]?visit|visit|guest|faq|a-?z|know[- ]?before|accessib|arrival|policies|policy|venue[- ]?info|info)', re.I)
SKIP = re.compile(r'\.(jpg|jpeg|png|gif|webp|svg|mp4|zip|ics)(\?|$)|/(tickets?|events?|calendar|shop|store|careers|press|news)(/|$)', re.I)


def host(url):
    h = (urlparse(url).hostname or '').lower()
    return h[4:] if h.startswith('www.') else h


def same_site(a, b):
    ha, hb = host(a), host(b)
    return bool(ha) and (ha == hb or ha.endswith('.' + hb) or hb.endswith('.' + ha))


class Fetcher:
    def __init__(self, delay, use_js):
        self.s = requests.Session()
        self.s.headers.update({'User-Agent': UA, 'Accept-Language': 'en'})
        self.delay = delay
        self.robots = {}
        self.last = 0.0
        self.browser = None
        if use_js:
            try:
                from playwright.sync_api import sync_playwright
                self._pw = sync_playwright().start()
                self.browser = self._pw.chromium.launch()
            except Exception as e:
                print(f'  (JavaScript rendering unavailable: {e}. Continuing without it.)')

    def allowed(self, url):
        root = f'{urlparse(url).scheme}://{urlparse(url).netloc}'
        if root not in self.robots:
            rp = robotparser.RobotFileParser()
            try:
                r = self.s.get(root + '/robots.txt', timeout=10)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except Exception:
                rp.parse([])
            self.robots[root] = rp
        return self.robots[root].can_fetch(UA, url)

    def get(self, url):
        if not self.allowed(url):
            return None, 'blocked by robots.txt'
        wait = self.delay - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.time()
        try:
            r = self.s.get(url, timeout=20)
        except Exception as e:
            return None, f'error: {type(e).__name__}'
        ctype = r.headers.get('content-type', '')
        if r.status_code != 200 or 'html' not in ctype:
            return None, f'HTTP {r.status_code} {ctype.split(";")[0]}'
        html = r.text
        if self.browser and len(BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)) < 600:
            try:
                page = self.browser.new_page(user_agent=UA)
                page.goto(url, wait_until='networkidle', timeout=30000)
                html = page.content()
                page.close()
            except Exception:
                pass
        return html, 'ok'

    def close(self):
        if self.browser:
            self.browser.close()
            self._pw.stop()


def passages(html, pattern):
    """Text blocks that mention the topic, each with a little context. No menus or footers."""
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'form']):
        tag.decompose()
    out, seen = [], set()
    for el in soup.find_all(['p', 'li', 'td', 'dd', 'h2', 'h3', 'h4', 'div']):
        if el.name == 'div' and el.find(['p', 'li', 'div', 'table']):
            continue  # only leaf-ish divs, so text isn't counted twice
        text = re.sub(r'\s+', ' ', el.get_text(' ', strip=True))
        if len(text) < 25 or len(text) > 1200 or not re.search(pattern, text, re.I):
            continue
        key = text.lower()[:160]
        if key in seen:
            continue
        seen.add(key)
        heading = el.find_previous(['h1', 'h2', 'h3', 'h4'])
        out.append({'heading': re.sub(r'\s+', ' ', heading.get_text(' ', strip=True))[:120] if heading else '', 'text': text})
    return out


def candidate_links(html, base, start):
    soup = BeautifulSoup(html, 'html.parser')
    found = []
    for a in soup.find_all('a', href=True):
        url = urldefrag(urljoin(base, a['href']))[0]
        if not url.startswith('http') or not same_site(url, start) or SKIP.search(url):
            continue
        label = (a.get_text(' ', strip=True) or '') + ' ' + url
        if PAGE_HINTS.search(label):
            found.append(url)
    return list(dict.fromkeys(found))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', default='data/venue_info.json')
    ap.add_argument('--section', default='rideshare', choices=sorted(TOPICS) + ['all'])
    ap.add_argument('--limit', type=int, default=25, help='how many venues (0 = all)')
    ap.add_argument('--venues', default='', help='comma-separated venue slugs to run instead')
    ap.add_argument('--all', action='store_true', help='include sections already confirmed (default: only unconfirmed ones)')
    ap.add_argument('--pages', type=int, default=8, help='most pages to open per venue')
    ap.add_argument('--delay', type=float, default=1.5, help='seconds between requests')
    ap.add_argument('--js', action='store_true', help='render JavaScript-heavy pages with Playwright')
    args = ap.parse_args()

    info = json.load(open(args.data))
    every = args.section == 'all'
    def todo(v):
        # The sections this venue still needs: unconfirmed ones (or all of them with --all).
        keys = sorted(TOPICS) if every else [args.section]
        return [k for k in keys if isinstance(v.get(k), dict)
                and (args.all or v[k].get('verificationStatus') != 'official_source_confirmed')]
    picks = [v.strip() for v in args.venues.split(',') if v.strip()]
    if picks:
        slugs = [s for s in picks if s in info]
    else:
        slugs = [s for s, v in info.items() if isinstance(v, dict) and todo(v)]
        if args.limit:
            slugs = slugs[:args.limit]
    print(f'{len(slugs)} venues, section: {args.section}')

    f = Fetcher(args.delay, args.js)
    out_jsonl = f'venue-evidence-{args.section}.jsonl'
    out_csv = f'venue-evidence-{args.section}.csv'
    stats = Counter()
    with open(out_jsonl, 'w') as jf, open(out_csv, 'w', newline='') as cf:
        w = csv.writer(cf)
        w.writerow(['venue', 'name', 'section', 'page', 'heading', 'passage'])
        for i, slug in enumerate(slugs, 1):
            v = info[slug]
            needed = todo(v) or ([args.section] if not every else [])
            pats = {k: TOPICS[k] for k in needed}
            seeds = [(v.get(k) or {}).get('officialLink') for k in needed] + [x.get('officialLink') for x in v.values() if isinstance(x, dict)]
            seeds = [s for s in dict.fromkeys(seeds) if s and s.startswith('http')]
            if not seeds:
                stats['no official link'] += 1
                continue
            start = seeds[0]
            queue = [s for s in seeds if same_site(s, start)] + [s for s in seeds if not same_site(s, start)]
            visited, found, notes = [], [], []
            while queue and len(visited) < args.pages:
                url = queue.pop(0)
                if url in visited:
                    continue
                html, status = f.get(url)
                visited.append(url)
                if not html:
                    notes.append(f'{url}: {status}')
                    continue
                for k, pat in pats.items():
                    for p in passages(html, pat):
                        found.append({'section': k, 'url': url, **p})
                for link in candidate_links(html, url, start):
                    if link not in visited and link not in queue:
                        queue.append(link)
            per = Counter(); kept = []
            for p in found:  # up to 8 passages per section
                if per[p['section']] < 8:
                    per[p['section']] += 1; kept.append(p)
            found = kept
            rec = {'venue': slug, 'name': v.get('name'), 'sections': needed,
                   'current': {k: v.get(k) for k in needed},
                   'pagesChecked': visited, 'notes': notes, 'evidence': found}
            jf.write(json.dumps(rec, ensure_ascii=False) + '\n')
            for p in found:
                w.writerow([slug, v.get('name'), p['section'], p['url'], p['heading'], p['text']])
            stats['with evidence' if found else 'nothing found'] += 1
            print(f'[{i}/{len(slugs)}] {v.get("name")}: {len(found)} passages from {len(visited)} pages')
    f.close()
    print('\nDone.', dict(stats))
    print(f'Evidence: {out_jsonl} (send this to Claude) and {out_csv} (open in Numbers or Excel to skim).')


if __name__ == '__main__':
    main()
