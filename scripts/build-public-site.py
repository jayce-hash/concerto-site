#!/usr/bin/env python3
import json, html, re, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from night_components import venue_section_card, setlist_card_for
from public_chrome import header_html, page_end, HEAD_ASSETS, product_screen, photo_slot, app_link, smart_banner, app_link_campaign
SITE='https://concertocity.com'
APP='https://apps.apple.com/us/app/concerto-show-go/id6744903414'

# Several venues share a name in different cities (four Orpheum Theatres, two 3Arenas). Their
# pages need the city in the title and description, or search engines see duplicates.
def shown_name(v):
    from collections import Counter
    global _NAME_COUNTS
    try: _NAME_COUNTS
    except NameError:
        _NAME_COUNTS = Counter(x['name'].strip().lower() for x in venues)
    return f"{v['name']} {v['city']}" if _NAME_COUNTS[v['name'].strip().lower()] > 1 else v['name']

def esc(x): return html.escape(str(x or ''), quote=True)
def head(title,desc,canonical,extra='',robots='index,follow,max-image-preview:large',banner=None):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{banner or smart_banner()}<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><meta name="robots" content="{esc(robots)}"><link rel="canonical" href="{esc(SITE+canonical)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{esc(SITE+canonical)}"><meta property="og:image" content="{SITE}/ConcertoSocialPreview.png"><meta property="og:site_name" content="Concerto"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE}/ConcertoSocialPreview.png"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png">{HEAD_ASSETS}{extra}</head><body class="public-site">'''+header_html(canonical)
def end(): return page_end()

tours=json.loads((ROOT/'data/tours.json').read_text())
venues=json.loads((ROOT/'data/venues.json').read_text())
vi=json.loads((ROOT/'data/venue_info.json').read_text())
setlists=json.loads((ROOT/'setlists.json').read_text())
stage_times=json.loads((ROOT/'data/stage_times.json').read_text()) if (ROOT/'data/stage_times.json').exists() else {}
def clock12(t):
    try:
        h,m=[int(x) for x in t.split(':')[:2]]; return f"{h%12 or 12}:{m:02d} {'PM' if h>=12 else 'AM'}"
    except Exception: return t
def stage_line(slug):
    h=stage_times.get(slug)
    if not h or not h.get('headliner'): return ''
    return f'<p class="stage-line"><b>Headliner around {clock12(h["headliner"])}</b> · based on {h["shows"]} shows this tour. Venues that verify their page can set the exact time.</p>'
def setlist_provenance(sl):
    """Honest label for where a song list came from. An official tour playlist is
    trustworthy content but not proof of the performed set or its order."""
    src=sl.get('source') or {}; note=(sl.get('note') or '')
    if src.get('eventDate') or src.get('provider')=='setlist.fm':
        return f"Confirmed setlist from {esc(src.get('venue') or 'a recent show')}{' on '+esc(src['eventDate']) if src.get('eventDate') else ''}{' · draft' if src.get('draft') else ''}"
    if 'apple music' in note.lower() or src.get('provider')=='apple-music':
        return f"Official tour playlist (Apple Music) · updated {esc(sl.get('updated',''))}"
    return f"Updated {esc(sl.get('updated',''))}"
tour_by_id={t['tourId']:t for t in tours}
venue_by_id={v['id']:v for v in venues}
available_setlists={k:v for k,v in setlists.items() if (v.get('songs') or []) and k in tour_by_id}
coming_setlists={k:v for k,v in setlists.items() if not (v.get('songs') or []) and k in tour_by_id}

featured_ids=['ariana-grande-the-eternal-sunshine-tour-na','jonas-brothers-the-burning-up-tour-all-over-again','bruno-mars-the-romantic-tour','harry-styles-together-together-tour','bts-world-tour','noah-kahan-the-great-divide-tour']
featured=[tour_by_id[x] for x in featured_ids if x in tour_by_id]
feat_venues=['madison-square-garden','kia-forum','bridgestone-arena','red-rocks-amphitheatre','chase-center','american-airlines-center']
featured_v=[venue_by_id[x] for x in feat_venues if x in venue_by_id]
featured_set_ids=['jonas-brothers-the-burning-up-tour-all-over-again','ariana-grande-the-eternal-sunshine-tour-na','harry-styles-together-together-tour']
featured_set=[tour_by_id[x] for x in featured_set_ids if x in available_setlists and x in tour_by_id]

def venue_fallback(v):
    slug=v['id']
    folder=ROOT/'img'/'cityguides'/slug
    if not folder.exists(): return ''
    # Prefer the venue-named WebP, then any WebP containing the venue name.
    # Do not feature the supplied watermarked MSG fallback; use the live venue
    # photo source or the neutral fallback until a clean approved image exists.
    excluded={'img/cityguides/madison-square-garden/Madison-Square-Garden.webp'}
    webps=[p for p in folder.glob('*.webp') if p.relative_to(ROOT).as_posix() not in excluded]
    if not webps: return ''
    norm=lambda s: re.sub(r'[^a-z0-9]','',s.lower())
    vn=norm(v['name'])
    hit=next((p for p in webps if norm(p.stem)==vn),None) or next((p for p in webps if vn in norm(p.stem) or norm(p.stem) in vn),None)
    return '/'+str((hit or webps[0]).relative_to(ROOT)).replace('\\','/')

def artist_media(t, cls='rail-media'):
    return f'<div class="{cls}" data-artist="{esc(t["artist"])}"></div>'
def fallback_attr(fb):
    return (' data-fallback-src="'+esc(fb)+'"') if fb else ''
def venue_media(v, cls='rail-media'):
    fb=venue_fallback(v)
    return '<div class="'+cls+'" data-vphoto data-vname="'+esc(v['name'])+'" data-vcity="'+esc(v.get('city'))+'" data-vlat="'+esc(v.get('lat'))+'" data-vlng="'+esc(v.get('lng'))+'"'+fallback_attr(fb)+'></div>'

def ld_json(obj):
    return '<script type="application/ld+json">'+json.dumps(obj).replace('</','<\\/')+'</script>'
def breadcrumb_ld(items):
    return ld_json({'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i+1,'name':n,'item':SITE+u} for i,(n,u) in enumerate(items)]})
def related_venues(v,n=4):
    same_city=[x for x in venues if x['id']!=v['id'] and (x.get('city') or '').lower()==(v.get('city') or '').lower()]
    same_state=[x for x in venues if x['id']!=v['id'] and x not in same_city and v.get('state') and x.get('state')==v.get('state')]
    pool=(same_city+same_state)[:n]
    if len(pool)<n:
        rest=[x for x in venues if x['id']!=v['id'] and x not in pool]
        i=venues.index(v); pool+= (rest[i:]+rest[:i])[:n-len(pool)]
    return pool
def related_tours(t,n=4):
    with_set=[x for x in tours if x['tourId']!=t['tourId'] and x['tourId'] in available_setlists]
    i=tours.index(t)
    return (with_set[i%max(1,len(with_set)):]+with_set[:i%max(1,len(with_set))])[:n]
def related_list(items,kind):
    if not items: return ''
    if kind=='venue':
        cards=''.join(f'<a class="coming-card" href="/venue/{esc(x["id"])}"><strong>{esc(x["name"])}</strong><span>{esc(x.get("city"))}{", "+esc(x.get("state")) if x.get("state") else ""}</span></a>' for x in items)
        return f'<section class="library-related"><div class="site-shell"><div class="section-lead"><p class="eyebrow">Nearby and related</p><h2>More venue guides.</h2></div><div class="coming-grid related-grid">{cards}</div></div></section>'
    cards=''.join(f'<a class="coming-card" href="/tour/{esc(x["tourId"])}"><strong>{esc(x["artist"])}</strong><span>{esc(x["tourName"])} · Setlist available</span></a>' for x in items)
    return f'<section class="library-related"><div class="site-shell"><div class="section-lead"><p class="eyebrow">Also on the road</p><h2>More tours with setlists.</h2></div><div class="coming-grid related-grid">{cards}</div></div></section>'


def ui_next_show():
    return ('<div class="ui ui-next" aria-label="Your Next Show card as it appears in the app"><span class="ui-kicker">Your next show</span><h3>Jonas Brothers</h3><p class="ui-tour">The Burning Up Tour All Over Again</p><p class="ui-meta">American Airlines Center · Nov 10 · Doors 7:30 PM</p><div class="ui-rule"></div><div class="ui-count"><b data-countdown="2026-11-10T19:30:00-06:00">64</b><span>days until show day</span></div><span class="ui-link">View Your Night →</span></div>')
def ui_bag_policy(slug):
    v=vi.get(slug) or {}; bp=v.get('bagPolicy') or {}
    allowed=''.join('<li class="ok">'+esc(x)+'</li>' for x in (bp.get('allowed') or [])[:4]); no=''.join('<li class="no">'+esc(x)+'</li>' for x in (bp.get('prohibited') or [])[:3])
    note=('<p class="ui-note">'+esc(bp.get('note'))+'</p>') if bp.get('note') else ''
    return ('<div class="ui ui-section" aria-label="Bag Policy section as it appears in the app"><div class="ui-section-head"><span class="ui-icon"></span><h3>Bag Policy</h3><span class="ui-verified">'+esc(bp.get('verified'))+'</span></div><p>'+esc(bp.get('summary'))+'</p><div class="ui-lists"><div><span class="ui-label">Allowed</span><ul>'+allowed+'</ul></div><div><span class="ui-label">Not allowed</span><ul>'+no+'</ul></div></div>'+note+'<span class="ui-link">Official Info ↗</span></div>')
def ui_getting_out(slug):
    v=vi.get(slug) or {}; rs=v.get('rideshare') or {}
    return ('<div class="ui ui-exit" aria-label="Getting Home card as it appears in the app"><span class="ui-kicker">Encore exit</span><h3>Getting Home</h3><p>'+esc(rs.get('note') or rs.get('summary'))+'</p><div class="ui-pills"><span>Uber</span><span>Lyft</span></div></div>')
def ui_setlist(slug, n=6):
    sl=setlists.get(slug) or {}; songs=(sl.get('songs') or [])[:n]; total=len(sl.get('songs') or [])
    items=''.join('<li><i>%02d</i>%s</li>'%(i+1,esc(x)) for i,x in enumerate(songs))
    return ('<div class="ui ui-setlist" aria-label="Setlist as it appears in the app"><div class="ui-section-head"><h3>Setlist</h3><span class="ui-meta">'+str(total)+' songs · Updated '+esc((sl.get('updated') or '')[:10])+'</span></div><ol>'+items+'</ol><span class="ui-link">View all '+str(total)+' songs</span></div>')

def tour_status(t):
    s=setlists.get(t['tourId'])
    if s and (s.get('songs') or []): return 'Setlist available','status-live'
    if s: return 'Setlist coming soon','status-soon'
    return 'Tour guide','status-soon'

def tour_card(t):
    status,_=tour_status(t)
    return f'''<a class="rail-card" href="/tour/{esc(t['tourId'])}">{artist_media(t)}<div class="rail-body"><span class="tag">{esc(status)}</span><h3>{esc(t['artist'])}</h3><p>{esc(t['tourName'])}</p></div></a>'''

def venue_card(v):
    return f'''<a class="rail-card" href="/venue/{esc(v['id'])}">{venue_media(v)}<div class="rail-body"><span class="tag">Verified guide</span><h3>{esc(v['name'])}</h3><p>{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}</p></div></a>'''

def featured_tour(t, label=None):
    status,_=tour_status(t)
    return f'''<a class="featured-card" href="/tour/{esc(t['tourId'])}"><div class="featured-media" data-artist="{esc(t['artist'])}"></div><div class="featured-copy-overlay"><span class="tag">{esc(label or status)}</span><h3>{esc(t['artist'])}</h3><p>{esc(t['tourName'])}</p></div></a>'''

def featured_venue(v):
    fb=venue_fallback(v)
    return f'''<a class="featured-card" href="/venue/{esc(v['id'])}"><div class="featured-media" data-vphoto data-vname="{esc(v['name'])}" data-vcity="{esc(v.get('city'))}" data-vlat="{esc(v.get('lat'))}" data-vlng="{esc(v.get('lng'))}"{fallback_attr(fb)}></div><div class="featured-copy-overlay"><span class="tag">Verified venue guide</span><h3>{esc(v['name'])}</h3><p>{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}</p></div></a>'''

# Homepage — product/company story first; directories stay discoverable but do not dictate the design.
home_ld=ld_json({'@context':'https://schema.org','@graph':[{'@type':'Organization','@id':SITE+'/#org','name':'Concerto','url':SITE,'logo':SITE+'/img/app-icon.png','slogan':'From the Concert to the City','sameAs':['https://instagram.com/theconcertoapp','https://www.tiktok.com/@theconcertoapp','https://www.youtube.com/@theconcertoapp',APP]},{'@type':'WebSite','@id':SITE+'/#site','url':SITE,'name':'Concerto','publisher':{'@id':SITE+'/#org'},'potentialAction':{'@type':'SearchAction','target':SITE+'/search?q={search_term_string}','query-input':'required name=search_term_string'}},{'@type':'SoftwareApplication','name':'Concerto','operatingSystem':'iOS','applicationCategory':'EntertainmentApplication','url':APP,'offers':{'@type':'Offer','price':'0','priceCurrency':'USD'}}]})
live=sum(1 for v in setlists.values() if v.get('songs'))
GET_APP=app_link_campaign('website-home')
from experience_pages import home_page
home = home_page(head, home_ld)

(ROOT/'index.html').write_text(home)

# Venues hub — editorial context before the full database.
v_cards=[]
for v in sorted(venues,key=lambda x:(x.get('name') or '').lower()):
    v_cards.append(f'''<a class="catalog-card filter-item venue-item" href="/venue/{esc(v['id'])}">{venue_media(v,'thumb')}<div class="body"><span class="micro status-live">Verified venue guide</span><h2>{esc(v['name'])}</h2><p>{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}{' · '+esc(v.get('country')) if v.get('country') else ''}</p></div></a>''')
venue_featured=featured_v[:3]
venues_html=head('Concert Venue Guides, Bag Policies, Parking & More | Concerto','Explore verified concert venue guides with bag policies, parking, rideshare, concessions, accessibility, entrances, and other show-night information.','/venues')+f'''<main><section class="page-hero-v3"><div class="site-shell"><p class="eyebrow">The venue guide</p><h1>Know before you go.</h1><p>Bag rules, parking, entry, and getting home. Find the details for your venue before you leave.</p><div class="hero-meta"><span class="meta-pill">{len(venues)} venue guides</span><span class="meta-pill">Official-source verification</span><span class="meta-pill">Bag policy · Parking · Rideshare · More</span></div><div class="search-wrap"><input aria-label="Search venues" data-filter-target=".venue-item" placeholder="Search venue, city, or state"></div></div></section><section class="featured-strip"><div class="site-shell wide"><div class="rail-head"><div><h2>Start with the venue.</h2><p>Explore a few of the guides available in Concerto.</p></div><a href="{APP}" target="_blank" rel="noopener">Open in the app</a></div><div class="featured-grid">{''.join(featured_venue(v) for v in venue_featured)}</div></div></section><section class="catalog-section"><div class="site-shell wide"><div class="catalog-intro"><h2>All venue guides.</h2><p>Search by venue, city, or state. Open any guide for its sources and verification dates.</p></div><div class="catalog-grid">{''.join(v_cards)}</div></div></section></main>'''+end()
(ROOT/'venues.html').write_text(venues_html)

# Tours hub.
t_cards=[]
for t in sorted(tours,key=lambda x:(x.get('artist') or '').lower()):
    status,status_cls=tour_status(t)
    t_cards.append(f'''<a class="catalog-card filter-item tour-item" href="/tour/{esc(t['tourId'])}">{artist_media(t,'thumb')}<div class="body"><span class="micro {status_cls}">{esc(status)}</span><h2>{esc(t['artist'])}</h2><p>{esc(t['tourName'])}</p></div></a>''')
tours_html=head('Concert Tours & Tour Setlists | Concerto','Browse concert tour guides, available setlists, and venue context on Concerto.','/tours')+f'''<main><section class="page-hero-v3"><div class="site-shell"><p class="eyebrow">The tour guide</p><h1>Follow the tour.</h1><p>Find your artist’s tour and its available setlist. Bring the details into your night with Concerto.</p><div class="hero-meta"><span class="meta-pill">{len(tours)} tour guides</span><span class="meta-pill">{len(available_setlists)} published setlists</span></div><div class="search-wrap"><input aria-label="Search tours" data-filter-target=".tour-item" placeholder="Search artist or tour"></div></div></section><section class="featured-strip"><div class="site-shell wide"><div class="rail-head"><div><h2>Featured tours.</h2><p>A few tours to explore.</p></div><a href="/setlists">Explore setlists →</a></div><div class="featured-grid">{''.join(featured_tour(t) for t in featured[:3])}</div></div></section><section class="catalog-section"><div class="site-shell wide"><div class="catalog-intro"><h2>All tour guides.</h2><p>Open a tour for its details and available setlist.</p></div><div class="catalog-grid">{''.join(t_cards)}</div></div></section></main>'''+end()
(ROOT/'tours.html').write_text(tours_html)

# Setlists hub — only populated setlists are marketed as setlists; coming-soon records remain tour trackers.
s_cards=[]
for tid,s in sorted(available_setlists.items(),key=lambda kv:(kv[1].get('artist') or '').lower()):
    songs=s.get('songs') or []
    s_cards.append(f'''<a class="catalog-card filter-item setlist-item" href="/setlist/{esc(tid)}"><div class="thumb" data-artist="{esc(s.get('artist'))}"></div><div class="body"><span class="micro status-live">{len(songs)} songs · updated {esc(s.get('updated'))}</span><h2>{esc(s.get('artist'))}</h2><p>{esc(s.get('tour'))}</p></div></a>''')
coming_cards=[]
for tid,s in sorted(coming_setlists.items(),key=lambda kv:(kv[1].get('artist') or '').lower()):
    coming_cards.append(f'''<a class="coming-card filter-item setlist-item" href="/tour/{esc(tid)}"><strong>{esc(s.get('artist'))}</strong><span>{esc(s.get('tour'))} · Setlist Coming Soon!</span></a>''')
setlists_html=head('Concert Setlists & Tour Setlists | Concerto','Find concert tour setlists with their sources and update dates. Explore the songs and keep the tour connected to your night in Concerto.','/setlists')+f'''<main><section class="page-hero-v3"><div class="site-shell"><p class="eyebrow">Know every song</p><h1>Setlists, without the hunt.</h1><p>Find the songs for your artist’s tour. Check the source and update date, then start listening.</p><div class="hero-meta"><span class="meta-pill">{len(available_setlists)} published setlists</span><span class="meta-pill">{len(coming_setlists)} tours being tracked</span></div><div class="search-wrap"><input aria-label="Search setlists" data-filter-target=".setlist-item" placeholder="Search artist or tour"></div></div></section><section class="featured-strip"><div class="site-shell wide"><div class="rail-head"><div><h2>Start with these setlists.</h2><p>Explore the songs behind the show.</p></div></div><div class="featured-grid">{''.join(featured_tour(t,'Setlist available') for t in featured_set)}</div></div></section><section class="setlist-section"><div class="site-shell wide"><div class="catalog-intro"><h2>Available now.</h2><p>Each list includes an update date. Songs and order can vary by show.</p></div><div class="catalog-grid">{''.join(s_cards)}</div></div></section><section class="setlist-section alt"><div class="site-shell wide"><div class="catalog-intro"><h2>Tracking next.</h2><p>Tour guides awaiting a published setlist.</p></div><div class="coming-grid">{''.join(coming_cards)}</div></div></section></main>'''+end()
(ROOT/'setlists.html').write_text(setlists_html)

# Detail pages.
(ROOT/'venue').mkdir(exist_ok=True)
for v in venues:
    slug=v['id']; info=vi.get(slug,{})
    sections=[]
    order=[('bagPolicy','Bag Policy'),('parking','Parking'),('rideshare','Rideshare'),('gates','Entrances & Doors'),('accessibility','Accessibility'),('concessions','Concessions'),('reEntry','Re-Entry'),('ticketPickup','Ticket Pickup')]
    for key,label in order:
        card=venue_section_card(info,key,label)
        if card: sections.append(card)
    shown=shown_name(v)
    desc=f"{shown} concert guide with bag policy, parking, rideshare, concessions, accessibility, entrances, and other show-night information."
    ld={'@context':'https://schema.org','@type':'MusicVenue','name':v['name'],'address':{'@type':'PostalAddress','addressLocality':v.get('city') or '','addressRegion':v.get('state') or '','addressCountry':v.get('country') or ''},'url':SITE+'/venue/'+slug}
    ld['geo']={'@type':'GeoCoordinates','latitude':v.get('lat'),'longitude':v.get('lng')} if v.get('lat') else None
    ld={k:x for k,x in ld.items() if x is not None}
    extra=ld_json(ld)+breadcrumb_ld([('Venues','/venues'),(v['name'],f'/venue/{slug}')])
    fb=venue_fallback(v)
    page=head(f"{shown} Bag Policy, Parking & Venue Guide | Concerto",desc,f'/venue/{slug}',extra,banner=smart_banner('venue',slug))+f'''<main class="experience-product"><section class="stage-hero library-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/venues">Venues</a> &nbsp;/&nbsp; {esc(v['name'])}</div><p class="eyebrow">Venue guide</p><h1>{esc(v['name'])}</h1><p class="lead">{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}{' · '+esc(v.get('country')) if v.get('country') else ''}</p><div class="hero-actions">{app_link('venue',slug,'Save a show here in Concerto')}</div><div class="tonight" data-venue-tonight data-name="{esc(v['name'])}" data-country="{esc(v.get('country') or '')}" data-lat="{esc(v.get('lat'))}" data-lng="{esc(v.get('lng'))}"></div></div><div class="site-shell wide"><div class="detail-media library-media" data-vphoto data-vname="{esc(v['name'])}" data-vcity="{esc(v.get('city'))}" data-vlat="{esc(v.get('lat'))}" data-vlng="{esc(v.get('lng'))}"{fallback_attr(fb)}></div></div></section><section class="library-body"><div class="site-shell"><div class="section-lead"><p class="eyebrow">Know before you go</p><h2>What matters at {esc(v['name'])}.</h2><p>Each section shows its source and the date it was last checked. When something is not confirmed, it says so.</p></div><div class="card-grid">{''.join(sections)}</div></div></section>{related_list(related_venues(v),'venue')}<section class="last-call"><div class="site-shell"><h2>Going to a show here?</h2><div class="last-call-actions">{app_link('venue',slug,'Open in Concerto')}</div><p class="small-print">Your Night keeps these rules, the setlist, and the way home on one page.</p></div></section></main>'''+end()
    (ROOT/'venue'/f'{slug}.html').write_text(page)

(ROOT/'tour').mkdir(exist_ok=True); (ROOT/'setlist').mkdir(exist_ok=True)
# Remove stale generated setlist pages so only populated setlists are deployable/indexable.
for p in (ROOT/'setlist').glob('*.html'): p.unlink()
for t in tours:
    slug=t['tourId']; s=setlists.get(slug); songs=(s.get('songs') or []) if s else []
    if songs: desc=f"{t['artist']} {t['tourName']} tour guide with a current {len(songs)}-song setlist and links to plan the show in Concerto."
    elif s: desc=f"{t['artist']} {t['tourName']} tour guide on Concerto. Setlist coming soon, with venue and show-night context available now."
    else: desc=f"{t['artist']} {t['tourName']} tour guide with venue and show-night context on Concerto."
    ld={'@context':'https://schema.org','@type':'MusicGroup','@id':SITE+'/tour/'+slug+'#artist','name':t['artist'],'url':SITE+'/tour/'+slug}
    if t.get('tourWebsite'): ld['sameAs']=[t['tourWebsite']]
    extra=ld_json(ld)+breadcrumb_ld([('Tours','/tours'),(t['artist'],f'/tour/{slug}')])
    if songs:
        first=songs[:8]
        set_teaser=f'''<section class="detail-section"><p class="eyebrow">{'Confirmed setlist' if (s.get('source') or {}).get('eventDate') else 'Official tour playlist' if 'apple music' in (s.get('note') or '').lower() else 'Setlist'}</p><h2>{len(songs)} songs, ready.</h2><p class="provenance">{setlist_provenance(s)}. Setlists change by night.</p><ol class="song-list">{''.join('<li>'+esc(x)+'</li>' for x in first)}</ol><div class="link-row"><a class="btn-secondary" href="/setlist/{esc(slug)}">View full setlist →</a><a class="btn-secondary" href="https://music.apple.com/search?term={esc(t['artist'])}" target="_blank" rel="noopener">Apple Music</a><a class="btn-secondary" href="https://open.spotify.com/search/{esc(t['artist'])}" target="_blank" rel="noopener">Spotify</a></div></section>'''
    elif s:
        set_teaser=f'''<section class="detail-section"><p class="eyebrow">Setlist</p><h2>Setlist Coming Soon!</h2><p>Concerto is already tracking this tour. When there is a usable current setlist, the songs will appear here instead of an empty or guessed list.</p></section>'''
    else: set_teaser=''
    official=f'<a class="btn-secondary" href="{esc(t.get("tourWebsite"))}" target="_blank" rel="noopener">Official tour site ↗</a>' if t.get('tourWebsite') else ''
    setlist_card=setlist_card_for(slug,t['artist']) if songs else (f'''<figure class="night-card night-card-paper night-card-full"><div class="nc-head"><h3>Setlist Coming Soon!</h3><span class="nc-kicker">Tracking</span></div><p class="nc-body">Concerto is tracking this tour. Songs appear here when there is a usable current setlist, never a guessed one.</p></figure>''' if s else '')
    page=head(f"{t['artist']} {t['tourName']} Tour & Setlist | Concerto",desc,f'/tour/{slug}',extra,banner=smart_banner('tour',slug))+f'''<main class="experience-product"><section class="stage-hero library-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/tours">Tours</a> &nbsp;/&nbsp; {esc(t['artist'])}</div><p class="eyebrow">On tour</p><h1>{esc(t['artist'])}</h1><p class="lead">{esc(t['tourName'])}</p><div class="hero-actions">{app_link('tour',slug,'Open in Concerto')}{official}</div></div><div class="site-shell wide"><div class="detail-media library-media" data-artist="{esc(t['artist'])}"></div></div></section><section class="library-body"><div class="site-shell"><div class="card-grid card-grid-single">{setlist_card}</div></div></section>{related_list(related_tours(t),'tour')}<section class="last-call"><div class="site-shell"><h2>Going to this tour?</h2><div class="last-call-actions">{app_link('tour',slug,'Save your date in Concerto')}</div><p class="small-print">Your Night keeps the setlist, the venue rules, and the way home together.</p></div></section></main>'''+end()
    (ROOT/'tour'/f'{slug}.html').write_text(page)
    if songs:
        note=s.get('note') or ''
        desc2=f"{t['artist']} {t['tourName']} setlist: {len(songs)} songs, updated {s.get('updated','')}. View the current tour setlist on Concerto."
        ld2={'@context':'https://schema.org','@type':'ItemList','name':f"{t['artist']} {t['tourName']} setlist",'url':SITE+'/setlist/'+slug,'numberOfItems':len(songs),'about':{'@type':'MusicGroup','@id':SITE+'/tour/'+slug+'#artist','name':t['artist']},'itemListElement':[{'@type':'ListItem','position':i+1,'name':song} for i,song in enumerate(songs)]}
        extra2=ld_json(ld2)+breadcrumb_ld([('Setlists','/setlists'),(t['artist'],f'/tour/{slug}'),('Setlist',f'/setlist/{slug}')])
        sp=head(f"{t['artist']} {t['tourName']} Setlist | Concerto",desc2,f'/setlist/{slug}',extra2,banner=smart_banner('tour',slug))+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/setlists">Setlists</a> &nbsp;/&nbsp; <a href="/tour/{esc(slug)}">{esc(t['artist'])}</a></div><div class="detail-grid"><div><p class="eyebrow">Tour setlist</p><h1>{esc(t['artist'])}</h1><p class="subtitle">{esc(t['tourName'])} · {len(songs)} songs</p><div class="hero-meta"><span class="meta-pill">Updated {esc(s.get('updated'))}</span><span class="meta-pill">{esc(note) if note else 'Current tour reference'}</span></div></div><div class="detail-media" data-artist="{esc(t['artist'])}"></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main"><section class="detail-section"><p class="eyebrow">{'Confirmed setlist' if (s.get('source') or {}).get('eventDate') else 'Official tour playlist' if 'apple music' in (s.get('note') or '').lower() else 'Setlist'}</p><h2>{len(songs)} songs.</h2><p class="provenance">{setlist_provenance(s)}. Setlists change by night.</p><ol class="song-list">{''.join('<li>'+esc(x)+'</li>' for x in songs)}</ol></section><section class="detail-section"><div class="link-row">{app_link('tour',slug,'Save your show in Concerto')}<a class="btn-secondary" href="/tour/{esc(slug)}">Tour dates</a></div></section></div><aside><div class="side-card"><span class="tag">{esc(t['tourName'])}</span><h3>{esc(t['artist'])}</h3><p>{setlist_provenance(s)}.</p>{app_link('tour',slug,'Open in Concerto')}</div></aside></div></section></main>'''+end()
        (ROOT/'setlist'/f'{slug}.html').write_text(sp)

print(f'Built public site: home + {len(venues)} venues + {len(tours)} tours + {len(available_setlists)} populated setlists; tracking {len(coming_setlists)} coming soon')
