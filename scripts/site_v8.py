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
def store_button(ct, label='Download on the App Store'):
    return f'<a class="c-btn c-btn-gold" href="{STORE(ct)}" target="_blank" rel="noopener"><svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M16.37 12.6c-.02-2.2 1.8-3.26 1.88-3.31-1.03-1.5-2.62-1.7-3.19-1.73-1.36-.14-2.65.8-3.34.8-.69 0-1.75-.78-2.88-.76-1.48.02-2.85.86-3.61 2.19-1.54 2.67-.39 6.62 1.11 8.79.73 1.06 1.6 2.25 2.74 2.21 1.1-.04 1.52-.71 2.85-.71 1.33 0 1.71.71 2.87.69 1.19-.02 1.94-1.08 2.66-2.14.84-1.23 1.19-2.42 1.21-2.48-.03-.01-2.31-.89-2.3-3.55zM14.2 6.13c.61-.74 1.02-1.76.9-2.78-.88.04-1.94.58-2.57 1.32-.56.65-1.06 1.7-.93 2.7.98.08 1.98-.5 2.6-1.24z"/></svg>{label}</a>'

def close(title='See you at the show.', ct='website-close'):
    return (f'<section class="c-close" data-reveal><div class="c-wrap"><h2>{title}</h2><div class="c-close-row">{store_button(ct)}'
            f'<img class="c-qr" src="/img/appstore-qr.png" width="96" height="96" alt="QR code: Concerto on the App Store" loading="lazy"></div>'
            '<p class="c-fine">Free on iPhone. Concerto+ available in the app.</p></div></section>')

def eyebrow(t): return f'<p class="c-eyebrow">{e(t)}</p>'

def principles():
    items = [('Accurate before clever.', 'Every venue section is researched from official sources and carries the date it was checked.'),
             ('Honest about the unknown.', 'When a time, a rule, or a setlist is not confirmed, Concerto says so instead of guessing.'),
             ('The essentials are free.', 'Bag policy, entry, parking, rideshare, accessibility, and setlists never sit behind a paywall.'),
             ('Partners are labeled.', 'When a restaurant, hotel, or venue appears because it partners with Concerto, it says so. Always.')]
    cells = ''.join(f'<div class="c-principle"><span>0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p></div>' for i, (h, t) in enumerate(items))
    return f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("What we believe")}<h2 class="c-h2">The night deserves accuracy.</h2><div class="c-principles">{cells}</div></div></section>'

def name_section():
    return ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-narrow">' + eyebrow('Why Concerto') +
            '<p class="c-statement">A concerto is written for a soloist and an orchestra. On a show night, the artist is the soloist. '
            'The venue, the city, the dinner before, and the ride home are the orchestra.</p>'
            '<p class="c-statement-after">We build for the orchestra, so the soloist gets your full attention.</p></div></section>')

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
def home():
    hero = (f'<section class="c-hero"><div class="c-wrap c-hero-grid"><div class="c-hero-copy">{eyebrow("The concert-night companion")}'
            '<h1>From the concert<br>to the city.</h1>'
            '<p class="c-lead">Concerto keeps everything around a live show in one place: the venue’s rules, the music, the city, and the way home. So the night can be about the night.</p>'
            f'<div class="c-actions">{store_button("website-home")}<a class="c-link c-link-light" href="#what">What Concerto does</a></div></div>'
            '<figure class="c-hero-photo"><img src="/img/cityguides/kia-forum/Kia-Forum.webp" alt="The Kia Forum, Inglewood, California" width="1042" height="731" fetchpriority="high">'
            '<figcaption>The Kia Forum, Inglewood</figcaption></figure></div>'
            f'<div class="c-wrap c-hero-strip"><span>{N_V} venue guides</span><span>{N_T} tours</span><span>{N_S} setlists</span><span>Free on iPhone</span></div></section>')
    rows = [('Know the venue.', f'Bag policy, entrances, parking, rideshare, and accessibility for {N_V} venues, each researched from official sources and dated.', '/venues', f'Browse {N_V} venue guides'),
            ('Know the music.', f'Tour dates and setlists for {N_T} tours, labeled by where they came from, so you can learn the songs before doors.', '/tours', 'Browse tours and setlists'),
            ('Know the night.', 'Save a show and Your Night keeps it all on one page, from the first reminder to the ride home.', '/your-night', 'How Your Night works')]
    what = (f'<section class="c-section c-white" id="what" data-reveal><div class="c-wrap">{eyebrow("What Concerto does")}<h2 class="c-h2">Three things, done carefully.</h2><ol class="c-rows">'
            + ''.join(f'<li><span class="c-num">0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p><a class="c-link" href="{u}">{e(l)}</a></li>' for i, (h, t, u, l) in enumerate(rows)) + '</ol></div></section>')
    plus = ('<section class="c-section c-gold" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Concerto+') +
            '<h2 class="c-h2">For the nights you want planned.</h2><p class="c-body">Plan My Night, AI Bag Check, and show-day alerts, built around the show you saved. $7.99 a month or $69.99 a year, with a 7-day free trial.</p>'
            '<a class="c-link" href="/premium">Explore Concerto+</a></div><p class="c-pull">Dinner at 5:45.<br>Out the door at 7:10.<br>Lights down at 7:30.</p></div></section>')
    partners = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('For venues and partners') +
                '<h2 class="c-h2">Built with the rooms we cover.</h2></div><div><p class="c-body">Venues can verify their own page, post stage times, and correct their information through the Concerto Partner Console. Restaurants and hotels near the venue can reach fans on show night, clearly labeled.</p>'
                '<div class="c-actions"><a class="c-link" href="/partners">Partner with Concerto</a><a class="c-link" href="/console/">Partner Console</a></div></div></div></section>')
    return '<main id="main-content" class="c-page">' + hero + name_section() + what + photo_band() + numbers() + principles() + plus + partners + guide_index() + close() + '</main>'

def your_night():
    stages = [('Weeks out', 'Learn the songs. Know the rules.', 'The tour’s setlist, labeled by where it came from. The venue’s bag policy, entrances, and parking, each with the date it was checked.'),
              ('The week of', 'The forecast arrives. The plan comes together.', 'Weather appears seven days out and never sooner. Places to eat and drink near the venue, with partners always labeled.'),
              ('Show day', 'Leave on time. Walk in ready.', 'Show-day alerts in the venue’s own time zone. Directions, parking, and rideshare in one place.'),
              ('After the encore', 'The way home is already there.', 'The venue’s published pickup guidance and your ride, kept with the show.')]
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
    feats = [('Plan My Night', 'A plan for the evening around the show you saved: when to eat, when to leave, and how you get home.'),
             ('AI Bag Check', 'Compare your bag with the venue’s published policy before you leave. It shows the rule it used, and the venue still makes the final call.'),
             ('Show-day alerts', 'The morning forecast, a reminder before you head out, and the way home after the encore, in the venue’s time zone.')]
    rows = ''.join(f'<li><span class="c-num">0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p></li>' for i, (h, t) in enumerate(feats))
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type"><div class="c-wrap c-narrow">{eyebrow("Concerto+")}<h1>For the nights<br>you want planned.</h1><p class="c-lead">Concerto+ adds planning to the free app: an evening built around your show, a check of your bag against the venue’s rule, and alerts on show day.</p><div class="c-actions">{store_button("website-premium", "Start the 7-day free trial")}</div></div></section>'
            f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("What is included")}<h2 class="c-h2">Three things the free app does not do.</h2><ol class="c-rows">{rows}</ol></div></section>'
            '<section class="c-section c-cream" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Pricing') + '<h2 class="c-h2">Simple, and cancel anytime.</h2><p class="c-body">Billed through the App Store. Manage or cancel in your Apple ID settings.</p></div>'
            '<div class="c-prices"><div><b>$7.99</b><span>per month, with a 7-day free trial</span></div><div><b>$69.99</b><span>per year</span></div></div></div></section>'
            '<section class="c-section c-white" data-reveal><div class="c-wrap c-narrow">' + eyebrow('Always free') + '<p class="c-statement">Bag policy, entrances, parking, rideshare, accessibility, setlists, and directions never sit behind Concerto+.</p></div></section>'
            + close('Start with the app.', 'website-premium') + '</main>')

def about():
    facts = [('Founded', 'Dallas–Fort Worth'), ('Company', 'Concerto LLC'), ('Product', 'Concerto for iPhone'), ('Coverage', f'{N_V} venues, {N_T} tours')]
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type"><div class="c-wrap c-narrow">{eyebrow("About Concerto")}<h1>The ticket is the start<br>of the night.</h1><p class="c-lead">Concerto brings the practical details around a concert into one place, so fans spend less time piecing them together and more time at the show.</p></div></section>'
            + name_section() +
            '<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('The founder') + '<h2 class="c-h2">Jayce Wells</h2><p class="c-role">Founder</p></div>'
            '<div><p class="c-body">Jayce founded Concerto in Dallas–Fort Worth around a straightforward problem: having a ticket does not mean having the rest of the night figured out. The bag policy, the parking, dinner, the setlist, and the ride home can each send a fan somewhere different.</p>'
            '<p class="c-body">Concerto brings those questions back to the show. It is a founder-led company with a focused aim: make preparing for a concert easier, and the night around it better.</p></div></div></section>'
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
    return ('<main id="main-content" class="c-page">' + hub_intro('Venue guides', f'{N_V} venues.<br>Every rule, checked.', 'Bag policy, entrances, parking, rideshare, and accessibility for each venue, researched from official sources and dated.', 'Search venues or cities', '.c-entry')
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
    return ('<main id="main-content" class="c-page">' + hub_intro('Tours', f'{N_T} tours<br>on the road.', f'Tour guides with dates, the official tour site, and setlists for {N_S} tours, labeled by where they came from.', 'Search artists or tours', '.c-entry')
            + f'<section class="c-section c-white"><div class="c-wrap c-directory">{body}</div></section>' + close() + '</main>')

def setlists_hub():
    items = sorted(LIVE.items(), key=lambda kv: (kv[1].get('artist') or '').lower())
    body = '<div class="c-group"><ul>' + ''.join(f'<li class="c-entry"><a href="/setlist/{k}">{e(v.get("artist"))}</a><span>{e(v.get("tour"))} · {songs_word(len(v["songs"]))}</span></li>' for k, v in items) + '</ul></div>'
    return ('<main id="main-content" class="c-page">' + hub_intro('Setlists', f'{N_S} setlists,<br>labeled by source.', 'Official tour playlists and confirmed setlists, each marked with where it came from and when it was updated. Setlists change by night.', 'Search artists', '.c-entry')
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
            f'<p class="c-lead">What to know before a show at {e(v["name"])}: the bag policy, entrances, parking, rideshare, and accessibility, from official sources.</p>'
            f'<div class="c-actions">{app_link("venue", v["id"], "Open in Concerto", "c-btn c-btn-navy")}</div>'
            f'<div class="tonight" data-venue-tonight data-name="{e(v["name"])}" data-country="{e(v.get("country") or "")}" data-lat="{e(v.get("lat"))}" data-lng="{e(v.get("lng"))}"></div></div>'
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
    steps = [('Pick the venue.', 'Bag Check starts from the same verified venue policy used throughout Concerto.'), ('Show Concerto the bag.', 'Compare the size and type of your bag against the venue’s published limits.'), ('Leave with context.', 'It explains the rule it used and what is uncertain. The venue always makes the final call.')]
    rows = ''.join(f'<li><span class="c-num">0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p></li>' for i, (h, t) in enumerate(steps))
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type"><div class="c-wrap c-narrow">{eyebrow("Concerto+ · AI Bag Check")}<h1>Check the bag<br>before the door.</h1><p class="c-lead">Compare what you plan to bring with the venue’s published bag policy, before you leave the house.</p><div class="c-actions">{store_button("website-bagcheck")}<a class="c-link" href="/bags">Read bag policies</a></div></div></section>'
            f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("How it works")}<h2 class="c-h2">Three steps, one answer.</h2><ol class="c-rows">{rows}</ol></div></section>'
            + close('Pack once.', 'website-bagcheck') + '</main>')

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

def build():
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
