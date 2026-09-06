#!/usr/bin/env python3
import json, html, re
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parent.parent
SITE='https://concertocity.com'
APP='https://apps.apple.com/us/app/concerto-show-go/id6744903414'

def esc(x): return html.escape(str(x or ''), quote=True)
def slugify(x): return re.sub(r'[^a-z0-9]+','-',str(x).lower()).strip('-')
def head(title,desc,canonical,extra=''):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="apple-itunes-app" content="app-id=6744903414"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{esc(SITE+canonical)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{esc(SITE+canonical)}"><meta property="og:image" content="{SITE}/ConcertoSocialPreview.png"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&family=Playfair+Display:wght@500;600&display=swap" rel="stylesheet"><link rel="stylesheet" href="/css/public-v3.css">{extra}</head><body class="public-site">'''
def end(): return '<script src="/js/public-v3.js"></script></body></html>'

tours=json.loads((ROOT/'data/tours.json').read_text())
venues=json.loads((ROOT/'data/venues.json').read_text())
vi=json.loads((ROOT/'data/venue_info.json').read_text())
setlists=json.loads((ROOT/'setlists.json').read_text())
tour_by_id={t['tourId']:t for t in tours}
venue_by_id={v['id']:v for v in venues}

featured_ids=[
'ariana-grande-the-eternal-sunshine-tour-na','jonas-brothers-the-burning-up-tour-all-over-again','bruno-mars-the-romantic-tour','harry-styles-together-together-tour','bts-world-tour','noah-kahan-the-great-divide-tour']
featured=[tour_by_id[x] for x in featured_ids if x in tour_by_id]
feat_venues=['madison-square-garden','the-o2','kia-forum','red-rocks-amphitheatre','chase-center','american-airlines-center']
featured_v=[venue_by_id[x] for x in feat_venues if x in venue_by_id]

def tour_card(t, tag='Tour guide'):
    has=t['tourId'] in setlists
    micro='Setlist available' if has else tag
    return f'''<a class="rail-card" href="/tour/{esc(t['tourId'])}"><div class="rail-media" data-artist="{esc(t['artist'])}"></div><div class="rail-body"><span class="tag">{esc(micro)}</span><h3>{esc(t['artist'])}</h3><p>{esc(t['tourName'])}</p></div></a>'''

def venue_card(v):
    return f'''<a class="rail-card" href="/venue/{esc(v['id'])}"><div class="rail-media" data-vphoto data-vname="{esc(v['name'])}" data-vcity="{esc(v.get('city'))}" data-vlat="{esc(v.get('lat'))}" data-vlng="{esc(v.get('lng'))}"></div><div class="rail-body"><span class="tag">Verified guide</span><h3>{esc(v['name'])}</h3><p>{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}</p></div></a>'''

home=head('Concerto | From the Concert to the City®','Concerto is the concert companion for the show, the venue, and everything around it. Find tours and setlists, know the venue, discover what is nearby, and plan your night.','/')+f'''
<main>
<section class="hero-public"><div class="site-shell wide hero-grid"><div class="hero-copy"><p class="eyebrow">From the Concert to the City®</p><h1>The concert is only part of the night.</h1><p class="lead">Concerto brings the show, the venue, and the city around it into one trusted experience — so you can find the show, know what matters, and plan everything around it.</p><div class="hero-actions"><a class="btn-primary" href="{APP}" target="_blank" rel="noopener">Get Concerto for iPhone →</a><a class="btn-secondary" href="/tours">Explore tours</a></div><div class="hero-proof"><div class="proof"><strong>346</strong><span>venue guides</span></div><div class="proof"><strong>158</strong><span>tour guides</span></div><div class="proof"><strong>157</strong><span>setlists</span></div></div></div><div class="device-stage" aria-label="Concerto app previews"><div class="device one"><img src="/img/product/home.png" alt="Concerto Home screen"></div><div class="device two"><img src="/img/product/venue.png" alt="Concerto venue guide"></div><div class="device-badge"><strong>Your night, connected.</strong><span>One show becomes venue context, setlists, nearby places, weather, arrival, and getting home.</span></div></div></div></section>
<div class="logo-strip"><div class="site-shell logo-strip-inner"><span><b>Discover</b> the show</span><span><b>Know</b> the venue</span><span><b>Plan</b> the night</span><span><b>Go</b> with confidence</span></div></div>
<section class="story-section"><div class="site-shell"><div class="section-head"><p class="eyebrow">One night. One place.</p><div><h2>Everything around the show, finally connected.</h2><p>Concert planning is usually scattered across ticketing apps, venue sites, maps, weather, playlists, and group chats. Concerto turns those fragments into one useful show-night experience.</p></div></div><div class="story-grid"><article class="story-card light"><span class="number">01 · Discover</span><h3>Find what is happening.</h3><p>Browse current tours, events near you, and venue guides without digging across the internet.</p><a class="mini-link" href="/tours">Explore tours →</a></article><article class="story-card sand"><span class="number">02 · Prepare</span><h3>Know before you go.</h3><p>Verified bag policies, parking, concessions, entrances, accessibility, rideshare guidance, and more.</p><a class="mini-link" href="/venues">Browse venues →</a></article><article class="story-card"><span class="number">03 · Your Night</span><h3>Turn a saved show into a plan.</h3><p>Your show becomes the anchor for timing, weather, nearby places, setlists, getting there, and getting home.</p><a class="mini-link" href="/premium">Meet Concerto+ →</a></article></div></div></section>
<section class="product-split"><div class="product-copy"><p class="eyebrow">Concerto+</p><h2>Your whole night, planned around you.</h2><p>Free Concerto tells you what you need to know. Concerto+ helps decide what to do with it — using your saved show, venue, timing, weather, and nearby context.</p><div class="feature-list"><div class="feature-row"><div class="feature-icon">✓</div><div><b>Show-aware planning</b><span>Recommendations built around the concert you actually saved.</span></div></div><div class="feature-row"><div class="feature-icon">⌁</div><div><b>AI Bag Check</b><span>Compare what you are bringing against the venue policy before you leave.</span></div></div><div class="feature-row"><div class="feature-icon">↗</div><div><b>One connected night</b><span>Travel, nearby places, timing, weather, and venue context stay attached to the show.</span></div></div></div><div class="hero-actions"><a class="btn-primary" style="background:#C9A84C;color:#121E36!important" href="/premium">Explore Concerto+</a><a class="btn-secondary" style="border-color:rgba(255,255,255,.18);color:#fff;background:transparent" href="{APP}">Open in the app</a></div></div><div class="product-visual"><img src="/img/product/tour.png" alt="Concerto tour screen"></div></section>
<section class="discovery"><div class="site-shell wide"><div class="rail-head"><h2>On the road now.</h2><a href="/tours">View all {len(tours)} tours →</a></div><div class="card-rail">{''.join(tour_card(t) for t in featured)}</div></div></section>
<section class="navy-band"><div class="site-shell"><div class="section-head"><p class="eyebrow">The Concerto standard</p><div><h2>Useful only if you can trust it.</h2><p>Critical venue information is researched from official sources and dated. If something has not been confirmed, Concerto should say so instead of filling the gap with a guess.</p></div></div><div class="metrics"><div class="metric"><strong>346</strong><span>venues with structured show-night information</span></div><div class="metric"><strong>8</strong><span>core venue information sections per verified guide</span></div><div class="metric"><strong>1</strong><span>source of truth across app and web</span></div></div><div class="trust-note"><span>Verified facts stay free. Personalization and orchestration power Concerto+.</span><a class="text-link" href="/about">How Concerto works →</a></div></div></section>
<section class="discovery"><div class="site-shell wide"><div class="rail-head"><h2>Know the venue before you arrive.</h2><a href="/venues">View all {len(venues)} venues →</a></div><div class="card-rail">{''.join(venue_card(v) for v in featured_v)}</div></div></section>
<section class="cta-band"><div class="site-shell"><p class="eyebrow">Your next show starts here</p><h2>Less searching. More night.</h2><p>Find the show, save it, know the venue, and let Concerto keep everything around the night connected.</p><div class="hero-actions" style="justify-content:center"><a class="btn-primary" href="{APP}">Get the App →</a><a class="btn-secondary" href="/near-me">See what’s near you</a></div></div></section>
</main>'''+end()
(ROOT/'index.html').write_text(home)

# Hubs
v_cards=[]
for v in sorted(venues,key=lambda x:(x.get('name') or '').lower()):
    v_cards.append(f'''<a class="catalog-card filter-item venue-item" href="/venue/{esc(v['id'])}"><div class="thumb" data-vphoto data-vname="{esc(v['name'])}" data-vcity="{esc(v.get('city'))}" data-vlat="{esc(v.get('lat'))}" data-vlng="{esc(v.get('lng'))}"></div><div class="body"><span class="micro">Verified venue guide</span><h2>{esc(v['name'])}</h2><p>{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}{' · '+esc(v.get('country')) if v.get('country') else ''}</p></div></a>''')
venues_html=head('Concert Venue Guides, Bag Policies, Parking & More | Concerto','Explore verified concert venue guides with bag policies, parking, concessions, rideshare, accessibility, entrances, ticket pickup, and re-entry information.','/venues')+f'''<main><section class="page-hero-v3"><div class="site-shell"><p class="eyebrow">Every venue. Every rule.</p><h1>Know before you go.</h1><p>Verified venue information for arenas, stadiums, theaters, amphitheaters, and festivals — researched from official sources and organized for show night.</p><div class="hero-meta"><span class="meta-pill">{len(venues)} venue guides</span><span class="meta-pill">Official-source verification</span><span class="meta-pill">Bag policy · Parking · Rideshare · More</span></div><div class="search-wrap"><input aria-label="Search venues" data-filter-target=".venue-item" placeholder="Search venue, city, or state"></div></div></section><section class="catalog-section"><div class="site-shell wide"><div class="catalog-grid">{''.join(v_cards)}</div></div></section></main>'''+end()
(ROOT/'venues.html').write_text(venues_html)

t_cards=[]
for t in sorted(tours,key=lambda x:(x.get('artist') or '').lower()):
    has=t['tourId'] in setlists
    t_cards.append(f'''<a class="catalog-card filter-item tour-item" href="/tour/{esc(t['tourId'])}"><div class="thumb" data-artist="{esc(t['artist'])}"></div><div class="body"><span class="micro">{'Setlist available' if has else 'Tour guide'}</span><h2>{esc(t['artist'])}</h2><p>{esc(t['tourName'])}</p></div></a>''')
tours_html=head('Concert Tours & Tour Setlists | Concerto','Browse current concert tours, official tour links, show guides, and available setlists on Concerto.','/tours')+f'''<main><section class="page-hero-v3"><div class="site-shell"><p class="eyebrow">On the road now</p><h1>Follow the tour.</h1><p>Browse active tour guides and jump directly into available setlists, venue context, and the show-night experience in Concerto.</p><div class="hero-meta"><span class="meta-pill">{len(tours)} tours</span><span class="meta-pill">{len(setlists)} setlists</span></div><div class="search-wrap"><input aria-label="Search tours" data-filter-target=".tour-item" placeholder="Search artist or tour"></div></div></section><section class="catalog-section"><div class="site-shell wide"><div class="catalog-grid">{''.join(t_cards)}</div></div></section></main>'''+end()
(ROOT/'tours.html').write_text(tours_html)

s_cards=[]
for tid,s in sorted(setlists.items(),key=lambda kv:(kv[1].get('artist') or '').lower()):
    if tid not in tour_by_id: continue
    s_cards.append(f'''<a class="catalog-card filter-item setlist-item" href="/setlist/{esc(tid)}"><div class="thumb" data-artist="{esc(s.get('artist'))}"></div><div class="body"><span class="micro">{len(s.get('songs') or [])} songs · updated {esc(s.get('updated'))}</span><h2>{esc(s.get('artist'))}</h2><p>{esc(s.get('tour'))}</p></div></a>''')
setlists_html=head('Concert Setlists & Tour Setlists | Concerto','Find current concert setlists and tour setlists for artists on the road now. Concerto connects each setlist to the tour, venue, and show-night experience.','/setlists')+f'''<main><section class="page-hero-v3"><div class="site-shell"><p class="eyebrow">Know every song</p><h1>Setlists, without the hunt.</h1><p>Current tour setlists organized around the artist and tour you care about — with the rest of the night one tap away in Concerto.</p><div class="hero-meta"><span class="meta-pill">{len(setlists)} setlists</span><span class="meta-pill">Tour-connected</span></div><div class="search-wrap"><input aria-label="Search setlists" data-filter-target=".setlist-item" placeholder="Search artist or tour"></div></div></section><section class="catalog-section"><div class="site-shell wide"><div class="catalog-grid">{''.join(s_cards)}</div></div></section></main>'''+end()
(ROOT/'setlists.html').write_text(setlists_html)

# Detail pages
(ROOT/'venue').mkdir(exist_ok=True)
for v in venues:
    slug=v['id']; info=vi.get(slug,{})
    sections=[]
    order=[('bagPolicy','Bag Policy'),('parking','Parking'),('rideshare','Rideshare'),('concessions','Concessions'),('accessibility','Accessibility'),('reEntry','Re-Entry'),('ticketPickup','Ticket Pickup'),('gates','Entrances & Gates')]
    for key,label in order:
        x=info.get(key) or {}
        body=x.get('summary') or x.get('note') or x.get('body') or ''
        if body:
            ver=x.get('verified') or ''
            official=x.get('officialLink') or ''
            link=f'<a class="text-link" href="{esc(official)}" target="_blank" rel="noopener">Official source →</a>' if official else ''
            sections.append(f'''<article class="info-card"><div class="label">{esc(label)}</div><h3>{esc(x.get('title') or label)}</h3><p>{esc(body)}</p>{f'<span class="verified">Verified {esc(ver)}</span>' if ver else ''}{f'<div class="link-row">{link}</div>' if link else ''}</article>''')
    desc=f"{v['name']} concert guide with bag policy, parking, rideshare, concessions, accessibility, entrances, and other show-night information."
    ld={'@context':'https://schema.org','@type':'MusicVenue','name':v['name'],'address':{'@type':'PostalAddress','addressLocality':v.get('city') or '','addressRegion':v.get('state') or '','addressCountry':v.get('country') or ''},'url':SITE+'/venue/'+slug}
    extra='<script type="application/ld+json">'+json.dumps(ld).replace('</','<\\/')+'</script>'
    page=head(f"{v['name']} Bag Policy, Parking & Venue Guide | Concerto",desc,f'/venue/{slug}',extra)+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/venues">Venues</a> &nbsp;/&nbsp; {esc(v['name'])}</div><div class="detail-grid"><div><p class="eyebrow">Venue guide</p><h1>{esc(v['name'])}</h1><p class="subtitle">{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}{' · '+esc(v.get('country')) if v.get('country') else ''}</p><div class="hero-meta"><span class="meta-pill">Verified venue information</span><span class="meta-pill">Updated from official sources</span></div></div><div class="detail-media" data-vphoto data-vname="{esc(v['name'])}" data-vcity="{esc(v.get('city'))}" data-vlat="{esc(v.get('lat'))}" data-vlng="{esc(v.get('lng'))}"></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main"><section class="detail-section"><p class="eyebrow">Know before you go</p><h2>What matters at {esc(v['name'])}.</h2><div class="info-grid">{''.join(sections)}</div></section><section class="detail-section"><p class="eyebrow">From the Concert to the City®</p><h2>The venue is only one part of the night.</h2><p>Save your show in Concerto to keep venue rules, nearby places, weather, timing, getting there, and getting home attached to the same night.</p><div class="link-row"><a class="btn-primary" href="{APP}">Open Concerto →</a><a class="btn-secondary" href="/near-me">Explore nearby</a></div></section></div><aside><div class="side-card"><span class="tag">Concerto venue guide</span><h3>Planning a show here?</h3><p>Use Concerto on iPhone for the full saved-show experience around {esc(v['name'])}.</p><a class="btn-primary" href="{APP}">Get the App</a><a class="btn-secondary" href="/venues">Browse more venues</a></div></aside></div></section></main>'''+end()
    (ROOT/'venue'/f'{slug}.html').write_text(page)

(ROOT/'tour').mkdir(exist_ok=True); (ROOT/'setlist').mkdir(exist_ok=True)
for t in tours:
    slug=t['tourId']; s=setlists.get(slug); desc=f"{t['artist']} {t['tourName']} tour guide with current setlist information and links to plan the show in Concerto."
    ld={'@context':'https://schema.org','@type':'MusicGroup','name':t['artist'],'url':t.get('tourWebsite') or SITE+'/tour/'+slug}
    extra='<script type="application/ld+json">'+json.dumps(ld).replace('</','<\\/')+'</script>'
    set_teaser=''
    if s:
        first=(s.get('songs') or [])[:8]
        set_teaser=f'''<section class="detail-section"><p class="eyebrow">Latest setlist</p><h2>{len(s.get('songs') or [])} songs, ready.</h2><ol class="song-list">{''.join('<li>'+esc(x)+'</li>' for x in first)}</ol><div class="link-row"><a class="btn-secondary" href="/setlist/{esc(slug)}">View full setlist →</a></div></section>'''
    official=f'<a class="btn-secondary" href="{esc(t.get("tourWebsite"))}" target="_blank" rel="noopener">Official tour site ↗</a>' if t.get('tourWebsite') else ''
    page=head(f"{t['artist']} — {t['tourName']} Tour & Setlist | Concerto",desc,f'/tour/{slug}',extra)+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/tours">Tours</a> &nbsp;/&nbsp; {esc(t['artist'])}</div><div class="detail-grid"><div><p class="eyebrow">On tour</p><h1>{esc(t['artist'])}</h1><p class="subtitle">{esc(t['tourName'])}</p><div class="link-row">{official}<a class="btn-primary" href="{APP}">Open in Concerto →</a></div></div><div class="detail-media" data-artist="{esc(t['artist'])}"></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main">{set_teaser}<section class="detail-section"><p class="eyebrow">The whole night</p><h2>Tour guide meets show-night guide.</h2><p>Concerto connects the tour to the venue and the city around it. Save a show to keep setlists, venue information, nearby places, weather, timing, arrival, and getting home together.</p></section></div><aside><div class="side-card"><span class="tag">Tour guide</span><h3>Going to this tour?</h3><p>Save the show in Concerto and turn a tour date into Your Night.</p><a class="btn-primary" href="{APP}">Get the App</a>{f'<a class="btn-secondary" href="/setlist/{esc(slug)}">View setlist</a>' if s else ''}</div></aside></div></section></main>'''+end()
    (ROOT/'tour'/f'{slug}.html').write_text(page)
    if s:
        songs=s.get('songs') or []
        note=s.get('note') or ''
        desc2=f"{t['artist']} {t['tourName']} setlist: {len(songs)} songs, updated {s.get('updated','')}. View the full tour setlist on Concerto."
        ld2={'@context':'https://schema.org','@type':'ItemList','name':f"{t['artist']} {t['tourName']} setlist",'numberOfItems':len(songs),'itemListElement':[{'@type':'ListItem','position':i+1,'name':song} for i,song in enumerate(songs)]}
        extra2='<script type="application/ld+json">'+json.dumps(ld2).replace('</','<\\/')+'</script>'
        sp=head(f"{t['artist']} {t['tourName']} Setlist | Concerto",desc2,f'/setlist/{slug}',extra2)+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/setlists">Setlists</a> &nbsp;/&nbsp; <a href="/tour/{esc(slug)}">{esc(t['artist'])}</a></div><div class="detail-grid"><div><p class="eyebrow">Tour setlist</p><h1>{esc(t['artist'])}</h1><p class="subtitle">{esc(t['tourName'])} · {len(songs)} songs</p><div class="hero-meta"><span class="meta-pill">Updated {esc(s.get('updated'))}</span><span class="meta-pill">{esc(note) if note else 'Tour setlist'}</span></div></div><div class="detail-media" data-artist="{esc(t['artist'])}"></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main"><section class="detail-section"><p class="eyebrow">Setlist</p><h2>What they’re playing.</h2><ol class="song-list">{''.join('<li>'+esc(x)+'</li>' for x in songs)}</ol></section><section class="detail-section"><p class="eyebrow">Go beyond the songs</p><h2>Plan the rest of the night.</h2><p>The setlist is one part of the show. Concerto connects it with the venue, nearby places, weather, arrival, and getting home.</p><div class="link-row"><a class="btn-primary" href="{APP}">Open Concerto →</a><a class="btn-secondary" href="/tour/{esc(slug)}">View tour guide</a></div></section></div><aside><div class="side-card"><span class="tag">Setlist</span><h3>{esc(t['tourName'])}</h3><p>Updated {esc(s.get('updated'))}. Setlists can change by date; use this as a current tour reference.</p><a class="btn-primary" href="{APP}">Save your show</a><a class="btn-secondary" href="/setlists">More setlists</a></div></aside></div></section></main>'''+end()
        (ROOT/'setlist'/f'{slug}.html').write_text(sp)

print(f'Built public site: home + {len(venues)} venues + {len(tours)} tours + {len(setlists)} setlists')
