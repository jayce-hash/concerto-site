import json
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
from venue_glance import glance as venue_glance

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
    if src.get('eventDate') and src.get('provider') == 'setlist.fm': return f"Reported setlist from {src.get('venue') or 'a recent show'}, {pretty_date(src['eventDate'])} (setlist.fm)"
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

def close(title='See you at the show.', ct='website-close', fine='Free on iPhone. Concerto+ available in the app.'):
    return (f'<section class="c-close" data-reveal><div class="c-wrap">'
            '<img class="c-appicon" src="/img/app-icon-256.png" width="96" height="96" alt="Concerto app icon" loading="lazy">'
            f'<h2>{title}</h2><div class="c-close-row">{store_button(ct, tone="white")}'
            '<img class="c-qr" src="/img/appstore-qr.png" width="104" height="104" alt="QR code: Concerto on the App Store" loading="lazy"></div>'
            f'<p class="c-fine">{e(fine)}</p></div></section>')

def eyebrow(t): return f'<p class="c-eyebrow">{e(t)}</p>'

def principles():
    items = [('Accurate before clever.', 'Researched from official sources. Dated, every time.'),
             ('Honest about the unknown.', 'Not confirmed? Concerto says so instead of guessing.'),
             ('The essentials are free.', 'Venue guides, setlists, places nearby, and Your Night. Never paywalled.'),
             ('Private by default.', 'Ticket screenshots and photos stay on your phone.')]
    cells = ''.join(f'<div class="c-principle"><span>0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p></div>' for i, (h, t) in enumerate(items))
    return f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("What we believe")}<h2 class="c-h2">The night deserves accuracy.</h2><div class="c-principles">{cells}</div></div></section>'

def name_section():
    return ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-narrow">' + eyebrow('Why Concerto') +
            '<p class="c-statement">A concerto is written for a soloist and an orchestra.<br>The artist is the soloist. The venue, the city, and the ride home are the orchestra.</p>'
            '<p class="c-statement-after">Concerto is built for everything around the show.</p></div></section>')

def photo_band(title='Every room has rules. We read them first.'):
    tiles = ''
    for slug, fname in PHOTOS:
        v = VBY.get(slug)
        if not v: continue
        tiles += (f'<a class="c-photo" href="/venue/{slug}"><img src="/img/cityguides/{slug}/{fname}.webp" alt="{e(v["name"])}, {e(place(v))}" loading="lazy" width="800" height="560">'
                  f'<span class="c-photo-cap"><b>{e(v["name"])}</b><span>{e(place(v))}</span></span></a>')
    return f'<section class="c-section c-white c-photos-section" data-reveal><div class="c-wrap">{eyebrow("The rooms")}<h2 class="c-h2">{title}</h2></div><div class="c-photos">{tiles}</div></section>'

def numbers():
    items = [(V_COPY, 'venue guides'), (N_T, 'tours followed'), (N_S, 'setlists live'), (8, 'essentials per venue')]
    return '<section class="c-numbers" data-reveal><div class="c-wrap c-numbers-row">' + ''.join(f'<div><b>{n}</b><span>{e(l)}</span></div>' for n, l in items) + '</div></section>'

# Demand, from Google Search Console (Jul 13 to Oct 12, 2026): about 1,450 search appearances a
# day in the first week, about 12,050 in the last; average position 10.3 then, 9.0 now. Update
# these four values when the numbers move; every page that shows the proof reads them from here.
PROOF_DAY, PROOF_GROWTH, PROOF_POS, PROOF_AS_OF = '12,000', '8×', '9.0', 'October 2026'

def proof_strip():
    items = [(PROOF_DAY, 'Google search appearances a day'), (PROOF_GROWTH, 'as many as in July'), ('Page one', f'average Google position, {PROOF_POS}')]
    return ('<section class="c-numbers c-proof" data-reveal><div class="c-wrap"><div class="c-numbers-row">'
            + ''.join(f'<div><b>{n}</b><span>{e(l)}</span></div>' for n, l in items)
            + f'</div><p class="c-proof-src">Google Search Console, {PROOF_AS_OF}. Search appearances are times Concerto showed in Google results.</p></div></section>')

def guide_index():
    vs = [VBY[s] for s in FEATURED_VENUES if s in VBY][:12]
    ts = [t for t in TOURS if t['tourId'] in LIVE][:12]
    vcol = ''.join(f'<li><a href="/venue/{v["id"]}">{e(v["name"])}</a><span>{e(place(v))}</span></li>' for v in vs)
    tcol = ''.join(f'<li><a href="/tour/{t["tourId"]}">{e(t["artist"])}</a><span>{e(t["tourName"])}</span></li>' for t in ts)
    topics = [('Bag policies', '/bags', 'Venue by venue'), ('Parking', '/parking', 'Lots, garages, and routes'), ('Rideshare', '/rideshare', 'Drop-off and pickup'),
              ('Food and drink', '/concessions', 'What is inside'), ('Setlists', '/setlists', f'{N_S} tours'), ('Near me', '/near-me', 'Shows this week')]
    pcol = ''.join(f'<li><a href="{h}">{e(l)}</a><span>{e(d)}</span></li>' for l, h, d in topics)
    return (f'<section class="c-section c-cream" data-reveal><div class="c-wrap">{eyebrow("The guide")}<h2 class="c-h2">Start with where you are going.</h2>'
            f'<div class="c-index"><div><h3>Venues</h3><ul>{vcol}</ul><a class="c-more" href="/venues">All {V_COPY} venues</a></div>'
            f'<div><h3>Tours</h3><ul>{tcol}</ul><a class="c-more" href="/tours">All {N_T} tours</a></div>'
            f'<div><h3>Topics</h3><ul>{pcol}</ul><a class="c-more" href="/search">Search the guide</a></div></div></div></section>')

# ---------------- pages ----------------

def problem_section():
    # The homepage names the fan's problem in their own words. The story of the name is a good
    # one, but it explains Concerto rather than the night, so it lives on About instead.
    return ('<section class="c-section c-navy" data-reveal><div class="c-wrap c-narrow">' + eyebrow('The problem') +
            '<p class="c-statement">A ticket has the date and the venue.<br>Planning the rest usually takes five different apps.</p>'
            '<p class="c-statement-after">What can I bring in? Where do I park? Where should we eat before the show?<br>'
            'One page. Every answer sourced and dated.</p></div></section>')

def home():
    hero = (f'<section class="c-hero"><div class="c-wrap c-hero-grid"><div class="c-hero-copy">{eyebrow("The concert-night companion")}'
            '<h1>From the Concert<br>to the City</h1>'
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
            '<h2 class="c-h2">More of Your Night.</h2><p class="c-body">Exit Plan. AI Bag Check. Plan My Night.<br>' + e(PLUS_PRICE_LINE) + '</p>'
            '<a class="c-link" href="/premium">Explore Concerto+</a></div><p class="c-pull">Dinner at 5:45.<br>Out the door at 7:10.<br>Lights down at 7:30.</p></div></section>')
    partners = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('For venues and partners') +
                '<h2 class="c-h2">Built with the rooms we cover.</h2></div><div><p class="c-body">Venues verify their own page and post stage times.<br>Restaurants and hotels reach fans on show night, always labeled.</p>'
                '<div class="c-actions"><a class="c-link" href="/partners">Partner with Concerto</a></div></div></div></section>')
    return '<main id="main-content" class="c-page">' + hero + name_section() + what + photo_band() + numbers() + principles() + plus + partners + guide_index() + close() + '</main>'

def your_night():
    stages = [('Weeks out', 'Learn the songs. Know the rules.', 'The setlist, labeled by source. Bag policy, entry, and parking, each dated.'),
              ('The week of', 'The forecast arrives. The plan comes together.', 'Weather at seven days out, never sooner. Places to eat nearby, partners labeled.'),
              ('Show day', 'Leave on time. Walk in ready.', 'Alerts in the venue’s time zone. Directions, parking, and rideshare in one place.'),
              ('After the encore', 'The way home is already there.', 'The venue’s pickup guidance and your ride, kept with the show.')]
    tl = ''.join(f'<li><span class="c-when">{e(w)}</span><h3>{e(h)}</h3><p>{e(t)}</p></li>' for w, h, t in stages)
    free = ['Saving shows, from Concerto or your calendar', 'Your Night for every saved show', 'A show-day reminder for every saved show', f'Venue guides for {N_V} venues', 'Setlists, labeled by source', 'Directions, parking, and rideshare']
    paid = ['Plan My Night: the evening, built around your show', 'AI Bag Check against the venue’s policy', 'More show-day alerts: before you leave and the way home', 'More Concerto AI answers each day']
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
             ('More show-day alerts', 'A nudge before you leave, the way home after the encore, and a recap the next morning. The 9am show-day reminder is free.')]
    rows = ''.join(f'<li><span class="c-num">0{i+1}</span><h3>{e(h)}</h3><p>{e(t)}</p></li>' for i, (h, t) in enumerate(feats))
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type"><div class="c-wrap c-narrow">{eyebrow("Concerto+")}<h1>For the nights<br>you want planned.</h1><p class="c-lead">An evening built around your show. Your bag checked against the venue’s rule. More alerts on show day.</p><div class="c-actions">{store_button("website-premium", "Start the 7-day free trial")}</div></div></section>'
            f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("What is included")}<h2 class="c-h2">Three things the free app does not do.</h2><ol class="c-rows">{rows}</ol></div></section>'
            '<section class="c-section c-cream" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Pricing') + '<h2 class="c-h2">Simple, and cancel anytime.</h2><p class="c-body">Billed through the App Store. Cancel in your Apple ID settings.</p></div>'
            '<div class="c-prices"><div><b>$7.99</b><span>per month, with a 7-day free trial</span></div><div><b>$69.99</b><span>per year</span></div></div></div></section>'
            '<section class="c-section c-white" data-reveal><div class="c-wrap c-narrow">' + eyebrow('Always free') + '<p class="c-statement">Bag policy, entry, parking, accessibility, setlists, directions.<br>Never behind Concerto+.</p></div></section>'
            + close('Start with the app.', 'website-premium') + '</main>')

def about():
    facts = [('Founded', 'March 2025'), ('Company', 'Concerto LLC'), ('Product', 'Concerto for iPhone'), ('Coverage', f'{N_V} venues, {N_T} tours')]
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-type"><div class="c-wrap c-narrow">{eyebrow("About Concerto")}<h1>The ticket is the start<br>of the night.</h1><p class="c-lead">The practical details around a concert, in one place.<br>Less piecing it together. More of the show.</p></div></section>'
            + name_section() +
            '<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('The founder') + '<h2 class="c-h2">Jayce Wells</h2><p class="c-role">Founder</p></div>'
            '<div><p class="c-body">A ticket does not mean the night is figured out. The bag policy, the parking, dinner, the setlist, the ride home: each sends a fan somewhere different.</p>'
            '<p class="c-body">Concerto brings those questions back to the show. Founder-led.</p></div></div></section>'
            + principles() +
            '<section class="c-numbers" data-reveal><div class="c-wrap c-facts">' + ''.join(f'<div><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in facts) + '</div></section>'
            '<section class="c-section c-cream" data-reveal><div class="c-wrap c-links-row"><a class="c-link" href="/press">Press</a><a class="c-link" href="/investors">Investors</a><a class="c-link" href="/contact">Contact</a></div></section>'
            + close() + '</main>')

def hub_intro(kicker, h1, lead, placeholder, target):
    return (f'<section class="c-hero c-hero-type c-hero-hub"><div class="c-wrap">{eyebrow(kicker)}<h1>{h1}</h1><p class="c-lead">{lead}</p>'
            f'<label class="c-filter"><span class="c-sr">{e(placeholder)}</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.75" cy="10.75" r="6.75"/><path d="m16 16 4.5 4.5" stroke-linecap="round"/></svg>'
            f'<input type="search" placeholder="{e(placeholder)}" data-filter-target="{target}" autocomplete="off"></label></div></section>')

def request_form(kind):
    """'Missing a venue or tour? Tell us.' Posts to the existing report inbox as a request."""
    noun = 'venue' if kind == 'venue' else 'tour'
    ph = 'Venue name and city' if kind == 'venue' else 'Artist and tour name'
    return (f'<section class="c-section c-cream"><div class="c-wrap c-narrow">{eyebrow("Not here yet?")}'
            f'<h2 class="c-h2 c-h2-sm">Missing a {noun}?<br>Tell us.</h2>'
            f'<form class="c-request" data-request="{noun}"><label class="c-sr" for="req-{noun}">{ph}</label>'
            f'<input id="req-{noun}" name="message" maxlength="200" required placeholder="{ph}">'
            f'<button class="c-btn c-btn-navy" type="submit">Send</button></form>'
            f'<p class="c-request-note" aria-live="polite">We read every request.</p></div></section>')


def venues_hub():
    groups = {}
    for v in sorted(VENUES, key=lambda x: (x.get('country') != 'US', x.get('state') or x.get('country') or '', x['name'])):
        key = v.get('state') if v.get('country') == 'US' and v.get('state') else (v.get('country') or 'Other')
        groups.setdefault(key, []).append(v)
    body = ''.join(f'<div class="c-group"><h2>{e(k)}</h2><ul>' + ''.join(f'<li class="c-entry"><a href="/venue/{v["id"]}">{e(v["name"])}</a><span>{e(v.get("city"))}</span></li>' for v in vs) + '</ul></div>' for k, vs in groups.items())
    return ('<main id="main-content" class="c-page">' + hub_intro('Venue guides', f'{N_V} venues.<br>Every rule, checked.', 'Bag policy, entry, parking, rideshare, accessibility.<br>From official sources, dated.', 'Search venues or cities', '.c-entry')
            + f'<section class="c-section c-white"><div class="c-wrap c-directory">{body}</div></section>' + request_form('venue') + close() + '</main>')

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
            + f'<section class="c-section c-white"><div class="c-wrap c-directory">{body}</div></section>' + request_form('tour') + close() + '</main>')

def setlists_hub():
    items = sorted(LIVE.items(), key=lambda kv: (kv[1].get('artist') or '').lower())
    body = '<div class="c-group"><ul>' + ''.join(f'<li class="c-entry"><a href="/setlist/{k}">{e(v.get("artist"))}</a><span>{e(v.get("tour"))} · {songs_word(len(v["songs"]))}</span></li>' for k, v in items) + '</ul></div>'
    return ('<main id="main-content" class="c-page">' + hub_intro('Setlists', f'{N_S} setlists,<br>labeled by source.', 'Official tour playlists and confirmed setlists, each marked with its source and date. Setlists change by night.', 'Search artists', '.c-entry')
            + f'<section class="c-section c-white"><div class="c-wrap c-directory c-directory-one">{body}</div></section>' + close() + '</main>')

# Hidden on the website until the place data is curated (apartments were showing as hotels).
# Flip to True to bring the section back; nothing else changes.
AROUND_THE_VENUE_ON = False

def around_venue(v):
    if not AROUND_THE_VENUE_ON: return ''
    """Restaurants, hotels and more around a venue, from its nearby file, as real HTML so search
    engines can read it ("restaurants near American Airlines Center"). Same data as the app.
    Google Places content: attributed beside it, linked by place ID, refreshed monthly."""
    from urllib.parse import quote
    f = ROOT / 'data' / 'nearby' / f"{v['id']}.json"
    try: d = json.loads(f.read_text())
    except Exception: return ''
    cols = []
    for key, title in (('restaurants', 'Restaurants'), ('hotels', 'Hotels'), ('more', 'More nearby')):
        # Convenience stores, pharmacies, gas and groceries are in Google's results but are not recommendations.
        skip = {'convenience_store', 'gas_station', 'pharmacy', 'drugstore', 'supermarket', 'grocery_store', 'atm', 'bank', 'car_wash', 'car_repair', 'parking', 'apartment_building', 'apartment_complex', 'condominium_complex', 'housing_complex', 'real_estate_agency', 'travel_agency'}  # same list as the app
        items = [x for x in ((d.get('tabs') or {}).get(key) or {}).get('items') or []
                 if x.get('name') and not (set(x.get('types') or []) & skip)][:6]
        if not items: continue
        lis = []
        for x in items:
            mi = x.get('distance_mi'); walk = f"{max(1, round((mi or 0) * 20))} min walk" if mi is not None and mi <= 1.2 else (f"{mi:.1f} mi" if mi is not None else '')
            price = '$' * int(x['price']) if isinstance(x.get('price'), (int, float)) and x['price'] > 0 else ''
            meta = ' \u00b7 '.join(z for z in (walk, price) if z)
            href = f"https://www.google.com/maps/search/?api=1&query={quote(x['name'])}&query_place_id={quote(x['place_id'])}" if x.get('place_id') else ''
            apple = f"https://maps.apple.com/?q={quote(x['name'])}&ll={x['lat']},{x['lng']}" if x.get('lat') is not None and x.get('lng') is not None else ''
            name = (f'<a href="{e(href)}"' + (f' data-apple-maps="{e(apple)}"' if apple else '') + f' target="_blank" rel="noopener nofollow">{e(x["name"])}</a>') if href else e(x['name'])
            lis.append(f'<li>{name}<span>{e(meta)}</span></li>')
        cols.append(f'<div class="c-around-col"><h3>{title}</h3><ul>' + ''.join(lis) + '</ul></div>')
    if not cols: return ''
    return (f'<section class="c-section c-white" data-reveal><div class="c-wrap">{eyebrow("Around the venue")}'
            f'<h2 class="c-h2 c-h2-sm">Near {e(v["name"])}.</h2>'
            f'<div class="c-around">' + ''.join(cols) + '</div>'
            f'<p class="c-source">Places from Google Maps. Walking times are estimates. Open Concerto for the full list and your night plan.</p></div></section>')


def _miles(a, b):
    import math
    try:
        la1, lo1, la2, lo2 = map(math.radians, (float(a['lat']), float(a['lng']), float(b['lat']), float(b['lng'])))
    except Exception:
        return None
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))

def nearby_venues(v, n=6):
    """The closest venue guides by distance, not the first ones alphabetically in the state."""
    rows = [(d, x) for x in VENUES if x['id'] != v['id'] for d in [_miles(v, x)] if d is not None]
    rows.sort(key=lambda r: r[0])
    return rows[:n]

def dist_label(d, country):
    if country in ('US', 'USA', 'GB', 'UK'):
        return 'Less than 1 mile' if d < 1 else f"{d:.0f} miles" if d >= 10 else f"{d:.1f} miles"
    km = d * 1.609
    return 'Less than 1 km' if km < 1 else f"{km:.0f} km" if km >= 10 else f"{km:.1f} km"

def nb_dims(t):
    """Escape, then keep a size like 22" x 14" x 9" on one line."""
    return re.sub(r'(?<=\S) ([x×]) (?=\S)', '&nbsp;\\1&nbsp;', e(t))

def directions_link(v):
    from urllib.parse import quote
    lat, lng = v.get('lat'), v.get('lng')
    if lat is None or lng is None: return ''
    g = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
    a = f"https://maps.apple.com/?daddr={lat},{lng}&q={quote(v['name'])}"
    return f'<a class="c-btn c-btn-line" href="{e(g)}" data-apple-maps="{e(a)}" target="_blank" rel="noopener">Directions</a>'

# ---------- App-style detail pages (venue and tour) ----------
# The website's venue and tour pages share the app's look: a photo card, a serif title, pill
# buttons, chips that jump down the page, and white rounded cards with an icon, a title and the
# date each section was checked. App-only features stay in the app.
# The app's own icons: Ionicons (through @expo/vector-icons), gold, no background tile.
from app_icons import IONICONS, MDI_STADIUM
_ALIAS = {'shield': 'shield-checkmark', 'chev': 'chevron-down', 'pin': 'location', 'music': 'musical-notes',
          'users': 'person-outline', 'info': 'information-circle-outline', 'nav': 'navigate', 'globe': 'globe-outline',
          'bell': 'ticket', 'mic': 'mic', 'stadium': 'stadium'}
def icon(name, size=20):
    name = _ALIAS.get(name, name)
    if name == 'stadium':
        return (f'<svg class="cx-icon" width="{size}" height="{size}" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="{MDI_STADIUM}"/></svg>')
    return (f'<svg class="cx-icon" width="{size}" height="{size}" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true">{IONICONS[name]}</svg>')

# Same icon for each section as the app's venue screen (app/venue/[slug].tsx).
SECTION_ICON = {'bagPolicy': 'bag-check', 'gates': 'enter', 'parking': 'car', 'rideshare': 'car-sport', 'accessibility': 'accessibility',
                'concessions': 'restaurant', 'reEntry': 'repeat', 'ticketPickup': 'ticket'}

def cx_chips(items):
    return '<nav class="cx-chips" aria-label="On this page">' + ''.join(f'<a href="#{a}">{e(l)}</a>' for a, l in items) + '</nav>'

def cx_ver(text, check=True):
    return f'<span class="cx-ver{"" if check else " cx-ver-plain"}">{icon("shield", 14) if check else ""}{e(text)}</span>'

def cx_card(anchor, ic, title, meta, body, open_=False, section=None, check=True, tag='h2'):
    """A collapsible white card: icon, title, the date it was checked, then the content."""
    ds = f' data-section="{e(section)}"' if section else ''
    return (f'<details class="cx-card" id="{anchor}"{ds}{" open" if open_ else ""}><summary>'
            f'<span class="cx-ic">{icon(ic)}</span><span class="cx-tt"><{tag} class="cx-card-t">{e(title)}</{tag}>'
            f'{cx_ver(meta, check) if meta else ""}</span><span class="cx-chev">{icon("chev", 18)}</span></summary>'
            f'<div class="cx-card-b">{body}</div></details>')

def cx_btn(href, label, ic=None, primary=False, attrs=''):
    return (f'<a class="cx-pill{" cx-pill-gold" if primary else ""}" href="{e(href)}"{attrs}>'
            f'{icon(ic, 17) if ic else ""}<span>{e(label)}</span></a>')

def cx_directions(v):
    from urllib.parse import quote
    lat, lng = v.get('lat'), v.get('lng')
    if lat is None or lng is None: return ''
    g = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
    a = f"https://maps.apple.com/?daddr={lat},{lng}&q={quote(v['name'])}"
    return cx_btn(g, 'Directions', 'nav', attrs=f' data-apple-maps="{e(a)}" target="_blank" rel="noopener"')

def cx_app_pill(kind, slug, label, ic):
    """The app deep link, styled as the gold pill. Same link and tracking as app_link()."""
    html = app_link(kind, slug, label, 'cx-pill cx-pill-gold')
    return html.replace('>' + e(label) + '<', '>' + icon(ic, 17) + '<span>' + e(label) + '</span><', 1)


def upcoming_shell(v):
    """Filled by js/public-v6.js from the same Ticketmaster feed the app uses. Hidden until it has shows."""
    return (f'<section class="cx-sec c-upcoming" id="upcoming" data-venue-upcoming hidden aria-labelledby="up-h"><div class="cx-wrap">'
            f'<div class="cx-sec-head"><h2 class="cx-h2" id="up-h">Upcoming shows at {e(v["name"])}</h2></div><ol class="c-up-list"></ol>'
            f'<p class="cx-note">Save a show in Concerto and get its bag rules, doors, and parking on the morning of the show.</p></div></section>')

def venue_page(v):
    info = INFO.get(v['id']) or {}
    cards = []
    for key, label, anchor in SECTIONS:
        x = info.get(key) or {}
        body = x.get('summary') or x.get('note') or x.get('body') or ''
        if not body: continue
        lists = ''
        if x.get('allowed') or x.get('prohibited'):
            col = lambda h, items, cls: (f'<div class="cx-rule {cls}"><h3>{h}</h3><ul>' + ''.join('<li>' + e(a) + '</li>' for a in items) + '</ul></div>') if items else ''
            lists = '<div class="cx-rules">' + col('Allowed', x.get('allowed', []), 'cx-yes') + col('Not allowed', x.get('prohibited', []), 'cx-no') + '</div>'
        src = (f'<div class="link-row cx-links"><a href="{e(x["officialLink"])}" target="_blank" rel="noopener">Official source</a></div>' if x.get('officialLink') else '')
        meta = f'Checked {pretty_date(x.get("verified"))}' if x.get('verified') else 'Not yet verified'
        cards.append(cx_card(anchor, SECTION_ICON.get(key, 'info'), label, meta, f'<p>{e(body)}</p>{lists}{src}',
                             open_=not cards, section=key, check=bool(x.get('verified'))))
    near = nearby_venues(v)
    near_html = ''.join(f'<a class="cx-tile" href="/venue/{x["id"]}"><span class="cx-tile-ic">{icon("pin", 18)}</span><span><b>{e(x["name"])}</b>'
                        f'<small>{e(x.get("city"))} · {dist_label(d, v.get("country"))}</small></span></a>' for d, x in near)
    local = dict(PHOTOS).get(v['id'])
    fb = f' data-fallback-src="/img/cityguides/{v["id"]}/{local}.webp"' if local else ''
    # Answer first: most visitors searched "<venue> bag policy", so the lead is the rule itself.
    bag_line = next((x['value'] for x in venue_glance(info) if x['key'] == 'bag'), None)
    lead = (f'<p class="cx-lead"><b>Bag policy:</b> {nb_dims(bag_line)}.</p>' if bag_line
            else f'<p class="cx-lead">Bag policy, entry, parking, rideshare, and accessibility at {e(v["name"])}, from official sources.</p>')
    photo = f'<div class="c-venue-photo cx-hphoto" data-vphoto data-vname="{e(v["name"])}" data-vcity="{e(v.get("city"))}" data-vlat="{e(v.get("lat"))}" data-vlng="{e(v.get("lng"))}"{fb}></div>'
    chips = cx_chips([('info', 'Venue info'), ('upcoming', 'Upcoming'), ('around', 'Around the venue')] + ([('venues', 'Nearby venues')] if near else []))
    return ('<main id="main-content" class="c-page cx">'
            # Same header as every other page: label, name, place, with a small photo on the right. No jump links.
            + f'<section class="c-hero c-hero-cream c-hero-page"><div class="c-wrap c-hero-inner"><nav class="c-crumbs" aria-label="Breadcrumb"><a href="/venues">Venues</a><span>/</span>{e(v["name"])}</nav>'
            f'{eyebrow("Venue guide")}<h1>{e(v["name"])}</h1><p class="c-lead">{e(place(v))}</p>{photo}'
            # Holds the venue's name and location for the page scripts; not shown.
            f'<div class="tonight cx-tonight" hidden data-venue-tonight data-name="{e(v["name"])}" data-country="{e(ISO.get(v.get("country"), v.get("country") or ""))}" data-lat="{e(v.get("lat"))}" data-lng="{e(v.get("lng"))}"></div></div></section>'
            # Order: Concerto Partners (added by the page script right after the hero), venue info,
            # upcoming shows, places around the venue, nearby venues.
            + f'<section class="cx-sec" id="info"><div class="cx-wrap"><div class="cx-sec-head"><h2 class="cx-h2">Venue info</h2><p class="cx-note">Checked against {e(v["name"])}’s official sources. Tap a section to open it.</p></div><div class="cx-cards">{"".join(cards)}</div></div></section>'
            + upcoming_shell(v)
            + f'<section class="cx-sec" id="around" data-nearby="{e(v["id"])}" data-name="{e(v["name"])}" hidden><div class="cx-wrap"><div class="cx-sec-head"><h2 class="cx-h2">Around {e(v["name"])}</h2><p class="cx-note">Places to eat, stay, and go near the venue. Places from Google.</p></div><div class="cx-rows"></div></div></section>'
            + (f'<section class="cx-sec" id="venues"><div class="cx-wrap"><div class="cx-sec-head"><h2 class="cx-h2">Nearby venues</h2></div><div class="cx-tiles">{near_html}</div></div></section>' if near else '')
            + f'<section class="cx-sec cx-sec-tight"><div class="cx-wrap"><p class="cx-cta-line"><b>Own a restaurant or hotel near {e(v["name"])}?</b> Reach concert fans planning their night here. <a href="/partners/restaurants">For restaurants</a> · <a href="/partners/hotels">For hotels</a></p></div></section>'
            + close('Going to a show here?', 'website-venue', f'Save your show in Concerto. At 9am on show day, it sends you the doors and show time at {v["name"]}, with Your Night one tap away. Free on iPhone.') + '</main>')

RULES = (('bagPolicy', 'Bags'), ('gates', 'Entry'), ('reEntry', 'Re-entry'), ('parking', 'Parking'), ('rideshare', 'Rideshare'))

def _rule_line(sec):
    """One short line from a confirmed guide section; None when the venue has not published it."""
    if not sec: return None
    # Newer guides use "summary"; the original 346 keep the text in "body" or "note".
    t = ' '.join((sec.get('summary') or sec.get('body') or sec.get('note') or '').split())
    # A line saying the venue has not published this is not a rule, whatever the status says.
    if t and re.search(r"(may |can )?var(y|ies) (by|for each|from) (event|show)|event-specific|does not publish one universal", t, re.I) and not re.search(r"\d", t):
        return 'Varies by event. Check your event details before you go'
    if not t or re.search(r"not (explicitly |specifically )?(detailed|confirmed|stated|published|specified|listed)|does not (state|specify|publish)|check the (event|show) listing", t, re.I): return None
    t = re.split(r'(?<=[.!?])\s', t)[0].rstrip('.') if t else ''
    if len(t) > 150: return None  # too long for one line: the full guide covers it
    return t or None

def _bag_answer(sec):
    """The one-line bag answer at the top of a venue page: the first sentence that states a size,
    else the first sentence. None when the venue has not published a rule (generic lead instead)."""
    first = _rule_line(sec)
    if not first: return None
    t = ' '.join((sec.get('summary') or sec.get('body') or sec.get('note') or '').split())
    for x in re.split(r'(?<=[.!?])\s', t)[:3]:
        x = x.rstrip('.')
        if re.search(r'\d', x) and len(x) <= 150: return x
    return first

def city_html(city):
    """Keep each part of a city name together; allow a break only after "/" or ", ". No widows."""
    parts = re.split(r'(/|, )', city)
    return ''.join((e(x) + '<wbr>') if x in ('/', ', ') else e(x).replace(' ', '\u00a0') for x in parts)

def jingle_ball_data():
    """The one file both the website and the app read: lineup, rules, tickets, partner per city."""
    from urllib.parse import quote
    d = json.loads((ROOT / 'data' / 'jingle-ball-2026.json').read_text())
    vname = {v['id']: v['name'] for v in VENUES}
    for c in d['cities']:
        info = INFO.get(c['venue'], {})
        c['venueName'] = vname.get(c['venue'], c['venue'])
        vv = next((v for v in VENUES if v['id'] == c['venue']), {})
        c['lat'], c['lng'] = vv.get('lat'), vv.get('lng')
        if c['lat'] is not None:
            c['uber'] = (f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[latitude]={c['lat']}"
                         f"&dropoff[longitude]={c['lng']}&dropoff[nickname]={quote(c['venueName'])}")
            c['lyft'] = f"https://ride.lyft.com/ridetype?id=lyft&destination[latitude]={c['lat']}&destination[longitude]={c['lng']}"
        # Verified per-city lines win; otherwise fall back to the venue's guide.
        lines = c.get('ruleLines') or {}
        c['rules'] = [{'label': lab, 'text': lines[lab] if lab in lines else _rule_line(info.get(key))} for key, lab in RULES]
        c['tickets'] = c.get('tickets') or f"https://www.ticketmaster.com/search?q={quote('Jingle Ball ' + c['venueName'])}"
        c['dateISO'] = '2026-12-' + {'dallas':'01','los-angeles':'04','chicago':'07','detroit':'08','new-york':'11','boston':'13','washington-dc':'14','philadelphia':'15','nashville':'17'}[c['anchor']]
        hour, minute = {'dallas':(19,30),'los-angeles':(19,30),'chicago':(19,0),'detroit':(19,30),'new-york':(19,0),'boston':(18,0),'washington-dc':(19,30),'philadelphia':(19,30),'nashville':(19,30)}[c['anchor']]
        offset = '-08:00' if c['anchor'] == 'los-angeles' else '-06:00' if c['anchor'] in ('dallas','chicago','nashville') else '-05:00'
        c['dateTime'] = c['dateISO'] + f'T{hour:02}:{minute:02}:00' + offset
        c['timezone'] = 'America/Los_Angeles' if c['anchor'] == 'los-angeles' else 'America/Chicago' if offset == '-06:00' else 'America/New_York'
        c['localTime'] = f'{hour:02}:{minute:02}:00'
        c['directions'] = 'https://www.google.com/maps/search/?api=1&query=' + quote(c['venueName'] + ' ' + c['city'])
        c['rules'] += [{'label': lab, 'text': _rule_line(info.get(key))} for key, lab in [('accessibility','Accessibility'),('ticketPickup','Ticket pickup')]]
        c['setTimes'] = c.get('setTimes') or None
        c['partner'] = c.get('partner') or None
    (ROOT / 'data' / 'jingle-ball-2026-hub.json').write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')) + '\n')
    return d

def jb_countdown():
    """Hero countdown: "62 days until Jingle Ball", a live clock to the showtime, following the
    next show or the city the fan picks. The page script keeps it live."""
    import datetime as _dt, json as _json
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    tz = {'ET': 5, 'CT': 6, 'MT': 7, 'PT': 8}  # December offsets from UTC (standard time)
    items = []
    for c in jingle_ball_data()['cities']:
        m = re.search(r'([A-Z][a-z]{2}) (\d{1,2})', c['date']); t = re.search(r'(\d{1,2}):(\d{2}) (AM|PM) ([A-Z]T)', c['time'])
        if not (m and t): continue
        h = int(t.group(1)) % 12 + (12 if t.group(3) == 'PM' else 0)
        start = _dt.datetime(2026, months.index(m.group(1)) + 1, int(m.group(2)), h, int(t.group(2))) + _dt.timedelta(hours=tz.get(t.group(4), 6))
        items.append({'a': c['anchor'], 'city': c['city'], 'date': c['date'], 'venue': c['venueName'], 't': start.strftime('%Y-%m-%dT%H:%M:00Z')})
    now = _dt.datetime.utcnow()
    nxt = next((x for x in items if _dt.datetime.strptime(x['t'], '%Y-%m-%dT%H:%M:00Z') > now), None)
    if not nxt: return '<div class="c-jb-count"><strong>That\u2019s a wrap on Jingle Ball 2026.</strong></div>'
    days = max(0, (_dt.datetime.strptime(nxt['t'], '%Y-%m-%dT%H:%M:00Z').date() - now.date()).days)
    lead = 'opens the tour' if nxt['a'] == items[0]['a'] else 'is next'
    data = e(_json.dumps(items, separators=(',', ':')))
    return (f'<div class="c-jb-count" data-cities="{data}" aria-live="polite">'
            f'<div class="c-jb-count-big"><b data-days>{days}</b><span><i data-unit>{"day" if days == 1 else "days"}</i> until<br>Jingle Ball</span></div>'
            f'<div class="c-jb-clock"><span><b data-h>00</b>hrs</span><span><b data-m>00</b>min</span><span><b data-s>00</b>sec</span></div>'
            f'<p class="c-jb-count-city"><strong data-city>{city_html(nxt["city"])}</strong> <span data-line>{lead} \u00b7 {e(nxt["date"])} \u00b7 {e(nxt["venue"])}</span></p>'
            f'<a class="c-jb-count-go" href="#{nxt["a"]}" data-go>See this night \u2192</a></div>')

def jingle_ball_hub():
    """Jingle Ball is nine different nights. Each city gets a ticket-style card with what that night needs."""
    from urllib.parse import quote
    d = jingle_ball_data()
    def card(c):
        acts = ''.join(f'<li><a href="https://music.apple.com/us/search?term={quote(a)}" target="_blank" rel="noopener">{e(a)}<span>Listen ↗</span></a></li>' for a in c['lineup'])
        rules = ''.join(f'<li><b>{e(r["label"])}</b><span>{e(r["text"]) if r["text"] else "Not published by the venue"}</span></li>' for r in c['rules'])
        partner = (f'<div class="c-jb-partner"><span>Before the show \u00b7 Concerto Partner</span><a href="{e(c["partner"].get("url",""))}" target="_blank" rel="noopener">{e(c["partner"]["name"])}</a>'
                   + (f'<p>{e(c["partner"].get("offer",""))}</p>' if c["partner"].get("offer") else '') + '</div>') if c.get('partner') else ''
        sets = (e(c['setTimes']) + '. ') if c.get('setTimes') else ''
        return (f'<article class="c-jb-card" role="tabpanel" aria-labelledby="tab-{c["anchor"]}" id="{c["anchor"]}">'
                f'<div class="c-jb-stub"><p class="c-jb-when">{e(c["date"])}<br>{e(c["time"])}</p><h3>{city_html(c["city"])}</h3><p class="c-jb-show">{e(c["show"])}</p></div>'
                f'<div class="c-jb-body"><p class="c-jb-label">Lineup</p><ul class="c-jb-acts">{acts}</ul>'
                f'<p class="c-jb-sets">{sets}Lineup order is not performance order.</p>'
                f'<div class="c-jb-info-grid"><div><p class="c-jb-label">Setlists &amp; stage times</p><h4>A different set for every night.</h4><p>Jingle Ball performances can differ from an artist’s own tour. Set times are usually shared by the station close to show day. The listed time is showtime.</p></div><div><p class="c-jb-label">Plan your night</p><h4>Make room for the whole evening.</h4><p>Save your show in Concerto, then plan dinner, travel and your stay with Concerto+.</p>{app_link("tour", "jingle-ball-2026-tour", "Open your concert companion", "c-link")}</div></div>' 
                f'<p class="c-jb-label">At {e(c["venueName"])}</p><ul class="c-jb-rules">{rules}</ul>'
                f'{partner}'
                f'<div class="c-jb-actions"><a class="c-jb-tix" href="{e(c["tickets"])}" target="_blank" rel="noopener nofollow">Get tickets</a>'
                + (f'<a class="c-jb-ride" href="{e(c["uber"])}" target="_blank" rel="noopener nofollow">Uber</a><a class="c-jb-ride" href="{e(c["lyft"])}" target="_blank" rel="noopener nofollow">Lyft</a>' if c.get('uber') else '') +
                f'<a class="c-jb-ride" href="{e(c["directions"])}" target="_blank" rel="noopener">Directions ↗</a><a class="c-jb-venue" href="/venue/{c["venue"]}">Full venue guide \u2192</a></div>'
                f'<p class="c-jb-gives">Benefits {e(c["benefits"])}</p></div></article>')
    tabs = ''.join(f'<button type="button" class="c-jb-chip" id="tab-{c["anchor"]}" role="tab" data-city="{c["anchor"]}" aria-controls="{c["anchor"]}">{e(c["city"])}</button>' for c in d['cities'])
    return ('<section class="c-section c-jb c-jb-glass" data-reveal><div class="c-snow" aria-hidden="true"><i></i><i></i></div><div class="c-wrap c-narrow">'
            + eyebrow('\u2726 Nine cities, nine nights') + '<h2 class="c-h2 c-h2-sm">Every Jingle Ball,<br>in one place.</h2>'
            + '<p class="c-body">Pick your city for the lineup, the arena\u2019s rules for the night, your tickets and your ride.</p>'
            + f'<div class="c-jb-chips" role="tablist" aria-label="Choose a city">{tabs}</div>'
            + '<div class="c-jb-grid">' + ''.join(card(c) for c in d['cities']) + '</div>'
            + f'<p class="c-source">Lineups from {e(d["source"])}, {e(d["sourceDate"])}. Venue rules checked against each arena\u2019s own guest guide on September 30, 2026. {e(d["onSale"])}</p>'
            + f'<div class="c-jb-info-grid c-jb-extras"><div><p class="c-jb-label">Tickets</p><h3>Know your on-sale.</h3><p>{e(d["onSale"])}</p><a class="c-link" href="https://www.iheart.com/jingle-ball/" target="_blank" rel="noopener">Official event updates ↗</a></div><div><p class="c-jb-label">Watch from home</p><h3>The holiday special.</h3><p>{e(d["broadcast"])}</p><p>Broadcast date and time have not been announced here.</p></div></div><details class="c-jb-faq"><summary>Does every city have the same lineup?</summary><p>No. Choose your city above before buying tickets or planning your night.</p></details><details class="c-jb-faq"><summary>Are doors and artist set times the same as showtime?</summary><p>No. Showtime is the event start. Check the event listing for doors, and do not assume the lineup is listed in performance order.</p></details></div></section>' )


def jingle_ball_page(t):
    return ('<main id="main-content" class="c-page c-jb-page"><section class="c-jb-hero"><div class="c-wrap"><nav class="c-crumbs" aria-label="Breadcrumb"><a href="/tours">Tours</a><span>/</span>Jingle Ball 2026</nav><div class="c-jb-hero-grid"><div>' + eyebrow('December 1–17, 2026 · iHeartRadio Jingle Ball') + '<h1>Nine nights.<br>One holiday<br><em>soundtrack.</em></h1><p class="c-lead">Your Jingle Ball 2026 companion. Find your city, meet the lineup and plan everything around the show.</p><div class="c-actions"><a class="c-btn c-btn-navy" href="#jingle-cities">Find your night</a>' + app_link('tour',t['tourId'],'Save in Concerto','c-btn c-btn-line') + '</div></div><figure>' + jb_countdown() + '</figure></div><div class="c-jb-statbar"><span><b>9</b> cities</span><span><b>Dec 1–17</b> holiday concert season</span><span><b>Your city.</b> Your lineup.</span></div></div></section><div id="jingle-cities">' + jingle_ball_hub() + '</div>' + close('Make a night of Jingle Ball.','website-tour') + '</main>')

def jb_lineups():
    """Jingle Ball has no setlist; its lineups sit where the setlist would, in the same style."""
    d = jingle_ball_data()
    parts = []
    for c in d['cities']:
        acts = ''.join(f'<li>{e(a)}</li>' for a in c['lineup'])
        parts.append(f'<div class="c-lineup" id="{c["anchor"]}"><h3 class="c-lineup-city">{city_html(c["city"])}</h3>'
                     f'<p class="c-source">{e(c["date"])} \u00b7 {e(c["time"])} \u00b7 <a class="c-link" href="/venue/{c["venue"]}">{e(c["venueName"])} guide</a></p>'
                     f'<div class="c-songs"><ol class="song-list">{acts}</ol></div></div>')
    return (f'<section class="c-section c-white"><div class="c-wrap c-narrow">{eyebrow("Lineups")}'
            f'<h2 class="c-h2 c-h2-sm">Nine cities,<br>nine lineups.</h2>'
            f'<p class="c-source">From {e(d["source"])}, {e(d["sourceDate"])}. Lineup order is not performance order.</p>'
            + ''.join(parts) + '</div></section>')

HOLIDAY_TOURS = {}  # seasonal headers: none active

def listen_link(t, s, cls='c-btn c-btn-line'):
    """Listen before the show: the official Apple Music set list playlist when the setlist names
    one, otherwise an Apple Music search for it."""
    from urllib.parse import quote
    m = re.search(r'https://music\.apple\.com/\S+', (s or {}).get('note') or '')
    if m: return f'<a class="{cls}" href="{e(m.group(0).rstrip(".,)"))}" target="_blank" rel="noopener">Listen on Apple Music</a>'
    if (s or {}).get('songs'):
        q = quote(f"{t['artist']} {t['tourName']} set list")
        return f'<a class="{cls}" href="https://music.apple.com/us/search?term={q}" target="_blank" rel="noopener">Find it on Apple Music</a>'
    return ''

def related_tours(t, n=6):
    """Six other tours with setlists, different on every page: same artist first letter neighbours
    would cluster, so pick a stable spread from the full list."""
    import hashlib
    pool = [x for x in TOURS if x['tourId'] in LIVE and x['tourId'] != t['tourId']]
    if len(pool) <= n: return pool
    start = int(hashlib.md5(t['tourId'].encode()).hexdigest(), 16) % len(pool)
    step = max(1, len(pool) // n)
    return [pool[(start + i * step) % len(pool)] for i in range(n)]

def show_info(tour_id):
    """Tours that aren't concerts (data/shows.json): no setlist, the cast sits where it would be."""
    try: return json.loads((ROOT / 'data' / 'shows.json').read_text()).get(tour_id)
    except Exception: return None

def tour_dates_shell(t):
    sh = show_info(t['tourId'])
    # A show is listed on Ticketmaster under its own name and outside the Music category,
    # so its dates are searched by that name, in every category, matching the start of the billing.
    extra = (f' data-tour-keyword="{e(sh.get("searchTerm") or t["artist"])}" data-tour-match="prefix"' + (' data-tour-any' if sh.get('anyCategory') else '')) if sh else ''
    return (f'<section class="cx-sec c-upcoming" id="dates" data-tour-dates data-tour-artist="{e(t["artist"])}" data-tour="{e(t["tourId"])}"{extra} hidden aria-labelledby="dates-h">'
            f'<div class="cx-wrap"><div class="cx-sec-head"><h2 class="cx-h2" id="dates-h">Tour Dates <span class="c-up-count" data-count></span></h2></div>'
            '<ol class="c-up-list"></ol><p class="cx-note">Each venue guide has its bag rules, doors, parking, and rideshare pickup. Dates from Ticketmaster.</p></div></section>')

def cx_panel(anchor, ic, title, meta, body, check=True):
    """An always-open white card, like the app's Setlist card."""
    return (f'<article class="cx-panel" id="{anchor}"><header><span class="cx-ic">{icon(ic)}</span><span class="cx-tt"><h2 class="cx-card-t">{e(title)}</h2>'
            f'{cx_ver(meta, check) if meta else ""}</span></header><div class="cx-card-b">{body}</div></article>')

def cx_songs(songs, start=1):
    return '<ol class="cx-songs">' + ''.join(f'<li><span class="cx-n">{i}</span><span>{e(x)}</span></li>' for i, x in enumerate(songs, start)) + '</ol>'

def tour_page(t):
    """Same look as the app's tour screen: the artist photo card, the dates, then the setlist
    (or the cast for a show), each as a white card."""
    s = SETS.get(t['tourId']); songs = (s or {}).get('songs') or []
    sh = show_info(t['tourId'])
    site = cx_btn(t['tourWebsite'], 'Tour site', 'globe', attrs=' target="_blank" rel="noopener"') if t.get('tourWebsite') else ''
    panels, chips = [], [('dates', 'Tour dates')]
    if songs:
        first, last = songs[0], songs[-1]
        lead = f'<p class="cx-lead"><b>Setlist:</b> {songs_word(len(songs))}, opening with “{e(first)}” and closing with “{e(last)}”.</p>'
        more = f'<a href="/setlist/{t["tourId"]}">All {songs_word(len(songs))}</a>' if len(songs) > 12 else f'<a href="/setlist/{t["tourId"]}">Setlist page</a>'
        listen = listen_link(t, s, '')
        panels.append(cx_panel('setlist', 'music', 'Setlist', f'Updated {pretty_date(s.get("updated"))}' if s.get('updated') else '',
            cx_songs(songs[:12]) + f'<p class="cx-fine">{e(re.sub(r", updated .*$", "", source_label(s)))}. Setlists change by night.</p>'
            f'<div class="cx-links">{more}{listen}</div>'))
        chips.append(('setlist', 'Setlist'))
    elif sh:
        lead = f'<p class="cx-lead">{e(sh["body"])}</p>'
        panels.append(cx_panel('the-show', 'info', sh.get('eyebrow') or 'The show', f'Updated {pretty_date(sh.get("updated"))}' if sh.get('updated') else '',
            f'<p>{e(sh["body"])}</p><p>{e(sh["heading"])} Dates are above as they’re announced, with a guide to every arena.</p>'))
        if sh.get('cast'):
            panels.append(cx_panel('cast', 'users', sh.get('castTitle') or 'Cast', '', '<ul class="cx-cast">' + ''.join(f'<li>{e(x)}</li>' for x in sh['cast']) + '</ul>'
                + (f'<p class="cx-fine">{e(sh["castNote"])}</p>' if sh.get('castNote') else '')))
        if sh.get('troupe'):
            panels.append(cx_panel('troupe', 'users', sh.get('troupeTitle') or 'Troupe', '', '<ul class="cx-cast">' + ''.join(f'<li>{e(x)}</li>' for x in sh['troupe']) + '</ul>'))
        chips.append(('the-show', 'The show'))
    elif t['tourId'] == 'jingle-ball-2026-tour':
        d = jingle_ball_data()
        lead = f'<p class="cx-lead">Every city has its own lineup. Dates, lineups, and a guide to every venue, from {e(d["source"])}.</p>'
        for i, c in enumerate(d['cities']):
            panels.append(cx_card(c['anchor'], 'music', c['city'], f'{c["date"]} · {c["time"]}',
                f'<p>Lineup order is not performance order. <a href="/venue/{c["venue"]}">{e(c["venueName"])} guide</a></p>' + cx_songs(c['lineup']),
                open_=i == 0, check=False))
        chips.append((d['cities'][0]['anchor'] if d['cities'] else 'dates', 'Lineups'))
    elif s and (s.get('note') or '').startswith('Lineups vary'):
        lead = '<p class="cx-lead">Every night brings a different lineup. Tour dates and a guide to every venue on the tour.</p>'
        panels.append(cx_panel('lineups', 'music', 'Lineups', '', '<p>Each night brings a different mix of artists. Open a date in Concerto to see who is playing, then plan the night around the venue.</p>'))
    else:
        lead = '<p class="cx-lead">Tour dates and a guide to every venue on the tour. The setlist appears here once it’s confirmed.</p>'
        if s:
            panels.append(cx_panel('setlist', 'music', 'Setlist', 'Coming soon', '<p><b>Setlist Coming Soon!</b> Concerto is following this tour. Songs appear here when there is a usable current setlist, never a guessed one.</p>', check=False))
            chips.append(('setlist', 'Setlist'))
    panels.append(cx_panel('about', 'info', 'About the tour', '', f'<p>{e(t["artist"])}: {e(t["tourName"])}. Open the tour in Concerto to save a date and get the venue’s rules, directions, and a show-day reminder with it.</p>'
        + (f'<div class="cx-links"><a href="{e(t["tourWebsite"])}" target="_blank" rel="noopener">Official tour site</a></div>' if t.get('tourWebsite') else '')))
    chips.append(('about', 'About'))
    more = related_tours(t)
    import datetime as _dt
    _until = HOLIDAY_TOURS.get(t['tourId'])
    _on = bool(_until) and _dt.date.today().isoformat() <= _until
    kicker = '✦ Holiday concert season' if _on else 'Tour guide'
    more_html = ''.join(f'<a class="cx-tile" href="/tour/{x["tourId"]}"><span class="cx-tile-ic">{icon("mic", 18)}</span><span><b>{e(x["artist"])}</b><small>{e(x["tourName"])}</small></span></a>' for x in more)
    if more: chips.append(('more', 'Also on the road'))
    close_fine = ('Save your date in Concerto. The cast, the venue guide, and a show-day reminder stay with your show. Free on iPhone.' if sh
                  else 'Save your date in Concerto. The setlist, the venue’s rules, and a show-day reminder stay with your show. Free on iPhone.')
    return ('<main id="main-content" class="c-page cx">'
            # Same header as every other page: label, artist, tour, with a small photo on the right. No jump links.
            + f'<section class="c-hero c-hero-cream c-hero-page"><div class="c-wrap c-hero-inner"><nav class="c-crumbs" aria-label="Breadcrumb"><a href="/tours">Tours</a><span>/</span>{e(t["artist"])}</nav>'
            f'{eyebrow(kicker)}<h1>{e(t["artist"])}</h1><p class="c-lead">{e(t["tourName"])}</p><div class="c-venue-photo c-artist-photo cx-hphoto" data-artist="{e(t["artist"])}"></div></div></section>'
            + tour_dates_shell(t)
            + f'<section class="cx-sec"><div class="cx-wrap cx-stack">{"".join(panels)}</div></section>'
            + (f'<section class="cx-sec" id="more"><div class="cx-wrap"><div class="cx-sec-head"><h2 class="cx-h2">Also on the road</h2></div><div class="cx-tiles">{more_html}</div></div></section>' if more else '')
            + close('Going to this tour?', 'website-tour', close_fine) + '</main>')

def setlist_page(slug, s):
    t = next((x for x in TOURS if x['tourId'] == slug), None)
    songs = s['songs']
    return ('<main id="main-content" class="c-page">' +
            f'<section class="c-hero c-hero-cream c-hero-page"><div class="c-wrap c-hero-inner"><nav class="c-crumbs" aria-label="Breadcrumb"><a href="/setlists">Setlists</a><span>/</span>{e(s.get("artist"))}</nav>{eyebrow("Setlist · " + (s.get("tour") or ""))}<h1>{e(s.get("artist"))}</h1>'
            f'<p class="c-lead">{songs_word(len(songs))}. {e(source_label(s))}. Setlists change by night.</p><div class="c-actions">{app_link("tour", slug, "Save your show in Concerto", "c-btn c-btn-navy")}'
            + (listen_link(t, s) if t else '') + (f'<a class="c-btn c-btn-line" href="/tour/{slug}#dates-h">Tour dates and venues</a>' if t else '') + '</div></div></section>'
            f'<section class="c-section c-white"><div class="c-wrap"><div class="c-songs c-songs-full"><ol class="song-list">' + ''.join(f'<li>{e(x)}</li>' for x in songs) + '</ol></div></div></section>'
            + close('Know every word.', 'website-setlist', 'Save your show in Concerto. The setlist, the venue’s bag rules, and a show-day reminder stay with your show. Free on iPhone.') + '</main>')

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

def ask_bar(home=False):
    """Concerto AI: one bar for search and questions. On the homepage it opens the search page,
    which asks right away; on the search page it searches as you type and asks on Enter."""
    hint = 'Try <span class="no-widow">“Where do I park for MSG?”</span> or <span class="no-widow">“Noah Kahan setlist”</span>'
    if home:
        return ('<form class="c-ask" action="/search" method="get" role="search" aria-label="Ask Concerto">'
                '<div class="c-ask-ring"><div class="c-ask-field"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.75" cy="10.75" r="6.75"/><path d="m16 16 4.5 4.5" stroke-linecap="round"/></svg>'
                '<input name="q" type="search" autocomplete="off" placeholder="Ask anything about your show" aria-label="Ask Concerto a question" required>'
                '<input type="hidden" name="ask" value="1"><button type="submit">Ask</button></div></div>'
                f'<p class="c-ask-hint">{hint}</p></form>')
    return ('<form class="c-ask" data-ask-form role="search" aria-label="Ask Concerto">'
            '<div class="c-ask-ring"><div class="c-ask-field"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.75" cy="10.75" r="6.75"/><path d="m16 16 4.5 4.5" stroke-linecap="round"/></svg>'
            '<input data-site-search type="search" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Ask anything, or search a venue or artist" aria-label="Ask Concerto or search">'
            '<button type="submit">Ask</button></div></div>'
            f'<p class="c-ask-hint">{hint}</p></form>')

def home():
    h = hero('The concert-night companion', 'From the Concert<br>to the City',
             'Save a show and Concerto does the rest. Find everything about your venue, the city around it, and so much more.',
             ask_bar(home=True) + store_button('website-home') + '<a class="c-link" href="#how">How it works</a>',
             [f'{V_COPY} venue guides', f'{N_T} tours', f'{N_S} setlists', 'Free on iPhone'], 'cream', 'c-hero-home')
    what = section('white', 'What Concerto does', 'Three things, done carefully.', rows([
        ('Know the venue.', e(f'Guides for {V_COPY} venues worldwide, from official sources and dated, so you know what to expect before you get there.'), '<a class="c-link" href="/venues">Browse venue guides</a>'),
        ('Know the tour.', e(f'Dates and setlists for {N_T} tours, so you know the songs before the lights go down.'), '<a class="c-link" href="/tours">Browse tours and setlists</a>'),
        ('Know the city.', 'Restaurants, hotels, and things to do around every venue, so the concert can be a whole night out.', '<a class="c-link" href="/your-night">How Your Night works</a>')]), sid='what')
    # The same five steps as the app's Help screen and the three-card intro, so the site,
    # the App Store, and the app all describe one journey.
    steps = [('Find your show', 'Search an artist, a venue, or a city. Or open Near Me for what’s on around you.'),
             ('Save it', 'Tap the bookmark and sign in with Apple. Add your ticket, how you’re getting there, and what bag you’re bringing. It takes a minute.'),
             ('Use Your Night', 'Everything for that show in four tabs: Before, Arrive, Show, and After.'),
             ('After the show', 'A memory card of your photos from the show, every show added to your Passport, and Concerto Wrapped in December.'),
             ('Add Concerto+', 'Exit Plan, AI Bag Check, and Plan My Night. ' + PLUS_PRICE_LINE)]
    journey = '<ol class="c-journey">' + ''.join(f'<li><b>{e(t)}</b><span>{e(d)}</span></li>' for t, d in steps) + '</ol>'
    how = ('<section class="c-section c-cream" id="how" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('How it works') +
           '<h2 class="c-h2">How Concerto works.</h2><p class="c-body">Five steps. The first two take a minute.</p>'
           '<div class="c-actions"><a class="c-link" href="/your-night">How Your Night works</a><a class="c-link" href="/help">Help Center</a></div></div><div>' + journey + '</div></div></section>')
    keep = ('<section class="c-section c-navy" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('After the show') +
            '<h2 class="c-h2">Photos, Passport,<br>and Wrapped.</h2>'
            '<p class="c-body">After the show, Concerto puts the photos you took at the venue on a card with the artist, the date, and the setlist, sized for Instagram Stories.</p>'
            '<p class="c-body">Every show you go to is added to your Passport. In December, Concerto Wrapped totals your year: shows, artists, venues, and songs heard live.</p></div>'
            '<p class="c-pull">Memory card.<br>Passport.<br>Concerto Wrapped.</p></div></section>')
    plus = ('<section class="c-section c-gold" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Concerto+') +
            '<h2 class="c-h2">More of Your Night.</h2><p class="c-body">Exit Plan. AI Bag Check. Plan My Night.<br>' + e(PLUS_PRICE_LINE) + '</p>'
            '<a class="c-link" href="/premium">Explore Concerto+</a></div><p class="c-pull">Dinner at 5:45.<br>Out the door at 7:10.<br>Lights down at 7:30.</p></div></section>')
    # Phone length matters: the principles live on About, and After the show is step 4 of How it works.
    return '<main id="main-content" class="c-page">' + h + problem_section() + what + how + plus + guide_index() + close() + '</main>'

# ---------------- 2.7: Your Night and Concerto+ ----------------
# One source for the words both pages (and the homepage) use, so the price and the
# feature names can never drift apart between pages. Keep in step with app/plus.tsx.
PLUS_YEAR, PLUS_PASS = '$29.99', '$4.99'
PLUS_PRICE_LINE = f'{PLUS_YEAR} a year, or {PLUS_PASS} for one show.'
V_COPY = '600+'  # venues: say "600+ venues worldwide", not the exact count

def four(cols):
    """The four Your Night tabs, side by side: name, one line, and what lives there.
    A gold + marks the Concerto+ parts, the same way the app marks them."""
    out = ''
    for name, line, items in cols:
        li = ''.join(f'<li{" class=c-plus" if plus else ""}>{e(t)}{"<span class=c-sr> (Concerto+)</span>" if plus else ""}</li>' for t, plus in items)
        out += f'<div class="c-tab"><p class="c-tab-name">{e(name)}</p><h3>{e(line)}</h3><ul>{li}</ul></div>'
    return f'<div class="c-four">{out}</div>'

def your_night():
    h = hero('Your Night', 'Your whole show,<br>on one page.',
             'Save a show and tell Concerto three things: how you’re getting there, what bag you’re bringing, and where you’re sitting. Your Night answers everything else for that show, from the setlist to the ride home.',
             store_button('website-your-night', tone='white') + '<a class="c-link" href="#tabs">See what’s inside</a>',
             ['Free in Concerto', 'Before, Arrive, Show, After', 'Venue, city, and setlist in one place'], 'navy')
    setup = rows([('How are you getting there?', 'Driving, rideshare, transit, or walking. Directions open the right way in Apple Maps, and parking or Uber and Lyft show up when they matter.', ''),
                  ('What bag are you bringing?', 'Clear bag, small bag, backpack, or none. Your Night checks it against the venue’s published rule and tells you plainly if it works.', ''),
                  ('Where are you sitting?', 'Section, row, and seat, or the floor. They sit on a ticket at the top of Arrive, one tap from the ticket itself.', '')])
    tabs = four([
        ('Before', 'Get ready.', [('The setlist the tour has been playing', False), ('Show-night weather', False), ('Restaurants, hotels, and things to do nearby', False), ('Plan My Night: dinner, when to leave, and the show', True)]),
        ('Arrive', 'Get in.', [('Your ticket, one tap away', False), ('Directions, parking, or Uber and Lyft', False), ('Your bag, checked against the rule', False), ('AI Bag Check from a photo of your bag', True)]),
        ('Show', 'Enjoy it.', [('Food, drink, and accessibility inside', False), ('The full setlist', False)]),
        ('After', 'Get home.', [('Uber or Lyft, from the venue’s pickup spot', False), ('Exit Plan: the fastest way out and where to get picked up', True), ('Your memory card', False)])])
    tabs_sec = section('white', 'Four tabs', 'Every part of the night, in the order you need it.',
                       tabs + '<p class="c-note">The page looks and works the same every time you open it. Parts marked <b class="c-plusmark">+</b> are Concerto+.</p>', sid='tabs')
    memory = ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('After the show') +
              '<h2 class="c-h2">Memory card and Passport.</h2>'
              '<p class="c-body">After the show, Concerto finds the photos you took there and puts them on a card with the artist, the date, the venue, and the setlist. Save it or share it.</p>'
              '<p class="c-body">Every show you go to gets a stamp in your Passport, with your shows, venues, artists, and cities for the year, ready to share.</p></div>'
              '<p class="c-pull">Memory card.<br>Passport.<br>Concerto Wrapped.</p></div></section>')
    ask = section('white', 'Concerto AI', 'Ask anything about your show.',
                  '<p class="c-body">Every Your Night page has its own question bar. Concerto AI already knows the venue and the artist, so “Can I bring a portable charger?” gets an answer for your show, from the venue’s own rules.</p>', narrow=True)
    free = ['Your Night for every show you save', 'Restaurants, hotels, and things to do near the venue', 'The setlist, weather, directions, parking, and rideshare',
            'Your bag, checked against the venue’s rule', 'Show-day alerts, and concerts near you each Friday', 'Your memory card and Passport', '3 Concerto AI answers a day']
    paid = ['Exit Plan', 'AI Bag Check', 'Plan My Night', '30 Concerto AI answers a day', 'More alerts: Time to Head Out, Exit Plan, and presales']
    cols = ('<div class="c-compare"><div><h3>Free</h3><ul>' + ''.join(f'<li>{e(x)}</li>' for x in free) + '</ul></div><div class="c-compare-plus"><h3>Concerto+</h3><ul>'
            + ''.join(f'<li>{e(x)}</li>' for x in paid) + f'</ul><p class="c-body">{e(PLUS_PRICE_LINE)}</p><a class="c-link" href="/premium">About Concerto+</a></div></div>')
    return ('<main id="main-content" class="c-page">' + h + section('cream', 'Set it up once', 'Three questions, answered once.', setup) + tabs_sec + memory + ask
            + section('cream', 'What it costs', 'Your Night is free.', cols) + close('Save your next show.', 'website-your-night') + '</main>')

def premium():
    h = hero('Concerto+', 'More of Your Night.',
             'Concerto+ adds the parts of the night that take the most planning: the way out, your bag, and the evening around the show. It lives inside Your Night, marked with a gold +, right where you need it.',
             store_button('website-premium') + '<a class="c-link" href="#pricing">See pricing</a>',
             [f'{PLUS_YEAR} a year', f'{PLUS_PASS} Show Pass for one show', 'Billed through the App Store'], 'gold')
    feats = rows([('Exit Plan', 'The fastest way out of the venue and the best place to get picked up, so the night doesn’t end in a crowd at the curb.', ''),
                  ('AI Bag Check', 'Take a photo of your bag and Concerto checks it against the venue’s published policy. It shows the rule it used, and the venue still makes the final call.', ''),
                  ('Plan My Night', 'Dinner nearby, when to leave, and the show, planned around showtime and how you’re getting there.', ''),
                  ('More Concerto AI', '30 answers a day instead of 3, for every question about your show.', ''),
                  ('More alerts', 'Time to Head Out, two hours before the show, and your Exit Plan near the end of the night, plus new dates and presales for the artists you follow. The show-day alert, the memory card reminder, and This Weekend stay free.', '')])
    where = ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Where it lives') +
             '<h2 class="c-h2">Inside Your Night,<br>not another screen.</h2></div><div>'
             '<p class="c-body">Each Concerto+ feature sits in the tab where you need it. Exit Plan is in After. AI Bag Check is in Arrive. Plan My Night is in Before.</p>'
             '<p class="c-body">Before you join, each one shows as a gold row that tells you what it does. Once you’re a member, the same row shows your answer.</p></div></div></section>')
    pricing = ('<section class="c-section c-white" id="pricing" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Pricing') +
               '<h2 class="c-h2">Two ways in.</h2><p class="c-body">Billed through the App Store. The yearly plan renews each year until you cancel in your Apple Account settings. The Show Pass is a one&#8209;time purchase.</p></div>'
               f'<div class="c-prices"><div><b>{PLUS_YEAR}</b><span>a year, for every show you save</span></div><div><b>{PLUS_PASS}</b><span>Show Pass: everything in Concerto+ for one show, through the morning after</span></div></div></div></section>')
    free = section('cream', 'Always free', '', '<p class="c-statement">Venue guides, places nearby, directions, the setlist, your memory card, and your Passport.<br>Never behind Concerto+.</p>', narrow=True)
    return ('<main id="main-content" class="c-page">' + h + section('white', 'What is included', 'Five things that make the night easier.', feats) + where + pricing + free
            + close('Start with Your Night.', 'website-premium', 'Free on iPhone. Concerto+ is in the app.') + '</main>')

def about():
    h = hero('About Concerto', 'The concert-night<br>companion.', 'Concerto makes concert nights easier, with what you need to know about the venue, the tour, and the city around it.',
             '', ['Founded 2025', 'Concerto LLC', 'Concerto for iPhone'], 'navy')
    founder = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Our story') + '<h2 class="c-h2">It started with<br>one night in Toronto.</h2></div>'
               '<div><p class="c-body">Our founder, Jayce Wells, had tickets to the Eras Tour in Toronto. Planning the night meant bouncing between Google, Apple Maps and OpenTable just to figure out what was around the stadium.</p>'
               '<p class="c-body">So he designed one app for the exact show you are going to. It started with every NFL, NBA and MLB stadium, entered by hand, and now covers more than 600 venues worldwide.</p>'
               '<p class="c-body">Today you save a show and Concerto builds Your Night around it, with what you need to know about the venue and the tour, and what’s around you in the city. You can ask Concerto AI anything about your show. Afterward you get a memory card of your photos, a Passport of every show, and Concerto Wrapped at the end of the year.</p>'
               '<div class="c-actions"><a class="c-link" href="/your-night">See Your Night</a><a class="c-link" href="/founder">Read Jayce&#8217;s letter</a></div></div></div></section>')
    asks = ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('What fans ask') + '<h2 class="c-h2">The same questions,<br>before every show.</h2></div>'
            '<div><p class="c-body"><b>What bag can I bring? Where do I park? When do doors open? What will they play? Where should we eat?</b></p>'
            '<p class="c-body">Fans ask these before every concert, and the answers are usually spread across a venue’s website, a map, a setlist site and a few tabs of restaurants. Concerto answers all of them for the exact venue and tour, on one page, and Concerto AI answers them in a sentence.</p>'
            '<p class="c-body">Fans are already searching for these answers, and Google is sending them to Concerto. Once a fan knows what they can bring, the next thing they decide is where to eat and where to stay, so the same page answers that too.</p>'
            '<div class="c-actions"><a class="c-link" href="/search">Ask Concerto a question</a></div></div></div></section>')
    facts = [('Founded', 'March 2025'), ('Company', 'Concerto LLC'), ('Product', 'Concerto for iPhone'), ('Coverage', f'{V_COPY} venues worldwide')]
    fx = '<section class="c-numbers" data-reveal><div class="c-wrap c-facts">' + ''.join(f'<div><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in facts) + '</div></section>'
    links = '<section class="c-section c-cream" data-reveal><div class="c-wrap c-links-row"><a class="c-link" href="/press">Press</a><a class="c-link" href="/investors">Investors</a><a class="c-link" href="/partners">Partners</a><a class="c-link" href="/contact">Contact</a></div></section>'
    return '<main id="main-content" class="c-page">' + h + name_section() + founder + asks + proof_strip() + principles() + fx + links + close() + '</main>'

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

# ----- from the founder -----
# Modeled on the founder letter as its own page (Patagonia: signed, dated, first person) with the
# origin told in the company's voice on About (Warby Parker). The three Canva drafts are the one
# exception to "no app imagery": dated historical artifacts, labeled, on this page only.
def founder():
    h = hero('From the founder', 'It started with<br>one night in Toronto.', 'Why Concerto exists, and what it took to build it.',
             '', ['Jayce Wells', 'September 2026'], 'navy')
    P = lambda t: f'<p class="c-letter-p">{t}</p>'
    drafts = ('<figure class="c-drafts">'
              '<div class="c-drafts-row">'
              '<img src="/img/founder/first-design-your-event.jpg" width="560" height="724" loading="lazy" alt="First Concerto design: a Your Event screen for a show at AT&amp;T Stadium, with restaurants, hotels, shops and transportation">'
              '<img src="/img/founder/first-design-transportation.jpg" width="560" height="724" loading="lazy" alt="First Concerto design: transportation, with a rideshare pickup map around the venue">'
              '<img src="/img/founder/first-design-restaurants.jpg" width="560" height="724" loading="lazy" alt="First Concerto design: restaurants near the venue">'
              '</div><figcaption>The first designs, made in Canva in October 2024.</figcaption></figure>')
    letter = (
      '<section class="c-section c-white" data-reveal><div class="c-wrap c-letter">'
      + P("In November 2024, I had tickets to night six of the Eras Tour in Toronto. I&#8217;d lived in Toronto, but I didn&#8217;t know the area around the Rogers Centre, and I spent the weeks before the show bouncing between Google, Apple Maps and OpenTable, trying to figure out where to eat, where to stay and what to do around one specific night.")
      + P("I kept thinking: there should be one app for this. Not for the city in general, but for the exact show you&#8217;re going to. So on October 25, 2024, I opened Canva and started designing it. The name Concerto and the line <em>From the Concert to the City</em> came right after.")
      + drafts
      + P("I started with 112 venues, every NFL, NBA and MLB stadium in the country. I entered each venue&#8217;s policies and official links into a spreadsheet by hand, then went venue by venue finding the restaurants and hotels nearby. In March 2025 Concerto became a company, and in April the first version launched on the App Store and Google Play.")
      + P("By that summer the guide had grown to 346 venues. I&#8217;d love to say it got easier. It didn&#8217;t. I spent hours, days and weeks researching venues, entering data, sketching new features, redesigning screens and making social content, even while paying for a developer and a PR agency. When neither was moving the needle, I made the hardest call so far: I cut both, took Concerto back, and rebuilt it from the ground up myself.")
      + P(f"Today Concerto covers more than 600 venues worldwide, from college arenas to stadiums and clubs across North America, the U.K. and Europe. Every guide is researched from the venue&#8217;s own official sources and dated, because the night deserves accuracy. It&#8217;s still built by one person.")
      + P('Where this goes next is bigger than one app. I want Concerto to know your night from the moment you buy the ticket to the moment you get home, and to share it with the people you&#8217;re going with. That means working with the people who make those nights happen: venues that want their guests to arrive knowing the rules, the restaurants and hotels around them, and <a href="/creators">creators</a> who live for live music. If that&#8217;s you, <a href="/contact">I&#8217;d love to talk</a>, and if you&#8217;d like to help build what comes next, <a href="/investors">start here</a>.')
      + P("If you&#8217;ve ever stood outside a venue wondering what you&#8217;re allowed to bring in, or how you&#8217;re getting home, Concerto is for you. Thank you for being here.")
      + '<p class="c-letter-sign">Jayce</p><p class="c-letter-role">Jayce Wells, Founder, Concerto</p>'
      + '<div class="c-actions"><a class="c-btn c-btn-navy" href="/contact">Write to Jayce</a><a class="c-link" href="/press">Press</a></div>'
      + '</div></section>')
    return '<main id="main-content" class="c-page">' + h + letter + close() + '</main>'


# ----- company -----
def press_coverage():
    """'In the news' on the press page, from data/press.json. Hidden until there is an article."""
    import datetime as _dt
    try: items = json.loads((ROOT / 'data' / 'press.json').read_text())
    except Exception: items = []
    if not items: return ''
    rows_html = ''
    for i in sorted(items, key=lambda x: x['date'], reverse=True):
        d = _dt.date.fromisoformat(i['date']).strftime('%B %-d, %Y')
        rows_html += (f'<li class="c-press-item"><p class="c-eyebrow">{e(i["outlet"])}</p>'
                      f'<a class="c-press-title" href="{e(i["url"])}" target="_blank" rel="noopener">{e(i["title"])}</a>'
                      f'<p class="c-press-date">{d}</p></li>')
    return section('white', 'In the news', 'Concerto in the press.', f'<ul class="c-press-list">{rows_html}</ul>')

def press():
    h = hero('Press and media', 'Concerto, in brief.', 'Concerto makes concert nights easier, with what fans need to know about the venue, the tour, and the city around it.', '<a class="c-btn c-btn-navy" href="/contact?topic=media">Media inquiry</a>', ['Founded 2025', 'Concerto for iPhone and the web'], 'cream')
    facts = [('Company', 'Concerto LLC'), ('Founder', 'Jayce Wells'), ('Founded', 'March 2025'), ('Product', 'Concerto for iPhone, and concertocity.com'), ('Coverage', f'{V_COPY} venues worldwide, {N_T} tours'), ('Pricing', f'Free. Concerto+ is {PLUS_YEAR} a year, or {PLUS_PASS} for one show'), ('Partners', 'Restaurants $99 a month, hotels $299 a month'), ('Search reach', f'About {PROOF_DAY} Google search appearances a day ({PROOF_AS_OF})'), ('Independence', 'Independent from artists, venues, teams, and promoters')]
    fact_list = '<dl class="c-facts-list">' + ''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in facts) + '</dl>'
    boiler = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Company background') + '<h2 class="c-h2">What Concerto does.</h2></div><div>'
              '<p class="c-body">A concert companion for fans who already have a ticket, on iPhone and the web, founded by Jayce Wells in 2025. Fans save a show and Concerto builds Your Night: the venue’s policies, the tour and setlist, and restaurants and hotels nearby. Concerto AI answers fans’ questions about their show from Concerto’s own venue guides. After the show, fans get a memory card of their photos, a Passport of every show, and Concerto Wrapped each December.</p>'
              '<p class="c-body">Concerto is free. Concerto+ adds Exit Plan, AI Bag Check, and Plan My Night. Through Concerto Partners, restaurants and hotels near a venue can appear first in its Nearby rows, always labeled Concerto Partner.</p>'
              f'<p class="c-body">Fans are searching for these answers: Concerto shows up in Google about {PROOF_DAY} times a day, eight times as often as in July.</p>'
              '<p class="c-body">Independent from artists, venues, teams, and promoters. A listed guide is not a partnership.</p></div></div></section>')
    kit = section('cream', 'Fact sheet', 'The essentials.', fact_list)
    bio = section('white', 'Founder bio', 'Jayce Wells.', '<p class="c-body">Jayce Wells is the 23-year-old founder of Concerto, a concert-night app covering 600+ venues worldwide. The idea came while planning a night at the Eras Tour in Toronto in 2024, juggling three apps to figure out the area around the stadium. He started with every NFL, NBA and MLB stadium, entering each venue&#8217;s policies by hand, launched in 2025, and after parting ways with his PR agency and app platform, rebuilt Concerto himself in 2026.</p><div class="c-actions"><a class="c-link" href="/founder">Read the letter from Jayce</a></div>')
    res = section('white', 'Media resources', 'Logos, interviews, and figures.', '<p class="c-body">Logo files, product images, interviews, confirmed figures. Ask and we will send them.</p><div class="c-actions"><a class="c-link" href="/contact?topic=media">Contact for media</a><a class="c-link" href="/about">Read the founder story</a></div>')
    return '<main id="main-content" class="c-page">' + h + press_coverage() + boiler + kit + bio + res + close() + '</main>'


def where_help():
    # Named plainly: what a partner would actually do, not what the company lacks. No amounts,
    # no terms, no "we are raising" — a public page stays about experience and introductions.
    items = [('Getting in front of fans.', 'Concerto is found by people who already have a ticket. Growth experience in consumer apps is what we would use fastest.', ''),
             ('The rooms.', 'Introductions to venues, promoters, and the teams who run buildings. That is how a guide becomes a partnership.', ''),
             ('The brands around the night.', 'Restaurants, hotels, and rideshare are already part of a concert night. We want the people who know how those deals get done.', ''),
             ('Operating in live music.', 'Anyone who has run a tour, a venue, or a ticketing product sees problems a fan-side app cannot.', '')]
    return section('white', 'Where help goes furthest', 'Four things, named plainly.', rows(items) +
                   '<p class="c-body">Concerto is founder-led, and the product is built. These are the areas where another set of hands or one good introduction moves the most.</p>'
                   '<div class="c-actions"><a class="c-link" href="/contact?topic=investor">Start a conversation</a></div>')

def investors():
    h = hero('Investors', 'The product is built.<br>Next is growth.', 'Concerto makes concert nights easier, with what fans need to know about the venue, the tour, and the city around it. We welcome people who know live music, hospitality, and consumer products.',
             '<a class="c-btn c-btn-navy" href="/contact?topic=investor">Contact the founder</a>', ['Founder-led', 'Since 2025'], 'navy')
    today = ('<section class="c-section c-white" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('The company today') + '<h2 class="c-h2">Built around one fan experience.</h2></div><div>'
             '<p class="c-body">Venue guidance, tour information, nearby discovery, and planning, around one saved show, with Concerto AI to answer fans’ questions about it. The app and website are built.</p>'
             '<p class="c-body">Concerto makes money two ways. Concerto+ is ' + PLUS_PRICE_LINE[:-1] + ', and adds Exit Plan, AI Bag Check, and Plan My Night. Concerto Partners lets restaurants and hotels near a venue come first in its Nearby rows, at $99 and $299 a month.</p><div class="c-actions"><a class="c-link" href="/founder">From the founder</a><a class="c-link" href="/partners">Concerto Partners</a></div></div></div></section>')
    demand = ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('The demand') + '<h2 class="c-h2">Fans are already<br>asking these questions.</h2></div><div>'
              '<p class="c-body">Before a show, fans search for the bag policy, parking, door times and the setlist. Google is sending those searches to Concerto’s venue and tour guides, and Concerto is still new, so it is climbing in the results every month.</p>'
              '<p class="c-body">The fan reading a venue’s bag policy is planning their night, and the next thing they decide is where to eat and stay. That is where Concerto Partners appear.</p></div></div></section>')
    conv = section('cream', 'The conversation', 'Relevant experience and introductions.', '<p class="c-body">Connections across venues, hospitality, artists, and consumer products are welcome. Financials, priorities, and terms are discussed directly.</p><div class="c-actions"><a class="c-link" href="/contact?topic=investor">Start a conversation</a></div>')
    return '<main id="main-content" class="c-page">' + h + today + demand + proof_strip() + where_help() + conv + close() + '</main>'

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
    """Concerto Partners: a restaurant or hotel leads the Nearby row for its venue in the app,
    leads the same row on the venue page online, and is suggested first by Concerto AI and Plan My Night.
    An optional Perk adds a gold star; tapping it shows the offer. Venues by conversation."""
    h = hero('Concerto Partners', 'Reach concert fans<br>near your venue.',
             'When fans save a show, Concerto shows them restaurants, hotels, and things to do near the venue. Partners come first.',
             '<a class="c-btn c-btn-navy" href="/partners/restaurants#join">For restaurants</a><a class="c-btn c-btn-line" href="/partners/hotels#join">For hotels</a>',
             ['Restaurants $99 a month', 'Hotels $299 a month', 'Live in minutes'], 'gold')
    why = partners_why('restaurants and hotels')
    what = section('white', 'What you get', 'First in the row<br>for your venue.', rows([
        ('First in Nearby Restaurants or Nearby Hotels.', 'Your place leads the row for your venue in the Concerto app, on the venue’s page and in Your Night for every show there. With more than one partner at a venue, the order rotates daily.', ''),
        ('First on the website and in answers.', 'Your place also leads its Nearby row on your venue’s page on concertocity.com, with its photo, and Concerto AI and Plan My Night suggest it first when fans ask where to eat or stay.', ''),
        ('The same card as every place around you.', 'Your photo from your Google listing, your price, and your distance from the venue. Tapping it opens directions.', ''),
        ('An optional Perk.', 'Add an offer, like a free dessert on show nights. A gold star appears on your card, and signed-in fans tap it to see the offer.', '')]))
    how = section('cream', 'How it works', 'Three steps.', rows([
        ('Pick your venue.', 'Search for your restaurant or hotel near any of Concerto’s 600+ venues worldwide. Your address, location, and photo fill in from Google.', ''),
        ('Add an offer if you want one.', 'Optional. Add an offer and your reservation or booking link. Fans who tap your star see the offer and can go straight to your link.', ''),
        ('Pay, and you’re live.', 'Restaurants are $99 a month and hotels $299 a month, with savings on annual plans and no commissions or booking fees. You’re live within minutes, and each month you see how many fans viewed and tapped your card.', '')]))
    note = section('white', 'Where it shows', '', '<p class="c-statement">In the app, on your venue’s page online, and in Concerto AI and Plan My Night.<br>Always labeled Concerto Partner.</p>', narrow=True)
    others = section('cream', 'Venues', 'Run a venue?',
                     '<p class="c-body">Venues can work with Concerto to keep their guide accurate and to share event-day updates with fans who saved a show. <a class="c-link" href="/partners/venues">Venue partnerships</a></p>', narrow=True)
    end = section('white', 'Questions', 'Questions about<br>Concerto Partners?',
                  '<p class="c-body">Email <a href="mailto:partners@concertocity.com">partners@concertocity.com</a>.</p>'
                  '<p class="c-actions"><a class="c-btn c-btn-navy" href="/partners/restaurants#join">For restaurants</a> <a class="c-btn c-btn-line" href="/partners/hotels#join">For hotels</a></p>', narrow=True)
    return '<main id="main-content" class="c-page">' + h + why + proof_strip() + what + how + note + others + end + '</main>'

def partners_why(kind='restaurants and hotels'):
    """Why a partner spot is worth paying for, in the founder's terms: fans find Concerto by looking
    up their venue, and where to eat and stay is the very next decision. Shared by all partner pages."""
    nxt = {'restaurants and hotels': 'where to eat and where to stay', 'restaurants': 'where to eat', 'hotels': 'where to stay'}[kind]
    return ('<section class="c-section c-cream" data-reveal><div class="c-wrap c-split"><div>' + eyebrow('Why it works') +
            '<h2 class="c-h2">Fans come for the venue.<br>Then they <span class="no-widow">plan the night.</span></h2></div><div>'
            '<p class="c-body">Fans find Concerto when they look up their venue before a show: the bag policy, parking, when doors open. Those searches already bring Concerto about '
            f'{PROOF_DAY} Google search appearances a day, eight times as many as in July.</p>'
            f'<p class="c-body">Once a fan knows what they can bring, the next thing they decide is {nxt}. The same page answers it, and Concerto Partners come first.</p>'
            '</div></div></section>')

PARTNER_V2 = {
    'partner-venues': dict(kicker='Venues', h1='Work with Concerto<br>on your venue guide.',
        lead='Fans use Concerto to plan their visit to 600+ venues worldwide: bag rules, entry, parking and rideshare. Work with us to keep your guide accurate and to reach fans before they arrive.',
        chips=['Accurate venue guides', 'Fans before they arrive', 'Custom partnerships'],
        rows=[('Keep your guide accurate.', 'Send us your current bag policy, entry, parking and rideshare details, and we&rsquo;ll update your guide in the app and on concertocity.com.'),
              ('Reach fans before they arrive.', 'Share event-day updates, like doors, set times or parking changes, with fans who saved a show at your venue.'),
              ('Promote what you offer.', 'Feature parking, premium seating, food and drink or hospitality to fans planning their visit.')],
        form_title='Tell us about<br>your venue.'),
    'partner-artists': dict(kicker='Artists and tours', h1='Work with Concerto<br>on your tour.',
        lead='Fans use Concerto to follow tours, check setlists and plan their night at each venue. Work with us to keep your tour accurate and to reach fans going to your shows.',
        chips=['Accurate tour pages', 'Fans going to your shows', 'Custom partnerships'],
        rows=[('Keep your tour page accurate.', 'Send confirmed dates, set times and setlist details, and we&rsquo;ll keep your tour page current in the app and on concertocity.com.'),
              ('Reach fans going to your shows.', 'Share tour news, merch or VIP information with fans who saved one of your shows.'),
              ('Promote a fan offer.', 'Feature a merch discount, presale or fan experience for Concerto members on your tour page.')],
        form_title='Tell us about<br>your tour.'),
}

def partner_page(key, form_html):
    c = PARTNER_V2.get(key)
    if c:  # venues and artists: plain, conversation-based partnerships
        h = hero(c['kicker'], c['h1'], c['lead'], '<a class="c-btn c-btn-navy" href="#interest">Get in touch</a><a class="c-link" href="/partners">All partnerships</a>', c['chips'], 'gold')
        what = section('white', 'What we can do together', 'Three ways to work<br>with Concerto.', rows([(t, b, '') for t, b in c['rows']]))
        how = section('cream', 'How it works', 'A conversation first.',
                      '<p class="c-body">Send us a note with what you have in mind. We&rsquo;ll reply by email to talk through the details, including pricing if it applies. There&rsquo;s no commitment until we both agree.</p>', narrow=True)
        form = (f'<section class="c-section c-white" id="interest"><div class="c-wrap c-split"><div>{eyebrow("Get in touch")}<h2 class="c-h2">{c["form_title"]}</h2>'
                '<p class="c-body">Questions first? Email <a href="mailto:partners@concertocity.com">partners@concertocity.com</a>.</p></div>'
                f'<div class="c-form">{form_html}</div></div></section>')
        return '<main id="main-content" class="c-page">' + h + what + how + form + '</main>'
    kicker, h1, lead, fans, explore, success = PARTNER[key]
    h = hero(kicker, h1, lead, '<a class="c-btn c-btn-navy" href="#interest">Get in touch</a><a class="c-link" href="/partners">All partnerships</a>', [], 'gold')
    form = (f'<section class="c-section c-cream" id="interest"><div class="c-wrap c-split"><div>{eyebrow("Get in touch")}<h2 class="c-h2">Tell us what you have in mind.</h2>'
            f'<p class="c-body">We&rsquo;ll reply by email.</p></div><div class="c-form">{form_html}</div></div></section>')
    return '<main id="main-content" class="c-page">' + h + form + '</main>'

def contact_page(form_html):
    h = hero('Contact', 'Let’s get you to<br>the right place.', 'Questions about your concert night, an idea for a collaboration, or a company inquiry. Start here.', '', ['support@concertocity.com', 'partners@concertocity.com'], 'cream')
    routes = ('<dl class="c-facts-list">'
              f'<div><dt>App support</dt><dd>{mail("support@concertocity.com")} or the <a href="/help">Help Center</a></dd></div>'
              f'<div><dt>Business</dt><dd>Write to {mail("partners@concertocity.com")}</dd></div>'
              '<div><dt>Media, creators, investors</dt><dd>Use the form, and pick the topic that fits</dd></div></dl>')
    form = f'<section class="c-section c-white"><div class="c-wrap c-split"><div>{eyebrow("How can we help?")}<h2 class="c-h2">Three ways in.</h2>{routes}</div><div class="c-form">{form_html}</div></div></section>'
    return '<main id="main-content" class="c-page">' + h + form + '</main>'

# ----- product and utility -----
def near_me():
    h = hero('Near Me', 'Concerts near you<br>this week.', 'Music shows in the next seven days, with the venue guide for each one.<br>Change the city to look somewhere else.',
             store_button('website-near-me', tone='white'), ['From Ticketmaster', 'Venue guides linked'], 'navy')
    live = ('<section class="c-section c-white c-live" data-live-near aria-labelledby="near-h"><div class="c-wrap">'
            '<p class="c-eyebrow">This week</p><h2 class="c-h2 c-h2-sm" id="near-h">Shows near <span data-live-city>you</span></h2>'
            '<p class="c-body" data-live-sub>Music shows in the next seven days, sorted by date.</p>'
            '<form class="c-live-form" data-live-form role="search"><label class="c-sr" for="near-city">City</label>'
            '<input id="near-city" type="search" placeholder="Try another city" autocomplete="address-level2"><button type="submit">Show shows</button></form>'
            '<div class="live-rail" data-live-rail aria-live="polite"><div class="live-skeleton"></div><div class="live-skeleton"></div><div class="live-skeleton"></div><div class="live-skeleton"></div></div>'
            '<noscript><p class="c-body">Turn on JavaScript to see shows near you, or open Near Me in Concerto.</p></noscript>'
            '<p class="c-qa-note">Tap a show to open it in Concerto, or open its venue guide for bag rules, doors, and parking.</p></div></section>')
    r = rows([('Find a show.', 'See what is on near you, by date.', '<a class="c-link" href="/tours">Browse tours</a>'),
              ('Save it.', 'A saved show gets Your Night: the venue’s rules, the setlist, and rideshare pickup on one page, plus a reminder on show day.', '<a class="c-link" href="/your-night">How Your Night works</a>'),
              ('Know the venue.', 'Every venue guide is researched from official sources and dated.', '<a class="c-link" href="/venues">Browse venues</a>')])
    return '<main id="main-content" class="c-page">' + h + live + section('cream', 'How it works', 'From a show near you to Your Night.', r) + close() + '</main>'

def perks_page():
    h = hero('Concerto Perks', 'Something extra<br>for your night.', 'Benefits from Concerto Partners, with the details to use them.<br>Availability depends on the venue, tour, and dates.', '', ['Offered by Concerto Partners', 'Always labeled'], 'gold')
    live = section('white', 'Available Perks', 'What is on right now.', '<div class="c-perks" data-live-perks aria-live="polite"><p class="c-body">Loading current partner benefits…</p><noscript><p class="c-body">Enable JavaScript to check current availability, or open Concerto.</p></noscript></div>')
    before = section('cream', 'Before you use one', 'Know what is included.', '<p class="c-body">Read the redemption instructions, dates, and conditions before you go.<br>Perks come from Concerto Partners, always labeled.</p>', narrow=True)
    return '<main id="main-content" class="c-page">' + h + live + before + close() + '</main>'

def search_page():
    h = hero('Ask Concerto', 'Ask about<br>your show.', 'Search venues, tours, and setlists, or ask a question. Answers come from Concerto’s venue guides and tour data, with the source linked.', ask_bar(), None, 'cream', 'c-hero-hub')
    answer = '<div class="c-answer" data-ask-answer hidden aria-live="polite"></div>'
    return '<main id="main-content" class="c-page">' + h + '<section class="c-section c-white c-search-section"><div class="c-wrap">' + answer + '<div data-site-search-results class="site-search-results c-search-results" aria-live="polite"><p class="c-body">Try an artist, tour, venue, or city.</p></div></div></section></main>'

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


def write_app_data():
    """Small data files the app reads instead of the 1.5 MB venue_info map.

    Home and the Venues hub only need a verified flag per venue; a venue page only needs its
    own record. Pulling the whole map for either blocks the JS thread while it parses.
    """
    out = ROOT / 'data'
    verified = {vid: ((rec.get('bagPolicy') or {}).get('verified') or '')
                for vid, rec in INFO.items() if (rec.get('bagPolicy') or {}).get('verified')}
    (out / 'venue_verified.json').write_text(json.dumps(verified, separators=(',', ':')) + '\n')
    per = out / 'venue_info'
    per.mkdir(exist_ok=True)
    for vid, rec in INFO.items():
        (per / f'{vid}.json').write_text(json.dumps(rec, separators=(',', ':'), ensure_ascii=False) + '\n')
    kb = (out / 'venue_verified.json').stat().st_size // 1024
    print(f'app data: venue_verified.json ({kb} KB) and {len(INFO)} per-venue files')

def write_search_index():
    """search-index.json powers BOTH search bars: the website's and the app's. It was a hand-made
    snapshot of 346 venues and 165 tours, so everything added later was unfindable. Rebuild it
    from the real data on every build; keep existing venue types, infer them for new venues."""
    import re as _re
    path = ROOT / 'search-index.json'
    old = {}
    try: old = {v['slug']: v.get('type') for v in json.loads(path.read_text()).get('venues', [])}
    except Exception: pass
    def vtype(name):
        n = name.lower()
        for word, t in (('stadium','Stadium'),('field','Stadium'),('bowl','Stadium'),
                        ('amphithe','Amphitheater'),('pavilion','Amphitheater'),('music center','Amphitheater'),
                        ('arena','Arena'),('center','Arena'),('centre','Arena'),('coliseum','Arena'),('garden','Arena'),
                        ('theatre','Theater'),('theater','Theater'),('hall','Theater'),('ballroom','Club'),('club','Club'),
                        ('festival','Festival'),('fest','Festival')):
            if word in n: return t
        return 'Venue'
    venues = [{'name': v['name'], 'slug': v['id'], 'type': old.get(v['id']) or vtype(v['name'])} for v in VENUES]
    tours = [{'name': t['tourName'], 'slug': t['tourId'], 'artist': t['artist']} for t in TOURS]
    path.write_text(json.dumps({'venues': venues, 'tours': tours}, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'search index: {len(venues)} venues, {len(tours)} tours')


def build():
    write_app_data()
    write_search_index()
    legacy = {f: (ROOT / f).read_text() for f in ['help.html', 'faq.html', 'privacy.html', 'terms.html', 'contact.html', 'partner-venues.html', 'partner-restaurants.html', 'partner-hotels.html', 'partner-artists.html']}
    form_of = lambda f: re.search(r'<form.*?</form>', legacy[f], re.S).group(0)
    rewrite('index.html', home()); rewrite('your-night.html', your_night()); rewrite('premium.html', premium());
    set_head('your-night.html', 'Your Night | Your Whole Show on One Page | Concerto', 'Save a concert and Concerto builds one page for that night: the venue, the tour, the city around it, and a memory card of your photos afterward. Free on iPhone.')
    set_head('premium.html', 'Concerto+ | Exit Plan, AI Bag Check, and Plan My Night', 'Concerto+ adds Exit Plan, AI Bag Check, Plan My Night, and more Concerto AI to Your Night. $29.99 a year, or a $4.99 Show Pass for one show.',
             [{'@type': 'Offer', 'price': '29.99', 'priceCurrency': 'USD', 'url': 'https://concertocity.com/premium', 'name': 'Yearly'},
              {'@type': 'Offer', 'price': '4.99', 'priceCurrency': 'USD', 'url': 'https://concertocity.com/premium', 'name': 'Show Pass'}])
    set_head('index.html', 'Concerto | Your Concert Night, on One Page', 'Concerto makes concert nights easier: guides to 600+ venues worldwide, tour dates and setlists, and things to do around every show. Free on iPhone.')
    rewrite('about.html', about())
    rewrite('venues.html', venues_hub()); rewrite('tours.html', tours_hub()); rewrite('setlists.html', setlists_hub()); rewrite('bagcheck.html', bagcheck())
    rewrite('bags.html', topic_page('bagPolicy', 'Bag policies', 'Concert bag policies,<br>venue by venue.', f'The bag rule at {N_V} venues, from each venue’s published policy, dated.'))
    rewrite('parking.html', topic_page('parking', 'Parking', 'Concert parking,<br>venue by venue.', 'Lots, garages, and routes. From official sources, dated.'))
    rewrite('rideshare.html', topic_page('rideshare', 'Rideshare', 'Drop-off and pickup,<br>venue by venue.', 'Where rideshare goes, before and after. Unconfirmed says unconfirmed.'))
    rewrite('concessions.html', topic_page('concessions', 'Food and drink', 'What is inside,<br>venue by venue.', 'Food, drink, and payment. From official sources, dated.'))
    # Hub titles say what people search for, not a tagline.
    for _rel, _t, _d in [
        ('bags.html', 'Concert Bag Policies by Venue (2026) | Concerto', f'Clear bag rules, size limits, and what you can bring, for {V_COPY} concert venues worldwide. From each venue’s official policy, dated.'),
        ('parking.html', 'Concert Parking by Venue: Lots, Garages & Tips | Concerto', f'Where to park for a concert at {V_COPY} venues worldwide: official lots, garages, and routes, from each venue’s own sources.'),
        ('rideshare.html', 'Uber & Lyft Pickup at Concert Venues | Concerto', f'Rideshare drop-off and pickup spots for concerts at {V_COPY} venues worldwide, from each venue’s official guidance.'),
        ('concessions.html', 'Food & Drink at Concert Venues | Concerto', f'What food and drinks are inside {V_COPY} concert venues worldwide, and how to pay, from official sources.'),
        ('near-me.html', 'Concerts Near Me This Week | Concerto', 'Concerts near you this week, with a guide to every venue: what to bring, parking, and places to eat nearby. Free on iPhone.'),
        ('bagcheck.html', 'AI Bag Check: Will My Bag Be Allowed? | Concerto', 'Take a photo of your bag and Concerto checks it against the venue’s published bag policy before you leave. Part of Concerto+.'),
        ('tours.html', 'Concert Tours: Dates & Setlists | Concerto', f'{N_T} concert tours with dates, the setlist each tour has been playing, and a guide to every venue.'),
        ('setlists.html', 'Concert Setlists by Tour | Concerto', f'Setlists for {N_S} current concert tours, labeled by source, so you know the songs before the show.'),
        ('venues.html', 'Concert Venue Guides: Bag Policy, Parking & Entry | Concerto', f'Guides to {V_COPY} concert venues worldwide: bag policy, entry, parking, rideshare, and what’s nearby, from official sources.'),
    ]:
        if (ROOT / _rel).exists(): set_head(_rel, _t, _d)
    for v in VENUES: rewrite(f'venue/{v["id"]}.html', venue_page(v))
    for t in TOURS: rewrite(f'tour/{t["tourId"]}.html', tour_page(t))
    for k, s in LIVE.items(): rewrite(f'setlist/{k}.html', setlist_page(k, s))
    ensure_page('founder.html', 'From the Founder | Concerto', 'Why Concerto exists: Jayce Wells on the Eras Tour night that started it, and what it took to build a concert guide to 600+ venues.', '/founder')
    rewrite('founder.html', founder());
    rewrite('press.html', press()); rewrite('investors.html', investors()); rewrite('creators.html', creators()); rewrite('partners.html', partners_hub())
    for k in PARTNER:
        # Hand-built pages (scripts/handbuilt/, e.g. the Oct 2026 restaurant partner page) are
        # copied in as written on every build instead of being generated.
        hb = ROOT / 'scripts' / 'handbuilt' / f'{k}.html'
        if hb.exists(): (ROOT / f'{k}.html').write_text(hb.read_text()); continue
        rewrite(f'{k}.html', partner_page(k, form_of(f'{k}.html')))
    rewrite('contact.html', contact_page(form_of('contact.html')))
    rewrite('near-me.html', near_me()); rewrite('search.html', search_page())
    rewrite('help.html', doc_page(legacy['help.html'], 'Help Center', 'Answers, in plain terms.', 'How Concerto works, in the order you’ll use it: find a show, save it, use Your Night, after the show, and Concerto+ when you want more.'))
    rewrite('faq.html', doc_page(legacy['faq.html'], 'FAQ', 'Questions, answered.', 'What Concerto is, what stays free, how Your Night and Concerto AI work, what Concerto+ adds, and how Concerto Partners works.'))
    rewrite('privacy.html', doc_page(legacy['privacy.html'], 'Legal', 'Privacy Policy.', 'What we collect, why, and the controls you have over it.', 'white', True))
    rewrite('terms.html', doc_page(legacy['terms.html'], 'Legal', 'Terms of Service.', 'The rules for using Concerto, in plain sections.', 'white', True))
    # Hand-built in Oct 2026 (paid-partner welcome after Stripe checkout): copied in as written.
    _hb = ROOT / 'scripts' / 'handbuilt' / 'partners-thank-you.html'
    if _hb.exists(): (ROOT / 'partners-thank-you.html').write_text(_hb.read_text())
    else:
        rewrite('partners-thank-you.html', simple('Inquiry received', 'Thank you for<br>reaching out.', 'Concerto will review the fit and contact you at the email you provided if there is a next step. This does not activate a partnership or publish an offer.', '<a class="c-link" href="/partners">Back to Partners</a>'))
    if (ROOT / 'contact-thank-you.html').exists():
        rewrite('contact-thank-you.html', simple('Message received', 'We have it.', 'Thanks for reaching out to Concerto. Your message is in the right place, and we will route it from the details you provided.', '<a class="c-link" href="/">Back to Concerto</a><a class="c-link" href="/about">About the company</a>'))
    rewrite('404.html', simple('Error 404', 'This page left<br>before the encore.', f'The page you are looking for does not exist or has moved. Everything else is still here, including guides for {V_COPY} venues worldwide.', '<a class="c-btn c-btn-navy" href="/">Back to Concerto</a><a class="c-link" href="/venues">Venue guides</a><a class="c-link" href="/search">Search</a>'))
    print(f'V8.1 site written: {N_V} venues, {N_T} tours, {len(LIVE)} setlists, and every company, partner, support, and legal page')



def set_head(rel, title, desc, offers=None):
    """Update a page's title, description, and social tags in place. The rest of the head stays byte for byte.
    offers: replaces the Product offers in the page's structured data (Concerto+ pricing)."""
    import re as _re, html as _h
    path = ROOT / rel
    src = path.read_text()
    t, d = _h.escape(title, quote=True), _h.escape(desc, quote=True)
    src = _re.sub(r'<title>.*?</title>', lambda m: f'<title>{t}</title>', src, count=1, flags=_re.S)
    for pat, val in ((r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{d}">'),
                     (r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{t}">'),
                     (r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{d}">'),
                     (r'<meta name="twitter:title" content="[^"]*">', f'<meta name="twitter:title" content="{t}">'),
                     (r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{d}">')):
        src = _re.sub(pat, lambda m, v=val: v, src, count=1)
    if offers is not None:
        src = _re.sub(r'"offers": \[[^\]]*\]', lambda m: '"offers": ' + json.dumps(offers), src, count=1)
        src = _re.sub(r'("@type": "Product", "name": "Concerto\+", "description": )"[^"]*"', lambda m: m.group(1) + json.dumps(desc), src, count=1)
    path.write_text(src)

# ---------------- writer ----------------
def ensure_page(rel, title, desc, path):
    """A new page takes About's shell with its own head: title, description, canonical, social."""
    import re as _re, html as _h
    src = (ROOT / 'about.html').read_text()
    url = f'https://concertocity.com{path}'
    t, d = _h.escape(title, quote=True), _h.escape(desc, quote=True)
    src = _re.sub(r'<title>.*?</title>', f'<title>{t}</title>', src, count=1, flags=_re.S)
    src = _re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{d}">', src, count=1)
    src = _re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', src, count=1)
    src = _re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{t}">', src, count=1)
    src = _re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{d}">', src, count=1)
    src = _re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">', src, count=1)
    (ROOT / rel).write_text(src)


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
    for f in ['near-me.html', 'partners.html', 'partner-restaurants.html', 'partner-hotels.html', 'partner-venues.html', 'partner-artists.html', 'creators.html', 'press.html',
              'investors.html', 'contact.html', 'faq.html', 'help.html', 'privacy.html', 'terms.html', 'partners-thank-you.html', 'search.html', '404.html']:
        restyle(f)
    print(f'V8 site written: home, your-night, premium, about, 3 hubs, 5 topic pages, {N_V} venues, {N_T} tours, {len(LIVE)} setlists')

if __name__ == '__main__':
    build()
