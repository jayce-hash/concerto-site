#!/usr/bin/env python3
"""Concerto venue crawler, version 2: finds what each venue's OWN website says about the
info sections Concerto still hasn't confirmed.

It collects evidence only and never edits venue_info.json. Compared with version 1 it:
  - starts from each venue's official website, its sitemap, and the usual page names
    (FAQ, A-Z guide, plan your visit, accessibility, parking, box office...), not only the links on file;
  - opens blocked or JavaScript-built pages in a real browser (--js), which most 403s and empty pages need;
  - reads PDF guides (A-Z guides are often PDFs) when pypdf is installed;
  - reads FAQ question-and-answer pairs and accordions, not just paragraphs;
  - opens the most promising pages first, up to --pages per venue;
  - can stop and pick up where it left off (--resume).

Polite by design: obeys robots.txt, waits between requests, and stays on the venue's own sites.

Setup (once):
  python3 -m pip install requests beautifulsoup4 playwright pypdf
  python3 -m playwright install chromium

Run (from the concerto-website folder):
  python3 venue_crawl2.py --js                 # every venue with an unconfirmed section
  python3 venue_crawl2.py --js --resume        # continue a run that stopped
  python3 venue_crawl2.py --js --venues chase-center,united-center
  python3 venue_crawl2.py --js --section rideshare

Output: venue-evidence-v2.jsonl (send this to Claude) and venue-evidence-v2.csv (to skim).
"""
import argparse, csv, io, json, re, sys, time
from collections import Counter
from urllib.parse import urljoin, urlparse, urldefrag
from urllib import robotparser

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit('Missing tools. Run:  python3 -m pip install requests beautifulsoup4 playwright pypdf')
try:
    import warnings; warnings.filterwarnings('ignore')
except Exception:
    pass

UA = 'ConcertoVenueResearch/2.0 (+https://concertocity.com; support@concertocity.com)'
SECTIONS = ['bagPolicy', 'parking', 'rideshare', 'concessions', 'accessibility', 'reEntry', 'ticketPickup', 'gates']
TOPICS = {
    'rideshare': r'\b(uber|lyft|bolt|ride ?share|ride-share|rideshare|ride-?hail|taxis?|cabs?|taxi rank|pick[- ]?up (zone|area|location|point)|drop[- ]?off (zone|area|location|point)|passenger drop)\b',
    'parking': r'\b(parking|car park|park(ing)? (lot|garage|deck)|valet|spothero|parkwhiz|ada parking|accessible parking)\b',
    'reEntry': r'\b(re-?entry|re-?enter|re-?admission|readmission|re-?admittance|pass[- ]?outs?|leave and (return|come back)|in-and-outs?|ins? and outs?|exit and re-?enter)\b',
    'ticketPickup': r'\b(will[- ]call|box office|ticket office|ticket window|ticket counter|ticket centre|ticket center|ticket pick ?up|mobile (ticket|entry)|digital tickets?|print(ed)? tickets?)\b',
    'gates': r'\b(doors (will )?open|gates (will )?open|door times?|entry times?|venue opens|entrances?|entry gate|gate [a-z0-9]{1,2}\b|door [a-z0-9]{1,2}\b|entry point|turnstiles?)\b',
    'accessibility': r'\b(ada|accessible|accessibility|wheelchair|assistive listening|hearing loop|service (animal|dog)s?|sensory|disabilit(y|ies)|mobility)\b',
    'concessions': r'\b(concessions?|food and (drink|beverage)s?|food & (drink|beverage)s?|cashless|outside food|refillable|water bottles?|refill station|bars? and restaurants?)\b',
    'bagPolicy': r'\b(bag policy|clear bags?|bags? (up to|no larger|must be|larger than|bigger than)|backpacks?|rucksacks?|purses?|clutch(es)?|fanny packs?|belt bags?)\b',
}
PAGE_HINTS = re.compile(r'(faq|a-?z|az-guide|guide|plan[- ]?your[- ]?(visit|trip|night)|visit|visitor|guest|getting[- ]?(here|there)|directions|transport|travel|parking|rideshare|uber|lyft|taxi|arrival|know[- ]?before|before[- ]?you[- ]?go|accessib|ada|disab|box[- ]?office|ticket[- ]?(info|office)|will[- ]?call|policies|policy|rules|security|bag|venue[- ]?info|info|help|food|drink|dining|concession|entry|entrance|doors)', re.I)
SKIP = re.compile(r'\.(jpg|jpeg|png|gif|webp|svg|mp4|mp3|zip|ics|css|js)(\?|$)|/(events?|calendar|shop|store|careers|jobs|press|news|blog|privacy|cookie|terms-of-use|login|account|cart)(/|$)|mailto:|tel:', re.I)
COMMON_PATHS = ['faq', 'faqs', 'a-z-guide', 'az-guide', 'plan-your-visit', 'visit', 'know-before-you-go', 'guest-services',
                'accessibility', 'ada', 'parking', 'directions', 'getting-here', 'box-office', 'venue-info', 'policies']
NOT_VENUE_HOSTS = ('ticketmaster.', 'livenation.', 'axs.com', 'seatgeek.', 'stubhub.', 'vividseats.', 'instagram.com',
                   'facebook.com', 'twitter.com', 'x.com', 'tiktok.com', 'youtube.com', 'wikipedia.org', 'google.', 'eventbrite.',
                   'dice.fm', 'songkick.', 'bandsintown.', 'tripadvisor.', 'yelp.')


def host(url):
    h = (urlparse(url).hostname or '').lower()
    return h[4:] if h.startswith('www.') else h


def on_sites(url, hosts):
    h = host(url)
    return any(h == x or h.endswith('.' + x) for x in hosts)


def hint_score(url, label=''):
    path = urlparse(url).path.lower()
    s = len(PAGE_HINTS.findall(path)) * 2 + len(PAGE_HINTS.findall(label or ''))
    if re.search(r'faq|a-?z|know-before|plan-your-visit|guest', path): s += 3
    if path.endswith('.pdf'): s += 1
    return s


class Fetcher:
    def __init__(self, delay, use_js):
        self.s = requests.Session()
        self.s.headers.update({'User-Agent': UA, 'Accept-Language': 'en'})
        self.delay, self.last, self.robots = delay, 0.0, {}
        self.browser = None
        if use_js:
            try:
                from playwright.sync_api import sync_playwright
                self._pw = sync_playwright().start()
                self.browser = self._pw.chromium.launch()
                self.ctx = self.browser.new_context(locale='en-US')
            except Exception as e:
                print(f'  (Browser unavailable: {e}. Run: python3 -m playwright install chromium)')

    def allowed(self, url):
        p = urlparse(url); root = f'{p.scheme}://{p.netloc}'
        if root not in self.robots:
            rp = robotparser.RobotFileParser()
            try:
                r = self.s.get(root + '/robots.txt', timeout=10)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except Exception:
                rp.parse([])
            self.robots[root] = rp
        return self.robots[root].can_fetch(UA, url)

    def sitemaps(self, root):
        rp = self.robots.get(root)
        found = list(getattr(rp, 'site_maps', lambda: None)() or []) if rp else []
        return found or [root + '/sitemap.xml']

    def wait(self):
        w = self.delay - (time.time() - self.last)
        if w > 0: time.sleep(w)
        self.last = time.time()

    def get_raw(self, url, timeout=20):
        self.wait()
        try:
            return self.s.get(url, timeout=timeout), None
        except Exception as e:
            return None, f'error: {type(e).__name__}'

    def browse(self, url):
        if not self.browser: return None
        self.wait()
        try:
            page = self.ctx.new_page()
            resp = page.goto(url, wait_until='domcontentloaded', timeout=30000)
            if resp is not None and resp.status >= 400:
                page.close(); return None
            try: page.wait_for_load_state('networkidle', timeout=8000)
            except Exception: pass
            # Open accordions and FAQ toggles so their answers are in the page.
            try:
                page.evaluate("""() => { document.querySelectorAll('details').forEach(d => d.open = true);
                  document.querySelectorAll('[aria-expanded="false"]').forEach((b, i) => { if (i < 80) try { b.click() } catch (e) {} }); }""")
                page.wait_for_timeout(600)
            except Exception: pass
            html = page.content(); page.close()
            return html
        except Exception:
            return None

    def get(self, url):
        """Returns (kind, content, status). kind is 'html' or 'pdf'."""
        if not self.allowed(url):
            return None, None, 'blocked by robots.txt'
        r, err = self.get_raw(url)
        if r is not None and r.status_code == 200:
            ctype = r.headers.get('content-type', '')
            if 'pdf' in ctype or url.lower().split('?')[0].endswith('.pdf'):
                return 'pdf', r.content, 'ok'
            if 'html' in ctype:
                html = r.text
                if self.browser and len(BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)) < 1500:
                    html = self.browse(url) or html
                return 'html', html, 'ok'
            return None, None, f'HTTP 200 {ctype.split(";")[0]}'
        status = err or f'HTTP {r.status_code}'
        if r is not None and r.status_code == 404:
            return None, None, status
        # Blocked (403/429/503), TLS trouble, or a timeout: a real browser usually gets through.
        html = self.browse(url)
        if html:
            return 'html', html, f'ok via browser ({status})'
        return None, None, status

    def close(self):
        if self.browser:
            self.browser.close(); self._pw.stop()


def pdf_blocks(data):
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    try:
        text = '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(data)).pages[:40])
    except Exception:
        return []
    blocks = [re.sub(r'\s+', ' ', b).strip() for b in re.split(r'\n\s*\n|\n(?=[A-Z][A-Z &/-]{3,}\n)', text)]
    return [{'heading': '', 'text': b} for b in blocks if 25 <= len(b) <= 1500]


def html_blocks(html):
    """Text blocks with their nearest heading, plus FAQ question/answer pairs."""
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'form', 'svg']):
        t.decompose()
    out = []
    for el in soup.find_all(['p', 'li', 'td', 'dd', 'div', 'span', 'section']):
        if el.name in ('div', 'section', 'span') and el.find(['p', 'li', 'div', 'table', 'section', 'ul']):
            continue
        text = re.sub(r'\s+', ' ', el.get_text(' ', strip=True))
        if 25 <= len(text) <= 1500:
            h = el.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'dt', 'summary', 'button'])
            out.append({'heading': re.sub(r'\s+', ' ', h.get_text(' ', strip=True))[:160] if h else '', 'text': text})
    # FAQ pairs: a question element followed by its answer.
    for q in soup.find_all(['dt', 'summary', 'h3', 'h4', 'h5', 'button']):
        qt = re.sub(r'\s+', ' ', q.get_text(' ', strip=True))
        if not (8 <= len(qt) <= 200): continue
        ans = q.find_next_sibling() if q.name != 'summary' else q.parent
        if ans is None and q.parent is not None: ans = q.parent.find_next_sibling()
        if ans is None: continue
        at = re.sub(r'\s+', ' ', ans.get_text(' ', strip=True))
        if q.name == 'summary': at = at[len(qt):].strip()
        if 20 <= len(at) <= 1500:
            out.append({'heading': qt[:160], 'text': at})
    return out


def links(html, base, hosts):
    soup = BeautifulSoup(html, 'html.parser')
    found = {}
    for a in soup.find_all('a', href=True):
        url = urldefrag(urljoin(base, a['href']))[0]
        if not url.startswith('http') or not on_sites(url, hosts) or SKIP.search(url):
            continue
        label = a.get_text(' ', strip=True)
        sc = hint_score(url, label)
        if sc > 0:
            found[url] = max(found.get(url, 0), sc)
    return found


def sitemap_urls(f, root, hosts, limit=400):
    out, seen, todo = {}, set(), f.sitemaps(root)[:3]
    while todo and len(seen) < 6:
        sm = todo.pop(0)
        if sm in seen or not f.allowed(sm): continue
        seen.add(sm)
        r, _ = f.get_raw(sm, timeout=15)
        if r is None or r.status_code != 200: continue
        locs = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', r.text)
        for u in locs:
            if u.endswith('.xml') or 'sitemap' in u.lower():
                if len(todo) < 6: todo.append(u)
            elif on_sites(u, hosts) and not SKIP.search(u):
                sc = hint_score(u)
                if sc > 0: out[u] = sc
        if len(out) > limit: break
    return out


def official_hosts(v):
    hs = Counter()
    for k in SECTIONS:
        u = (v.get(k) or {}).get('officialLink') or ''
        if u.startswith('http') and not any(b in host(u) for b in NOT_VENUE_HOSTS):
            hs[host(u)] += 2 if (v.get(k) or {}).get('verificationStatus') == 'official_source_confirmed' else 1
    return [h for h, _ in hs.most_common(3)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', default='data/venue_info.json')
    ap.add_argument('--section', default='all', choices=SECTIONS + ['all'])
    ap.add_argument('--venues', default='', help='comma-separated slugs')
    ap.add_argument('--limit', type=int, default=0, help='how many venues (0 = all)')
    ap.add_argument('--pages', type=int, default=15, help='most pages to open per venue')
    ap.add_argument('--delay', type=float, default=1.5, help='seconds between requests')
    ap.add_argument('--js', action='store_true', help='use a real browser for blocked or JavaScript pages (recommended)')
    ap.add_argument('--resume', action='store_true', help='skip venues already in the output file')
    ap.add_argument('--out', default='venue-evidence-v2')
    args = ap.parse_args()

    info = json.load(open(args.data))
    keys = SECTIONS if args.section == 'all' else [args.section]
    todo = lambda v: [k for k in keys if isinstance(v.get(k), dict) and v[k].get('verificationStatus') != 'official_source_confirmed']
    picks = [s.strip() for s in args.venues.split(',') if s.strip()]
    slugs = [s for s in picks if s in info] if picks else [s for s, v in info.items() if isinstance(v, dict) and todo(v)]
    if args.limit: slugs = slugs[:args.limit]
    done = set()
    if args.resume:
        try:
            done = {json.loads(l)['venue'] for l in open(args.out + '.jsonl')}
        except FileNotFoundError:
            pass
    slugs = [s for s in slugs if s not in done]
    print(f'{len(slugs)} venues to check ({len(done)} already done), sections: {args.section}')

    f = Fetcher(args.delay, args.js)
    mode = 'a' if args.resume else 'w'
    stats = Counter()
    with open(args.out + '.jsonl', mode) as jf, open(args.out + '.csv', mode, newline='') as cf:
        w = csv.writer(cf)
        if mode == 'w': w.writerow(['venue', 'name', 'section', 'page', 'heading', 'passage'])
        for i, slug in enumerate(slugs, 1):
            v = info[slug]
            needed = todo(v) or keys
            hosts = official_hosts(v)
            if not hosts:
                stats['no official website on file'] += 1
                print(f'[{i}/{len(slugs)}] {v.get("name")}: no official website on file'); continue
            # Candidate pages, best first: links on file, sitemap matches, usual page names, then what pages link to.
            cand = {}
            for k in SECTIONS:
                u = (v.get(k) or {}).get('officialLink')
                if u and on_sites(u, hosts): cand[u] = max(cand.get(u, 0), 5 + hint_score(u))
            roots = {}
            for k in SECTIONS:
                u = (v.get(k) or {}).get('officialLink') or ''
                if u.startswith('http') and on_sites(u, hosts):
                    pu = urlparse(u); roots.setdefault(host(u), f'{pu.scheme}://{pu.netloc}')
            for h in hosts[:2]:
                root = roots.get(h, f'https://{h}')
                cand.setdefault(root + '/', 4)
                f.allowed(root + '/')
                for u, sc in sitemap_urls(f, root, hosts).items(): cand[u] = max(cand.get(u, 0), sc + 2)
                for p in COMMON_PATHS: cand.setdefault(f'{root}/{p}', 1)
            visited, found, notes = [], [], []
            tried, opened = set(), 0
            while cand and opened < args.pages and len(tried) < args.pages * 3:
                url = max(cand, key=cand.get); cand.pop(url)
                if url.rstrip('/') in tried: continue
                tried.add(url.rstrip('/'))
                kind, content, status = f.get(url)
                if not content:
                    if not status.startswith('HTTP 404'): notes.append(f'{url}: {status}')
                    continue
                visited.append(url); opened += 1
                if status != 'ok': notes.append(f'{url}: {status}')
                blocks = pdf_blocks(content) if kind == 'pdf' else html_blocks(content)
                seen = set()
                for b in blocks:
                    key = b['text'].lower()[:200]
                    if key in seen: continue
                    seen.add(key)
                    for k in needed:
                        if re.search(TOPICS[k], b['heading'] + ' ' + b['text'], re.I):
                            found.append({'section': k, 'url': url, **b})
                if kind == 'html':
                    for u, sc in links(content, url, hosts).items():
                        if u not in visited: cand[u] = max(cand.get(u, 0), sc)
            per, kept, seenp = Counter(), [], set()
            for p in sorted(found, key=lambda p: -hint_score(p['url'], p['heading'])):
                key = (p['section'], p['text'][:200])
                if key in seenp or per[p['section']] >= 10: continue
                seenp.add(key); per[p['section']] += 1; kept.append(p)
            rec = {'venue': slug, 'name': v.get('name'), 'sections': needed, 'officialSites': hosts,
                   'current': {k: v.get(k) for k in needed}, 'pagesChecked': visited, 'notes': notes, 'evidence': kept}
            jf.write(json.dumps(rec, ensure_ascii=False) + '\n'); jf.flush()
            for p in kept:
                w.writerow([slug, v.get('name'), p['section'], p['url'], p['heading'], p['text']])
            got = sorted({p['section'] for p in kept})
            stats['with evidence' if kept else 'nothing found'] += 1
            print(f'[{i}/{len(slugs)}] {v.get("name")}: {len(kept)} passages for {len(got)}/{len(needed)} sections from {len(visited)} pages')
    f.close()
    print('\nDone.', dict(stats))
    print(f'Evidence: {args.out}.jsonl (send this to Claude) and {args.out}.csv (to skim).')


if __name__ == '__main__':
    main()
