"""Concerto public website, V8. Written from scratch on top of the URL list.

Runs after the legacy generators. For every public page it keeps the existing
<head> byte for byte (title, description, canonical, robots, Open Graph, smart
banner, structured data), then writes a new body. Google sees the same pages;
people see a new site. No screenshots and no imitation app UI anywhere: the site
sells with a point of view, real photography of real venues, and the guide itself.
"""
import html, json, re
from pathlib import Path
from public_chrome import header_html, footer_html, app_link, app_link_campaign, HEADER_START, FOOTER_START, FOOTER_END

ROOT = Path(__file__).resolve().parent.parent
def e(v): return html.escape(str(v or ''), quote=True)
VENUES = json.loads((ROOT / 'data/venues.json').read_text())
INFO = json.loads((ROOT / 'data/venue_info.json').read_text())
TOURS = json.loads((ROOT / 'data/tours.json').read_text())
SETS = json.loads((ROOT / 'setlists.json').read_text())
LIVE = {k: v for k, v in SETS.items() if v.get('songs')}
VBY = {v['id']: v for v in VENUES}
N_V, N_T, N_S = len(VENUES), len(TOURS), len(LIVE)
SECTIONS = [('bagPolicy', 'Bag policy', 'bag-policy'), ('gates', 'Entrances and doors', 'entrances'), ('parking', 'Parking', 'parking'),
            ('rideshare', 'Rideshare', 'rideshare'), ('accessibility', 'Accessibility', 'accessibility'), ('concessions', 'Food and drink', 'concessions'),
            ('reEntry', 'Re-entry', 're-entry'), ('ticketPickup', 'Tickets and will call', 'ticket-pickup')]
# Madison Square Garden's file is a watermarked Getty image: never used on the site.
PHOTOS = [('kia-forum', 'Kia-Forum'), ('bridgestone-arena', 'Bridgestone-Arena'),
          ('moody-center', 'Moody-Center'), ('td-garden', 'TD-Garden')]
FEATURED_VENUES = ['american-airlines-center', 'madison-square-garden', 'kia-forum', 'red-rocks-amphitheatre', 'sphere', 'bridgestone-arena',
                   'td-garden', 'united-center', 'moody-center', 'chase-center', 'the-o2', 'sofi-stadium']
STORE = lambda ct: app_link_campaign(ct)
# 37 venues store "USA" and 18 store "UK"; Ticketmaster only understands ISO codes, so tonight's
# lookup on those pages returned nothing. Normalize at the point of use.
ISO = {'USA': 'US', 'UK': 'GB'}

def place(v): return ', '.join(x for x in [v.get('city'), v.get('state') or v.get('country')] if x)
def pretty_date(d):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', d or '')
    if not m: return d or ''
    mon = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(m.group(2)) - 1]
    return f'{mon} {int(m.group(3))}, {m.group(1)}'
def source_label(s):
    src = s.get('source') or {}
    if src.get('eventDate'): return f"Confirmed setlist from {src.get('venue') or 'a recent show'}, {pretty_date(src['eventDate'])}"
    if 'apple music' in (s.get('note') or '').lower(): return f"Official tour playlist (Apple Music), updated {pretty_date(s.get('updated'))}"
    return f"Updated {pretty_date(s.get('updated'))}"
def songs_word(n): return f'{n} song' + ('' if n == 1 else 's')
def first_sentence(t, n=190):
    t = (t or '').strip(); m = re.match(r'(.+?[.!?])(\s|$)', t)
    t = m.group(1) if m else t
    return t if len(t) <= n else t[:n].rsplit(' ', 1)[0] + '…'

# ---------------- shared blocks ----------------
def store_button(ct, label='Download on the App Store', tone='black'):
    # Apple's official badge, unmodified, per the App Store marketing guidelines: black on light
    # backgrounds, white on dark. Never recolored, never below 40px tall, with clear space around it.
    return (f'<a class="c-store" href="{STORE(ct)}" target="_blank" rel="noopener" aria-label="Download Concerto on the App Store">'
            f'<img src="/img/badges/app-store-{tone}.svg" alt="Download on the App Store" width="160" height="53" loading="eager"></a>')

def close(title='See you at the show.', ct='website-close'):
    return (f'<section class="c-close" data-reveal><div class="c-wrap">'
            '<img class="c-appicon" src="/img/app-icon-256.png" width="96" height="96" alt="Concerto app icon" loading="lazy">'
            f'<h2>{title}</h2><div class="c-close-row">{store_button(ct, tone="white")}'
            '<img class="c-qr" src="/img/appstore-qr.png" width="104" height="104" alt="QR code: Concerto on the App Store" loading="lazy"></div>'
            '<p class="c-fine">Free on iPhone. Concerto+ available in the app.</p></div></section>')

def eyebrow(t): return f'<p class="c-eyebrow">{e(t)}</p>'

def principles():
    items = [('Accurate before clever.', 'Researched from official sources. Dated, every time.'),
             ('Honest about the unknown.', 'Not confirmed? Concerto says so instead of guessing.'),
             ('The essentials are free.', 'Bag policy, entry, parking, accessibility, setlists. Never paywalled.'),
             ('Partners are labeled.', 'A partner placement says so on the page. Always.')]
    cells = ''.join(f'<div class="c-principle"><span>0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p></div>' for i, (h, t) in enumerate(items))
    return f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("What we believe")}<h2 class="c-h2">The night deserves accuracy.</h2><div class="c-principles">{cells}</div></div></section>'

def name_section():
    return ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-narrow">' + eyebrow('Why Concerto') +
            '<p class="c-statement">A concerto is written for a soloist and an orchestra.<br>The artist is the soloist. The venue, the city, and the ride home are the orchestra.</p>'
            '<p class="c-statement-after">We build for the orchestra.</p></div></section>')

def photo_band(title='Every room has rules. We read them first.'):
    tiles = ''
    for slug, fname in PHOTOS:
        v = VBY.get(slug)
        if not v: continue
        tiles += (f'<a class="c-photo" href="/venue/{slug}"><img src="/img/cityguides/{slug}/{fname}.webp" alt="{e(v["name"])}, {e(place(v))}" loading="lazy" width="800" height="560">'
                  f'<span class="c-photo-cap"><b>{e(v["name"])}</b><span>{e(place(v))}</span></span></a>')
    return f'<section class="c-section c-white c-photos-section" data-reveal><div class="c-wrap">{eyebrow("The rooms")}<h2 class="c-h2">{title}</h2></div><div class="c-photos">{tiles}</div></section>'

def numbers():
    items = [(N_V, 'venue guides'), (N_T, 'tours followed'), (N_S, 'setlists live'), (8, 'essentials per venue')]
    return '<section class="c-numbers" data-reveal><div class="c-wrap c-numbers-row">' + ''.join(f'<div><b>{n}</b><span>{e(l)}</span></div>' for n, l in items) + '</div></section>'

def guide_index():
    vs = [VBY[s] for s in FEATURED_VENUES if s in VBY][:12]
    ts = [t for t in TOURS if t['tourId'] in LIVE][:12]
    vcol = ''.join(f'<li><a href="/venue/{v["id"]}">{e(v["name"])}</a><span>{e(place(v))}</span></li>' for v in vs)
    tcol = ''.join(f'<li><a href="/tour/{t["tourId"]}">{e(t["artist"])}</a><span>{e(t["tourName"])}</span></li>' for t in ts)
    topics = [('Bag policies', '/bags', 'Venue by venue'), ('Parking', '/parking', 'Lots, garages, and routes'), ('Rideshare', '/rideshare', 'Drop-off and pickup'),
              ('Food and drink', '/concessions', 'What is inside'), ('Setlists', '/setlists', f'{N_S} tours'), ('Near me', '/near-me', 'Shows this week')]
    pcol = ''.join(f'<li><a href="{h}">{e(l)}</a><span>{e(d)}</span></li>' for l, h, d in topics)
    return (f'<section class="c-section c-cream" data-reveal><div class="c-wrap">{eyebrow("The guide")}<h2 class="c-h2">Start with where you are going.</h2>'
            f'<div class="c-index"><div><h3>Venues</h3><ul>{vcol}</ul><a class="c-more" href="/venues">All {N_V} venues</a></div>'
            f'<div><h3>Tours</h3><ul>{tcol}</ul><a class="c-more" href="/tours">All {N_T} tours</a></div>'
            f'<div><h3>Topics</h3><ul>{pcol}</ul><a class="c-more" href="/search">Search the guide</a></div></div></div></section>')

# ---------------- pages ----------------

def problem_section():
    # The homepage names the fan's problem in their own words. The story of the name is a good
    # one, but it explains Concerto rather than the night, so it lives on About instead.
    return ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-narrow">' + eyebrow('The problem') +
            '<p class="c-statement">A ticket tells you the date.<br>It doesn\u2019t tell you the rest.</p>'
            '<p class="c-statement-after">What can I bring in? Where do I park? Where is the car after the encore?<br>'
            'One page. Every answer sourced and dated.</p></div></section>')

def home():
    hero = (f'<section class="c-hero"><div class="c-wrap c-hero-grid"><div class="c-hero-copy">{eyebrow("The concert-night companion")}'
            '<h1>From the concert<br>to the city.</h1>'
            '<p class="c-lead">The venue’s rules. The setlist. The timing. The way home. One page per show.</p>'
            f'<div class="c-actions">{store_button("website-home")}<a class="c-link c-link-light" href="#what">What Concerto does</a></div></div>'
            '<figure class="c-hero-photo"><img src="/img/cityguides/kia-forum/Kia-Forum.webp" alt="The Kia Forum, Inglewood, California" width="1042" height="731" fetchpriority="high">'
            '<figcaption>The Kia Forum, Inglewood</figcaption></figure></div>'
            f'<div class="c-wrap c-hero-strip"><span>{N_V} venue guides</span><span>{N_T} tours</span><span>{N_S} setlists</span><span>Free on iPhone</span></div></section>')
    rows = [('Know the venue.', f'Bag policy, entrances, parking, rideshare, and accessibility for {N_V} venues, each researched from official sources and dated.', '/venues', f'Browse {N_V} venue guides'),
            ('Know the music.', f'Tour dates and setlists for {N_T} tours, labeled by where they came from, so you can learn the songs before doors.', '/tours', 'Browse tours and setlists'),
            ('Know the night.', 'One saved show. One page, from the first reminder to the ride home.', '/your-night', 'How Your Night works')]
    what = (f'<section class="c-section c-white" id="what" data-reveal><div class="c-wrap">{eyebrow("What Concerto does")}<h2 class="c-h2">Three things, done carefully.</h2><ol class="c-rows">'
            + ''.join(f'<li><span class="c-num">0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p><a class="c-link" href="{u}">{e(l)}</a></li>' for i, (h, t, u, l) in enumerate(rows)) + '</ol></div></section>')
    plus = ('<section class="c-section c-gold" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Concerto+') +
            '<h2 class="c-h2">For the nights you want planned.</h2><p class="c-body">Plan My Night. AI Bag Check. Show-day alerts.<br>$7.99 a month. Seven days free.</p>'
            '<a class="c-link" href="/premium">Explore Concerto+</a></div><p class="c-pull">Dinner at 5:45.<br>Out the door at 7:10.<br>Lights down at 7:30.</p></div></section>')
    partners = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('For venues and partners') +
                '<h2 class="c-h2">Built with the rooms we cover.</h2></div><div><p class="c-body">Venues verify their own page and post stage times.<br>Restaurants and hotels reach fans on show night, always labeled.</p>'
                '<div class="c-actions"><a class="c-link" href="/partners">Partner with Concerto</a><a class="c-link" href="/console/">Partner Console</a></div></div></div></section>')
    return '<main id="main-content" class="c-page">' + hero + name_section() + what + photo_band() + numbers() + principles() + plus + partners + guide_index() + close() + '</main>'

def your_night():
    stages = [('Weeks out', 'Learn the songs. Know the rules.', 'The setlist, labeled by source. Bag policy, entry, and parking, each dated.'),
              ('The week of', 'The forecast arrives. The plan comes together.', 'Weather at seven days out, never sooner. Places to eat nearby, partners labeled.'),
              ('Show day', 'Leave on time. Walk in ready.', 'Alerts in the venue’s time zone. Directions, parking, and rideshare in one place.'),
              ('After the encore', 'The way home is already there.', 'The venue’s pickup guidance and your ride, kept with the show.')]
    tl = ''.join(f'<li><span class="c-when">{e(w)}</span><h3>{e(h)}</h3><p>{e(t)}</p></li>' for w, h, t in stages)
    free = ['Saving shows, from Concerto or your calendar', 'Your Night for every saved show', f'Venue guides for {N_V} venues', 'Setlists, labeled by source', 'Directions, parking, and rideshare']
    paid = ['Plan My Night: the evening, built around your show', 'AI Bag Check against the venue’s policy', 'Show-day alerts']
    cols = ('<div class="c-compare"><div><h3>Free</h3><ul>' + ''.join(f'<li>{e(x)}</li>' for x in free) + '</ul></div><div><h3>Concerto+</h3><ul>' + ''.join(f'<li>{e(x)}</li>' for x in paid) +
            '</ul><a class="c-link" href="/premium">About Concerto+</a></div></div>')
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type"><div class="c-wrap c-narrow">{eyebrow("Your Night")}<h1>One page for<br>the whole night.</h1><p class="c-lead">Save a show and Concerto builds the page around it: the venue’s rules, the setlist, the timing, the places nearby, and the way home. It changes as the show gets closer, so the top always says what matters next.</p><div class="c-actions">{store_button("website-your-night", "Save your next show")}</div></div></section>'
            f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("How it changes")}<h2 class="c-h2">From the ticket to the way home.</h2><ol class="c-timeline">{tl}</ol></div></section>'
            f'<section class="c-section c-cream" data-reveal><div class="c-wrap">{eyebrow("What it costs")}<h2 class="c-h2">The essentials are free.</h2>{cols}</div></section>'
            + close('Save your next show.', 'website-your-night') + '</main>')

def premium():
    feats = [('Plan My Night', 'When to eat. When to leave. How you get home.'),
             ('AI Bag Check', 'Your bag against the venue’s published rule, before you leave. The venue still decides at the door.'),
             ('Show-day alerts', 'Forecast in the morning. A nudge before you leave. The way home after the encore.')]
    rows = ''.join(f'<li><span class="c-num">0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p></li>' for i, (h, t) in enumerate(feats))
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type"><div class="c-wrap c-narrow">{eyebrow("Concerto+")}<h1>For the nights<br>you want planned.</h1><p class="c-lead">An evening built around your show. Your bag checked against the venue’s rule. Alerts on show day.</p><div class="c-actions">{store_button("website-premium", "Start the 7-day free trial")}</div></div></section>'
            f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("What is included")}<h2 class="c-h2">Three things the free app does not do.</h2><ol class="c-rows">{rows}</ol></div></section>'
            '<section class="c-section c-cream" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Pricing') + '<h2 class="c-h2">Simple, and cancel anytime.</h2><p class="c-body">Billed through the App Store. Cancel in your Apple ID settings.</p></div>'
            '<div class="c-prices"><div><b>$7.99</b><span>per month, with a 7-day free trial</span></div><div><b>$69.99</b><span>per year</span></div></div></div></section>'
            '<section class="c-section c-white" data-reveal><div class="c-wrap c-narrow">' + eyebrow('Always free') + '<p class="c-statement">Bag policy, entry, parking, accessibility, setlists, directions.<br>Never behind Concerto+.</p></div></section>'
            + close('Start with the app.', 'website-premium') + '</main>')

def about():
    facts = [('Founded', 'Dallas–Fort Worth'), ('Company', 'Concerto LLC'), ('Product', 'Concerto for iPhone'), ('Coverage', f'{N_V} venues, {N_T} tours')]
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type"><div class="c-wrap c-narrow">{eyebrow("About Concerto")}<h1>The ticket is the start<br>of the night.</h1><p class="c-lead">The practical details around a concert, in one place.<br>Less piecing it together. More of the show.</p></div></section>'
            + name_section() +
            '<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('The founder') + '<h2 class="c-h2">Jayce Wells</h2><p class="c-role">Founder</p></div>'
            '<div><p class="c-body">A ticket does not mean the night is figured out. The bag policy, the parking, dinner, the setlist, the ride home: each sends a fan somewhere different.</p>'
            '<p class="c-body">Concerto brings those questions back to the show. Founder-led, from Dallas–Fort Worth.</p></div></div></section>'
            + principles() +
            '<section class="c-numbers" data-reveal><div class="c-wrap c-facts">' + ''.join(f'<div><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in facts) + '</div></section>'
            '<section class="c-section c-cream" data-reveal><div class="c-wrap c-links-row"><a class="c-link" href="/press">Press</a><a class="c-link" href="/investors">Investors</a><a class="c-link" href="/partners">Partners</a><a class="c-link" href="/contact">Contact</a></div></section>'
            + close() + '</main>')

def hub_intro(kicker, h1, lead, placeholder, target):
    return (f'<section class="c-hero c-hero-type c-hero-hub"><div class="c-wrap">{eyebrow(kicker)}<h1>{h1}</h1><p class="c-lead">{lead}</p>'
            f'<label class="c-filter"><span class="c-sr">{e(placeholder)}</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.75" cy="10.75" r="6.75"/><path d="m16 16 4.5 4.5" stroke-linecap="round"/></svg>'
            f'<input type="search" placeholder="{e(placeholder)}" data-filter-target="{target}" autocomplete="off"></label></div></section>')

def venues_hub():
    groups = {}
    for v in sorted(VENUES, key=lambda x: (x.get('country') != 'US', x.get('state') or x.get('country') or '', x['name'])):
        key = v.get('state') if v.get('country') == 'US' and v.get('state') else (v.get('country') or 'Other')
        groups.setdefault(key, []).append(v)
    body = ''.join(f'<div class="c-group"><h2>{e(k)}</h2><ul>' + ''.join(f'<li class="c-entry"><a href="/venue/{v["id"]}">{e(v["name"])}</a><span>{e(v.get("city"))}</span></li>' for v in vs) + '</ul></div>' for k, vs in groups.items())
    return ('<main id="main-content" class="c-page">' + hub_intro('Venue guides', f'{N_V} venues.<br>Every rule, checked.', 'Bag policy, entry, parking, rideshare, accessibility.<br>From official sources, dated.', 'Search venues or cities', '.c-entry')
            + photo_band('Start with a room.') + f'<section class="c-section c-white"><div class="c-wrap c-directory">{body}</div></section>' + close() + '</main>')

def tours_hub():
    groups = {}
    for t in sorted(TOURS, key=lambda x: x['artist'].lower()):
        k = t['artist'][0].upper() if t['artist'][0].isalpha() else '#'
        groups.setdefault(k, []).append(t)
    def row(t):
        n = len(LIVE[t['tourId']]['songs']) if t['tourId'] in LIVE else 0
        return f'<li class="c-entry"><a href="/tour/{t["tourId"]}">{e(t["artist"])}</a><span>{e(t["tourName"])}{" · " + songs_word(n) if n else ""}</span></li>'
    body = ''.join(f'<div class="c-group"><h2>{e(k)}</h2><ul>' + ''.join(row(t) for t in ts) + '</ul></div>' for k, ts in groups.items())
    return ('<main id="main-content" class="c-page">' + hub_intro('Tours', f'{N_T} tours<br>on the road.', f'Dates, the official tour site, and {N_S} setlists, labeled by source.', 'Search artists or tours', '.c-entry')
            + f'<section class="c-section c-white"><div class="c-wrap c-directory">{body}</div></section>' + close() + '</main>')

def setlists_hub():
    items = sorted(LIVE.items(), key=lambda kv: (kv[1].get('artist') or '').lower())
    body = '<div class="c-group"><ul>' + ''.join(f'<li class="c-entry"><a href="/setlist/{k}">{e(v.get("artist"))}</a><span>{e(v.get("tour"))} · {songs_word(len(v["songs"]))}</span></li>' for k, v in items) + '</ul></div>'
    return ('<main id="main-content" class="c-page">' + hub_intro('Setlists', f'{N_S} setlists,<br>labeled by source.', 'Official tour playlists and confirmed setlists, each marked with its source and date. Setlists change by night.', 'Search artists', '.c-entry')
            + f'<section class="c-section c-white"><div class="c-wrap c-directory c-directory-one">{body}</div></section>' + close() + '</main>')

def venue_page(v):
    info = INFO.get(v['id']) or {}
    toc, secs = '', ''
    for key, label, anchor in SECTIONS:
        x = info.get(key) or {}
        body = x.get('summary') or x.get('note') or x.get('body') or ''
        if not body: continue
        toc += f'<li><a href="#{anchor}">{e(label)}</a></li>'
        lists = ''
        if x.get('allowed') or x.get('prohibited'):
            lists = '<div class="c-rules">' + (f'<div><h3>Allowed</h3><ul>{"".join("<li>"+e(a)+"</li>" for a in x.get("allowed", []))}</ul></div>' if x.get('allowed') else '') + (f'<div><h3>Not allowed</h3><ul>{"".join("<li>"+e(a)+"</li>" for a in x.get("prohibited", []))}</ul></div>' if x.get('prohibited') else '') + '</div>'
        ver = f'<span class="verified">Checked {e(pretty_date(x.get("verified")))}</span>' if x.get('verified') else '<span class="verified">Not yet verified</span>'
        src = f'<div class="link-row"><a href="{e(x["officialLink"])}" target="_blank" rel="noopener">Official source</a></div>' if x.get('officialLink') else ''
        secs += f'<article class="info-card c-guide-sec" data-section="{e(key)}" id="{anchor}"><div class="c-sec-head"><h2>{e(label)}</h2>{ver}</div><p>{e(body)}</p>{lists}{src}</article>'
    near = [x for x in VENUES if x['id'] != v['id'] and (x.get('state') == v.get('state') if v.get('country') == 'US' else x.get('country') == v.get('country'))][:6]
    near_html = ''.join(f'<li class="c-entry"><a href="/venue/{x["id"]}">{e(x["name"])}</a><span>{e(x.get("city"))}</span></li>' for x in near)
    local = dict(PHOTOS).get(v['id'])
    fb = f' data-fallback-src="/img/cityguides/{v["id"]}/{local}.webp"' if local else ''
    photo = f'<div class="c-venue-photo" data-vphoto data-vname="{e(v["name"])}" data-vcity="{e(v.get("city"))}" data-vlat="{e(v.get("lat"))}" data-vlng="{e(v.get("lng"))}"{fb}></div>'
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type c-hero-detail"><div class="c-wrap"><nav class="c-crumbs" aria-label="Breadcrumb"><a href="/venues">Venues</a><span>/</span>{e(v["name"])}</nav>{eyebrow("Venue guide · " + place(v))}<h1>{e(v["name"])}</h1>'
            f'<p class="c-lead">Bag policy, entry, parking, rideshare, and accessibility at {e(v["name"])}. From official sources, dated.</p>'
            f'<div class="c-actions">{app_link("venue", v["id"], "Open in Concerto", "c-btn c-btn-navy")}</div>'
            f'<div class="tonight" data-venue-tonight data-name="{e(v["name"])}" data-country="{e(ISO.get(v.get("country"), v.get("country") or ""))}" data-lat="{e(v.get("lat"))}" data-lng="{e(v.get("lng"))}"></div></div>'
            f'<div class="c-wrap">{photo}</div></section>'
            f'<section class="c-section c-white"><div class="c-wrap c-guide"><aside class="c-toc"><p class="c-eyebrow">On this page</p><ol>{toc}</ol></aside><div class="c-guide-body">{secs}</div></div></section>'
            + (f'<section class="c-section c-cream"><div class="c-wrap">{eyebrow("Nearby")}<h2 class="c-h2 c-h2-sm">More venue guides.</h2><div class="c-directory c-directory-one"><div class="c-group"><ul>{near_html}</ul></div></div></div></section>' if near else '')
            + close('Going to a show here?', 'website-venue') + '</main>')

def tour_page(t):
    s = SETS.get(t['tourId']); songs = (s or {}).get('songs') or []
    official = f'<a class="c-btn c-btn-line" href="{e(t["tourWebsite"])}" target="_blank" rel="noopener">Official tour site</a>' if t.get('tourWebsite') else ''
    if songs:
        setl = (f'<section class="c-section c-white"><div class="c-wrap c-narrow">{eyebrow("Setlist")}<h2 class="c-h2 c-h2-sm">{songs_word(len(songs))}.</h2><p class="c-source">{e(source_label(s))}. Setlists change by night.</p>'
                f'<div class="c-songs"><ol class="song-list">' + ''.join(f'<li>{e(x)}</li>' for x in songs[:12]) + '</ol></div>'
                + (f'<a class="c-link" href="/setlist/{t["tourId"]}">All {songs_word(len(songs))}</a>' if len(songs) > 12 else f'<a class="c-link" href="/setlist/{t["tourId"]}">Setlist page</a>') + '</div></section>')
    elif s:
        setl = f'<section class="c-section c-white"><div class="c-wrap c-narrow">{eyebrow("Setlist")}<h2 class="c-h2 c-h2-sm">Setlist Coming Soon!</h2><p class="c-body">Concerto is following this tour. Songs appear here when there is a usable current setlist, never a guessed one.</p></div></section>'
    else: setl = ''
    more = [x for x in TOURS if x['tourId'] in LIVE and x['tourId'] != t['tourId']][:6]
    more_html = ''.join(f'<li class="c-entry"><a href="/tour/{x["tourId"]}">{e(x["artist"])}</a><span>{e(x["tourName"])}</span></li>' for x in more)
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type c-hero-detail"><div class="c-wrap"><nav class="c-crumbs" aria-label="Breadcrumb"><a href="/tours">Tours</a><span>/</span>{e(t["artist"])}</nav>{eyebrow("On tour")}<h1>{e(t["artist"])}</h1><p class="c-lead">{e(t["tourName"])}</p>'
            f'<div class="c-actions">{app_link("tour", t["tourId"], "Open in Concerto", "c-btn c-btn-navy")}{official}</div></div>'
            f'<div class="c-wrap"><div class="c-venue-photo c-artist-photo" data-artist="{e(t["artist"])}"></div></div></section>'
            + setl + f'<section class="c-section c-cream"><div class="c-wrap">{eyebrow("Also on the road")}<h2 class="c-h2 c-h2-sm">More tours with setlists.</h2><div class="c-directory c-directory-one"><div class="c-group"><ul>{more_html}</ul></div></div></div></section>'
            + close('Going to this tour?', 'website-tour') + '</main>')

def setlist_page(slug, s):
    t = next((x for x in TOURS if x['tourId'] == slug), None)
    songs = s['songs']
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type c-hero-detail"><div class="c-wrap c-narrow"><nav class="c-crumbs" aria-label="Breadcrumb"><a href="/setlists">Setlists</a><span>/</span>{e(s.get("artist"))}</nav>{eyebrow("Setlist · " + (s.get("tour") or ""))}<h1>{e(s.get("artist"))}</h1>'
            f'<p class="c-lead">{songs_word(len(songs))}. {e(source_label(s))}. Setlists change by night.</p><div class="c-actions">{app_link("tour", slug, "Save your show in Concerto", "c-btn c-btn-navy")}'
            + (f'<a class="c-btn c-btn-line" href="/tour/{slug}">Tour guide</a>' if t else '') + '</div></div></section>'
            f'<section class="c-section c-white"><div class="c-wrap c-narrow"><div class="c-songs c-songs-full"><ol class="song-list">' + ''.join(f'<li>{e(x)}</li>' for x in songs) + '</ol></div></div></section>'
            + close('Know every word.', 'website-setlist') + '</main>')

def topic_page(key, kicker, h1, lead):
    rows = ''
    for v in sorted(VENUES, key=lambda x: x['name']):
        x = (INFO.get(v['id']) or {}).get(key) or {}
        body = x.get('summary') or x.get('note') or ''
        if not body: continue
        anchor = next(a for k, _, a in SECTIONS if k == key)
        rows += (f'<li class="c-entry c-topic"><div><a href="/venue/{v["id"]}#{anchor}">{e(v["name"])}</a><span>{e(place(v))}{" · checked " + e(pretty_date(x.get("verified"))) if x.get("verified") else ""}</span></div><p>{e(first_sentence(body))}</p></li>')
    return ('<main id="main-content" class="c-page">' + hub_intro(kicker, h1, lead, 'Search venues or cities', '.c-entry')
            + f'<section class="c-section c-white"><div class="c-wrap c-directory c-directory-one"><div class="c-group"><ul>{rows}</ul></div></div></section>' + close() + '</main>')

def bagcheck():
    steps = [('Pick the venue.', 'It starts from the same verified venue policy used everywhere in Concerto.'), ('Show Concerto the bag.', 'Size and type, against the venue’s published limits.'), ('Leave with context.', 'It names the rule it used. The venue still decides at the door.')]
    rows = ''.join(f'<li><span class="c-num">0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p></li>' for i, (h, t) in enumerate(steps))
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type"><div class="c-wrap c-narrow">{eyebrow("Concerto+ · AI Bag Check")}<h1>Check the bag<br>before the door.</h1><p class="c-lead">Compare what you plan to bring with the venue’s published bag policy, before you leave the house.</p><div class="c-actions">{store_button("website-bagcheck")}<a class="c-link" href="/bags">Read bag policies</a></div></div></section>'
            f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("How it works")}<h2 class="c-h2">Three steps, one answer.</h2><ol class="c-rows">{rows}</ol></div></section>'
            + close('Pack once.', 'website-bagcheck') + '</main>')


# ---------------- V8.1: one hero system, and the remaining pages ----------------
def strip(items):
    return '<div class="c-wrap c-hero-strip">' + ''.join(f'<span>{x}</span>' for x in items) + '</div>' if items else ''

def hero(kicker, h1, lead='', actions='', items=None, tone='cream', cls='', crumbs=''):
    return (f'<section class="c-hero c-hero-{tone} {cls}"><div class="c-wrap c-hero-inner">{crumbs}{eyebrow(kicker)}<h1>{h1}</h1>'
            + (f'<p class="c-lead">{lead}</p>' if lead else '') + (f'<div class="c-actions">{actions}</div>' if actions else '') + f'</div>{strip(items)}</section>')

def rows(items):
    return '<ol class="c-rows">' + ''.join(f'<li><span class="c-num">0{i+1}</span><h3>{e(h)}</h3><p>{t}</p>{extra}</li>' for i, (h, t, extra) in enumerate(items)) + '</ol>'

def timeline(items):
    return '<ol class="c-timeline">' + ''.join(f'<li><span class="c-when">{e(w)}</span><h3>{e(h)}</h3><p>{e(t)}</p></li>' for w, h, t in items) + '</ol>'

def section(tone, kicker, title, inner, narrow=False, sid=''):
    return (f'<section class="c-section c-{tone}"{f" id={chr(34)}{sid}{chr(34)}" if sid else ""} data-reveal><div class="c-wrap{" c-narrow" if narrow else ""}">'
            + (eyebrow(kicker) if kicker else '') + (f'<h2 class="c-h2">{title}</h2>' if title else '') + inner + '</div></section>')

def mail(addr): return f'<a href="mailto:{addr}">{addr}</a>'

def home():
    h = hero('The concert-night companion', 'From the concert<br>to the city.',
             'The venue’s rules. The setlist. The timing. The way home. One page per show.',
             store_button('website-home', tone='white') + '<a class="c-link c-link-light" href="#what">What Concerto does</a>',
             [f'{N_V} venue guides', f'{N_T} tours', f'{N_S} setlists', 'Free on iPhone'], 'navy', 'c-hero-home')
    what = section('white', 'What Concerto does', 'Three things, done carefully.', rows([
        ('Know the venue.', e(f'Bag policy, entry, parking, rideshare, accessibility. {N_V} venues, from official sources, dated.'), f'<a class="c-link" href="/venues">Browse {N_V} venue guides</a>'),
        ('Know the music.', e(f'{N_T} tours. {N_S} setlists, labeled by source. Learn the songs before doors.'), '<a class="c-link" href="/tours">Browse tours and setlists</a>'),
        ('Know the night.', 'Save a show and Your Night keeps it all on one page, from the first reminder to the ride home.', '<a class="c-link" href="/your-night">How Your Night works</a>')]), sid='what')
    plus = ('<section class="c-section c-gold" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Concerto+') +
            '<h2 class="c-h2">For the nights you want planned.</h2><p class="c-body">Plan My Night. AI Bag Check. Show-day alerts.<br>$7.99 a month. Seven days free.</p>'
            '<a class="c-link" href="/premium">Explore Concerto+</a></div><p class="c-pull">Dinner at 5:45.<br>Out the door at 7:10.<br>Lights down at 7:30.</p></div></section>')
    partners = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('For venues and partners') +
                '<h2 class="c-h2">Built with the rooms we cover.</h2></div><div><p class="c-body">Venues verify their own page and post stage times.<br>Restaurants and hotels reach fans on show night, always labeled.</p>'
                '<div class="c-actions"><a class="c-link" href="/partners">Partner with Concerto</a><a class="c-link" href="/console/">Partner Console</a></div></div></div></section>')
    return '<main id="main-content" class="c-page">' + h + problem_section() + what + photo_band() + numbers() + principles() + plus + partners + guide_index() + close() + '</main>'

def your_night():
    h = hero('Your Night', 'One page for<br>the whole night.', 'Rules, setlist, timing, places nearby, the way home.<br>The page changes as the show gets closer.',
             store_button('website-your-night', 'Save your next show'), ['Free in Concerto', 'Changes as show day gets closer', 'Works offline once saved' if False else 'One page per saved show'], 'cream')
    tl = timeline([('Weeks out', 'Learn the songs. Know the rules.', 'The tour’s setlist, labeled by where it came from. The venue’s bag policy, entrances, and parking, each with the date it was checked.'),
                   ('The week of', 'The forecast arrives. The plan comes together.', 'Weather appears seven days out and never sooner. Places to eat and drink near the venue, with partners always labeled.'),
                   ('Show day', 'Leave on time. Walk in ready.', 'Show-day alerts in the venue’s own time zone. Directions, parking, and rideshare in one place.'),
                   ('After the encore', 'The way home is already there.', 'The venue’s published pickup guidance and your ride, kept with the show.')])
    free = ['Saving shows, from Concerto or your calendar', 'Your Night for every saved show', f'Venue guides for {N_V} venues', 'Setlists, labeled by source', 'Directions, parking, and rideshare']
    paid = ['Plan My Night: the evening, built around your show', 'AI Bag Check against the venue’s policy', 'Show-day alerts']
    cols = ('<div class="c-compare"><div><h3>Free</h3><ul>' + ''.join(f'<li>{e(x)}</li>' for x in free) + '</ul></div><div><h3>Concerto+</h3><ul>' + ''.join(f'<li>{e(x)}</li>' for x in paid) + '</ul><a class="c-link" href="/premium">About Concerto+</a></div></div>')
    return '<main id="main-content" class="c-page">' + h + section('white', 'How it changes', 'From the ticket to the way home.', tl) + section('cream', 'What it costs', 'The essentials are free.', cols) + close('Save your next show.', 'website-your-night') + '</main>'

def premium():
    h = hero('Concerto+', 'For the nights<br>you want planned.', 'An evening built around your show. Your bag checked against the venue’s rule. Alerts on show day.',
             store_button('website-premium', 'Start the 7-day free trial'), ['$7.99 a month', '$69.99 a year', '7-day free trial', 'Cancel anytime'], 'gold')
    feats = rows([('Plan My Night', 'A plan for the evening around the show you saved: when to eat, when to leave, and how you get home.', ''),
                  ('AI Bag Check', 'Compare your bag with the venue’s published policy before you leave. It shows the rule it used, and the venue still makes the final call.', ''),
                  ('Show-day alerts', 'The morning forecast, a reminder before you head out, and the way home after the encore, in the venue’s time zone.', '')])
    pricing = ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Pricing') + '<h2 class="c-h2">Simple, and cancel anytime.</h2><p class="c-body">Billed through the App Store. Cancel in your Apple ID settings.</p></div>'
               '<div class="c-prices"><div><b>$7.99</b><span>per month, with a 7-day free trial</span></div><div><b>$69.99</b><span>per year</span></div></div></div></section>')
    free = section('white', 'Always free', '', '<p class="c-statement">Bag policy, entry, parking, accessibility, setlists, directions.<br>Never behind Concerto+.</p>', narrow=True)
    return '<main id="main-content" class="c-page">' + h + section('white', 'What is included', 'Three things the free app does not do.', feats) + pricing + free + close('Start with the app.', 'website-premium') + '</main>'

def about():
    h = hero('About Concerto', 'The ticket is the start<br>of the night.', 'The practical details around a concert, in one place.<br>Less piecing it together. More of the show.',
             '', ['Founded in Dallas–Fort Worth', 'Concerto LLC', 'Concerto for iPhone'], 'navy')
    founder = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('The founder') + '<h2 class="c-h2">Jayce Wells</h2><p class="c-role">Founder</p></div>'
               '<div><p class="c-body">A ticket does not mean the night is figured out. The bag policy, the parking, dinner, the setlist, the ride home: each sends a fan somewhere different.</p>'
               '<p class="c-body">Concerto brings those questions back to the show. Founder-led, from Dallas–Fort Worth.</p></div></div></section>')
    facts = [('Founded', 'Dallas–Fort Worth'), ('Company', 'Concerto LLC'), ('Product', 'Concerto for iPhone'), ('Coverage', f'{N_V} venues, {N_T} tours')]
    fx = '<section class="c-numbers" data-reveal><div class="c-wrap c-facts">' + ''.join(f'<div><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in facts) + '</div></section>'
    links = '<section class="c-section c-cream" data-reveal><div class="c-wrap c-links-row"><a class="c-link" href="/press">Press</a><a class="c-link" href="/investors">Investors</a><a class="c-link" href="/partners">Partners</a><a class="c-link" href="/contact">Contact</a></div></section>'
    return '<main id="main-content" class="c-page">' + h + name_section() + founder + principles() + fx + links + close() + '</main>'

def hub_intro(kicker, h1, lead, placeholder, target, items=None):
    filt = (f'<label class="c-filter"><span class="c-sr">{e(placeholder)}</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.75" cy="10.75" r="6.75"/><path d="m16 16 4.5 4.5" stroke-linecap="round"/></svg>'
            f'<input type="search" placeholder="{e(placeholder)}" data-filter-target="{target}" autocomplete="off"></label>')
    return hero(kicker, h1, lead, filt, items, 'cream', 'c-hero-hub')

def bagcheck():
    h = hero('Concerto+ · AI Bag Check', 'Check the bag<br>before the door.', 'Your bag against the venue’s published policy, before you leave the house.',
             store_button('website-bagcheck') + '<a class="c-link" href="/bags">Read bag policies</a>', ['Part of Concerto+', 'The venue makes the final call'], 'gold')
    r = rows([('Pick the venue.', 'Bag Check starts from the same verified venue policy used throughout Concerto.', ''), ('Show Concerto the bag.', 'Compare the size and type of your bag against the venue’s published limits.', ''),
              ('Leave with context.', 'It explains the rule it used and what is uncertain. The venue always makes the final call.', '')])
    return '<main id="main-content" class="c-page">' + h + section('white', 'How it works', 'Three steps, one answer.', r) + close('Pack once.', 'website-bagcheck') + '</main>'

# ----- company -----
def press():
    h = hero('Press and media', 'Concerto, in brief.', 'Concerto helps concert fans plan the night around their ticket.', '<a class="c-btn c-btn-navy" href="/contact?topic=media">Media inquiry</a>', ['Founded in Dallas–Fort Worth', 'Concerto for iPhone and the web'], 'cream')
    facts = [('Company', 'Concerto LLC'), ('Founder', 'Jayce Wells'), ('Founded in', 'Dallas–Fort Worth'), ('Product', 'Concerto for iPhone, and concertocity.com'), ('Coverage', f'{N_V} venue guides, {N_T} tours'), ('Independence', 'Independent from artists, venues, teams, and promoters')]
    fact_list = '<dl class="c-facts-list">' + ''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in facts) + '</dl>'
    boiler = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Company background') + '<h2 class="c-h2">One show. The night around it.</h2></div><div>'
              '<p class="c-body">An iPhone app and website, founded by Jayce Wells in Dallas–Fort Worth.<br>Fans save a show and get venue guidance, setlists, nearby places, and how to get there. Concerto+ adds planning.</p>'
              '<p class="c-body">Independent from artists, venues, teams, and promoters. A listed guide is not a partnership.</p></div></div></section>')
    kit = section('cream', 'Fact sheet', 'The essentials.', fact_list)
    res = section('white', 'Media resources', 'Logos, interviews, and figures.', '<p class="c-body">Logo files, product images, interviews, confirmed figures. Ask and we will send them.</p><div class="c-actions"><a class="c-link" href="/contact?topic=media">Contact for media</a><a class="c-link" href="/about">Read the founder story</a></div>')
    return '<main id="main-content" class="c-page">' + h + boiler + kit + res + close() + '</main>'

def investors():
    h = hero('Investors', 'A focused product.<br>A practical next step.', 'Concerto prepares fans for the night around the ticket.<br>We welcome people who know live music, hospitality, and consumer products.',
             '<a class="c-btn c-btn-navy" href="/contact?topic=investor">Contact the founder</a>', ['Founder-led', 'Dallas–Fort Worth'], 'navy')
    today = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('The company today') + '<h2 class="c-h2">Built around one fan experience.</h2></div><div>'
             '<p class="c-body">Venue guidance, tour information, nearby discovery, and planning, around one saved show. The app and website are built.</p>'
             '<p class="c-body">Concerto+ is the paid tier. The partner program is in development. Coverage is not a measure of users or revenue.</p></div></div></section>')
    conv = section('cream', 'The conversation', 'Relevant experience and introductions.', '<p class="c-body">Connections across venues, hospitality, artists, and consumer products are welcome. Figures, priorities, and terms are discussed directly, not inferred from the website.</p><div class="c-actions"><a class="c-link" href="/contact?topic=investor">Start a conversation</a></div>')
    return '<main id="main-content" class="c-page">' + h + today + principles() + conv + close() + '</main>'

def creators():
    h = hero('Creators', 'Help fans see<br>the whole night.', 'A useful point of view on a concert, a venue, or a city.<br>Music, food, travel, and local creators welcome.',
             '<a class="c-btn c-btn-navy" href="/contact?topic=creator">Pitch a collaboration</a>', ['Music', 'Food', 'Travel', 'Local'], 'cream')
    ideas = rows([('A pre-show dining guide.', 'Where to eat before a show at a specific venue, and why.', ''), ('An accessible venue walkthrough.', 'What arriving and moving through the building is actually like.', ''),
                  ('A concert-weekend itinerary.', 'The show as the center of a trip, from arrival to the last night out.', ''), ('A tip you wish you had known.', 'The practical thing that would have changed your night.', '')])
    how = section('cream', 'How it works', 'Clear terms before anything starts.', '<p class="c-body">Tell us the audience, the location or tour, the format, the timing, and your rates. Deliverables, rights, pay, and disclosures are agreed before work starts.</p><p class="c-body">An inquiry is not an invitation, a paid project, tickets, or travel.</p><div class="c-actions"><a class="c-link" href="/contact?topic=creator">Pitch a collaboration</a></div>', narrow=True)
    return '<main id="main-content" class="c-page">' + h + section('white', 'Ideas worth discussing', 'A real night. Your perspective.', ideas) + how + close() + '</main>'

# ----- partners -----
PARTNER = {
  'partner-restaurants': ('Restaurants and bars', 'Be part of their plans<br>before the show.', 'Help fans choose a meal or a drink that fits the venue and the evening.',
      'A concert menu, a reservation window, or a clearly defined dining benefit.', 'Introduce your business while fans are deciding where to eat. Agree on the venue, dates, placement, and action before launch.', 'Reservations, offer uses, or tracked visits to your booking page.'),
  'partner-hotels': ('Hotels', 'Give fans a reason<br>to stay the night.', 'Make a concert trip easier with a stay that works for the venue and the date.',
      'A concert rate, late checkout, or an included parking benefit with clear conditions.', 'Present a relevant stay to fans planning around nearby venues. Start with selected dates or one property, with scope agreed in advance.', 'Tracked booking-link visits; bookings only where your reporting supports attribution.'),
  'partner-venues': ('Venues', 'Help fans<br>arrive informed.', 'Put your published guidance within reach of fans planning their visit.',
      'Current entry rules, useful arrival information, or an optional parking or hospitality offer.', 'Improve the information fans find before arrival. Approved venue access supports guide updates and event timing; commercial placements are agreed separately.', 'Guide visits and arrival-link activity where tracking is available.'),
  'partner-artists': ('Artists and tours', 'Carry the connection<br>beyond the ticket.', 'Give fans useful information and a reason to engage around your tour dates.',
      'Confirmed tour information, a merch benefit, or an authorized fan-access offer.', 'Connect a benefit to your tour or selected venues. Work with Concerto on the relevant dates, source material, and fan action.', 'Tour-page activity and tracked offer-link visits where available.'),
}
STEPS = [('Step one', 'Tell us the fit.', 'Share your business, audience, location or tour, and an initial idea. An inquiry is not a commitment.'),
         ('Step two', 'Agree on the details.', 'We review the fan benefit, dates, placements, responsibilities, pricing if applicable, and what can be measured.'),
         ('Step three', 'Prepare and review.', 'Provide the approved copy, links, eligibility, and redemption instructions. The Partner Console lets you prepare an offer; publication follows review.'),
         ('Step four', 'Launch and learn.', 'Activate the agreed placement, keep the offer current, and review available results. Reach, bookings, and sales are not guaranteed.')]

def partners_hub():
    h = hero('Concerto Partners', 'A better concert night.<br>A useful place in it.', 'Meet fans while they plan the night.<br>Something useful for them. A clear objective for you.',
             '<a class="c-btn c-btn-navy" href="#categories">Find your fit</a><a class="c-link" href="/console/">Partner Console</a>', ['Restaurants and bars', 'Hotels', 'Venues', 'Artists and tours'], 'gold')
    cats = rows([(v[0] + '.', e(v[2]), f'<a class="c-link" href="/partners/{k.split("-",1)[1]}">Explore the fit</a>') for k, v in PARTNER.items()])
    means = section('cream', 'What a partnership means', 'Specific scope. Shared expectations.', '<p class="c-body">Agreed in advance. Labeled for fans. Measured only where measurement is real.<br>Clicks are not purchases. Reach, bookings, and sales are not guaranteed.</p>', narrow=True)
    return '<main id="main-content" class="c-page">' + h + section('white', 'Categories', 'Where you fit in the night.', cats, sid='categories') + section('white', 'Working together', 'A clear path to launch.', timeline(STEPS)) + means + close('Let’s build the night together.', 'website-partners') + '</main>'

def partner_page(key, form_html):
    kicker, h1, lead, fans, explore, success = PARTNER[key]
    h = hero(kicker, h1, lead, '<a class="c-btn c-btn-navy" href="#interest">Discuss a partnership</a><a class="c-link" href="/partners">All partner types</a>', ['Scope agreed in advance', 'Labeled for fans'], 'gold')
    opp = rows([('What fans receive', e(fans), ''), ('What you can explore', e(explore), ''), ('What success can mean', e(success) + ' Confirm measurement capabilities before launch; clicks are not confirmed purchases.', '')])
    form = (f'<section class="c-section c-cream" id="interest"><div class="c-wrap c-split"><div>{eyebrow("Start a conversation")}<h2 class="c-h2">Tell us what you have in mind.</h2>'
            '<p class="c-body">No proposal needed. We review the fit and follow up.</p><p class="c-body">Already approved? <a href="/console/">Open the Partner Console</a>.</p></div>'
            f'<div class="c-form">{form_html}</div></div></section>')
    return '<main id="main-content" class="c-page">' + h + section('white', 'The opportunity', 'Useful for fans. Relevant to you.', opp) + section('white', 'Working together', 'A clear path to launch.', timeline(STEPS)) + form + '</main>'

def contact_page(form_html):
    h = hero('Contact', 'Let’s get you to<br>the right place.', 'Questions about your concert night, an idea for a collaboration, or a company inquiry. Start here.', '', ['support@concertocity.com', 'partnerships@concertocity.com'], 'cream')
    routes = ('<dl class="c-facts-list">'
              f'<div><dt>App support</dt><dd>{mail("support@concertocity.com")} or the <a href="/help">Help Center</a></dd></div>'
              f'<div><dt>Partnerships</dt><dd>Choose your <a href="/partners">partner category</a> or write to {mail("partnerships@concertocity.com")}</dd></div>'
              '<div><dt>Media, creators, investors</dt><dd>Use the form, and pick the topic that fits</dd></div></dl>')
    form = f'<section class="c-section c-white"><div class="c-wrap c-split"><div>{eyebrow("How can we help?")}<h2 class="c-h2">Three ways in.</h2>{routes}</div><div class="c-form">{form_html}</div></div></section>'
    return '<main id="main-content" class="c-page">' + h + form + '</main>'

# ----- product and utility -----
def near_me():
    h = hero('Near Me', 'Something good.<br>Somewhere near you.', 'Concerts by location and date.<br>Save the one you are going to. The rest follows.',
             store_button('website-near-me', tone='white'), ['Shows by location and date', 'In the app'], 'navy')
    r = rows([('Find a show.', 'See what is on. Pick a date. Find a reason to go.', '<a class="c-link" href="/tours">Browse tours</a>'),
              ('Give the night a home.', 'A saved show opens Your Night: rules, setlist, places nearby, the way home.', '<a class="c-link" href="/your-night">How Your Night works</a>'),
              ('Know the room.', e(f'Every venue guide is researched from official sources and dated, for {N_V} venues.'), '<a class="c-link" href="/venues">Browse venues</a>')])
    return '<main id="main-content" class="c-page">' + h + section('white', 'How it works', 'From nearby to Your Night.', r) + photo_band('Start with a room near you.') + close() + '</main>'

def perks_page():
    h = hero('Concerto Perks', 'Something extra<br>for your night.', 'Benefits from Concerto Partners, with the details to use them.<br>Availability depends on the venue, tour, and dates.', '', ['Offered by Concerto Partners', 'Always labeled'], 'gold')
    live = section('white', 'Available Perks', 'What is on right now.', '<div class="c-perks" data-live-perks aria-live="polite"><p class="c-body">Loading current partner benefits…</p><noscript><p class="c-body">Enable JavaScript to check current availability, or open Concerto.</p></noscript></div>')
    before = section('cream', 'Before you use one', 'Know what is included.', '<p class="c-body">Read the redemption instructions, dates, and conditions before you go.<br>Perks come from Concerto Partners, always labeled.</p>', narrow=True)
    return '<main id="main-content" class="c-page">' + h + live + before + close() + '</main>'

def search_page():
    box = ('<label class="c-filter c-filter-lg"><span class="c-sr">Search Concerto</span><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.75" cy="10.75" r="6.75"/><path d="m16 16 4.5 4.5" stroke-linecap="round"/></svg>'
           '<input data-site-search type="search" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Venue, artist, tour, or city" aria-label="Search Concerto"></label>')
    h = hero('Search', 'Where’s the show?', 'Find a venue, artist, tour, city, or setlist.', box, None, 'cream', 'c-hero-hub')
    return '<main id="main-content" class="c-page">' + h + '<section class="c-section c-white c-search-section"><div class="c-wrap"><div data-site-search-results class="site-search-results c-search-results" aria-live="polite"><p class="c-body">Try an artist, tour, venue, or city.</p></div></div></section></main>'

def simple(kicker, h1, lead, actions):
    return '<main id="main-content" class="c-page">' + hero(kicker, h1, lead, actions, None, 'cream', 'c-hero-simple') + '</main>'

# ----- documents: Help, FAQ, Privacy, Terms keep their exact text -----
def legacy_body(src):
    m = src.split('<main', 1)[1]; m = m[m.find('>') + 1:]; m = m.split('</main>')[0]
    first = m.find('</section>')
    body = m[first + len('</section>'):] if first >= 0 else m
    body = re.sub(r'\sclass="[^"]*"', '', body); body = re.sub(r'\sstyle="[^"]*"', '', body)
    body = re.sub(r'<h1\b[^>]*>(.*?)</h1>', r'<h2>\1</h2>', body, flags=re.S)
    return body

def doc_page(src, kicker, h1, lead, tone='cream', legal=False):
    eff = re.search(r'Effective(?: Date:)?\s*([A-Z][a-z]+ \d{1,2}, \d{4})', src)
    items = [f'Effective {eff.group(1)}'] if (legal and eff) else None
    # Idempotent: Privacy, Terms, and Help are hand-written files, so on a rebuild the
    # source is our own previous output. Reuse its document body exactly instead of
    # wrapping it again (which nested one level deeper on every build).
    if 'c-doc-section' in src:
        body = src.split('<div class="c-wrap c-doc">', 1)[1].rsplit('</div></section></main>', 1)[0]
    else:
        body = legacy_body(src)
    return '<main id="main-content" class="c-page">' + hero(kicker, h1, lead, '', items, tone, 'c-hero-doc') + f'<section class="c-section c-white c-doc-section"><div class="c-wrap c-doc">{body}</div></section></main>'

def build():
    legacy = {f: (ROOT / f).read_text() for f in ['help.html', 'faq.html', 'privacy.html', 'terms.html', 'contact.html', 'partner-venues.html', 'partner-restaurants.html', 'partner-hotels.html', 'partner-artists.html']}
    form_of = lambda f: re.search(r'<form.*?</form>', legacy[f], re.S).group(0)
    rewrite('index.html', home()); rewrite('your-night.html', your_night()); rewrite('premium.html', premium()); rewrite('about.html', about())
    rewrite('venues.html', venues_hub()); rewrite('tours.html', tours_hub()); rewrite('setlists.html', setlists_hub()); rewrite('bagcheck.html', bagcheck())
    rewrite('bags.html', topic_page('bagPolicy', 'Bag policies', 'Concert bag policies,<br>venue by venue.', f'The bag rule at {N_V} venues, from each venue’s published policy, dated.'))
    rewrite('parking.html', topic_page('parking', 'Parking', 'Concert parking,<br>venue by venue.', 'Lots, garages, and routes. From official sources, dated.'))
    rewrite('rideshare.html', topic_page('rideshare', 'Rideshare', 'Drop-off and pickup,<br>venue by venue.', 'Where rideshare goes, before and after. Unconfirmed says unconfirmed.'))
    rewrite('concessions.html', topic_page('concessions', 'Food and drink', 'What is inside,<br>venue by venue.', 'Food, drink, and payment. From official sources, dated.'))
    for v in VENUES: rewrite(f'venue/{v["id"]}.html', venue_page(v))
    for t in TOURS: rewrite(f'tour/{t["tourId"]}.html', tour_page(t))
    for k, s in LIVE.items(): rewrite(f'setlist/{k}.html', setlist_page(k, s))
    rewrite('press.html', press()); rewrite('investors.html', investors()); rewrite('creators.html', creators()); rewrite('partners.html', partners_hub())
    for k in PARTNER: rewrite(f'{k}.html', partner_page(k, form_of(f'{k}.html')))
    rewrite('contact.html', contact_page(form_of('contact.html')))
    rewrite('near-me.html', near_me()); rewrite('perks.html', perks_page()); rewrite('search.html', search_page())
    rewrite('help.html', doc_page(legacy['help.html'], 'Help Center', 'Answers, in plain terms.', 'How Concerto works, from saving your first show to Your Night, Concerto+, and account controls.'))
    rewrite('faq.html', doc_page(legacy['faq.html'], 'FAQ', 'Questions, answered.', 'What Concerto is, what stays free, what Your Night is, and what Concerto+ adds.'))
    rewrite('privacy.html', doc_page(legacy['privacy.html'], 'Legal', 'Privacy Policy.', 'What we collect, why, and the controls you have over it.', 'white', True))
    rewrite('terms.html', doc_page(legacy['terms.html'], 'Legal', 'Terms of Service.', 'The rules for using Concerto, in plain sections.', 'white', True))
    rewrite('partners-thank-you.html', simple('Inquiry received', 'Thank you for<br>reaching out.', 'Concerto will review the fit and contact you at the email you provided if there is a next step. This does not activate a partnership or publish an offer.', '<a class="c-link" href="/partners">Back to Partners</a>'))
    if (ROOT / 'contact-thank-you.html').exists():
        rewrite('contact-thank-you.html', simple('Message received', 'We have it.', 'Thanks for reaching out to Concerto. Your message is in the right place, and we will route it from the details you provided.', '<a class="c-link" href="/">Back to Concerto</a><a class="c-link" href="/about">About the company</a>'))
    rewrite('404.html', simple('Error 404', 'This page left<br>before the encore.', f'The page you are looking for does not exist or has moved. Everything else is still here, including guides for {N_V} venues.', '<a class="c-btn c-btn-navy" href="/">Back to Concerto</a><a class="c-link" href="/venues">Venue guides</a><a class="c-link" href="/search">Search</a>'))
    print(f'V8.1 site written: {N_V} venues, {N_T} tours, {len(LIVE)} setlists, and every company, partner, support, and legal page')


# ---------------- writer ----------------
def rewrite(rel, main):
    path = ROOT / rel
    src = path.read_text()
    i = src.find('<main'); j = src.find(FOOTER_START)
    if i < 0 or j < 0: raise SystemExit(f'{rel}: missing main or footer marker')
    src = src[:i] + main + src[j:]
    src = src.replace('<body class="public-site">', '<body class="public-site v8">', 1)
    path.write_text(src)

def restyle(rel):
    path = ROOT / rel
    if not path.exists(): return
    src = path.read_text()
    # No imitation app UI anywhere: drop any card a previous version inserted.
    src = re.sub(r'<figure class="night-card[^"]*"[^>]*>.*?</figure>', '', src, flags=re.S)
    if 'class="public-site v8"' not in src:
        src = src.replace('<body class="public-site">', '<body class="public-site v8 v8-legacy">', 1)
    path.write_text(src)

def _build_v8_0():
    rewrite('index.html', home()); rewrite('your-night.html', your_night()); rewrite('premium.html', premium()); rewrite('about.html', about())
    rewrite('venues.html', venues_hub()); rewrite('tours.html', tours_hub()); rewrite('setlists.html', setlists_hub()); rewrite('bagcheck.html', bagcheck())
    rewrite('bags.html', topic_page('bagPolicy', 'Bag policies', 'Concert bag policies,<br>venue by venue.', f'The bag rule at each of {N_V} venues, from the venue’s own published policy, with the date it was checked.'))
    rewrite('parking.html', topic_page('parking', 'Parking', 'Concert parking,<br>venue by venue.', 'Lots, garages, and routes for each venue, from official sources and dated.'))
    rewrite('rideshare.html', topic_page('rideshare', 'Rideshare', 'Drop-off and pickup,<br>venue by venue.', 'Where rideshare goes before and after the show, and where it is not confirmed, the page says so.'))
    rewrite('concessions.html', topic_page('concessions', 'Food and drink', 'What is inside,<br>venue by venue.', 'Food, drink, and payment at each venue, from official sources and dated.'))
    for v in VENUES: rewrite(f'venue/{v["id"]}.html', venue_page(v))
    for t in TOURS: rewrite(f'tour/{t["tourId"]}.html', tour_page(t))
    for k, s in LIVE.items(): rewrite(f'setlist/{k}.html', setlist_page(k, s))
    for f in ['near-me.html', 'perks.html', 'partners.html', 'partner-restaurants.html', 'partner-hotels.html', 'partner-venues.html', 'partner-artists.html', 'creators.html', 'press.html',
              'investors.html', 'contact.html', 'faq.html', 'help.html', 'privacy.html', 'terms.html', 'partners-thank-you.html', 'search.html', '404.html']:
        restyle(f)
    print(f'V8 site written: home, your-night, premium, about, 3 hubs, 5 topic pages, {N_V} venues, {N_T} tours, {len(LIVE)} setlists')

if __name__ == '__main__':
    build()
