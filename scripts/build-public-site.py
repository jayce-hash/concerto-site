#!/usr/bin/env python3
import json, html, re, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from public_chrome import header_html, page_end, HEAD_ASSETS, product_screen, photo_slot, app_link, smart_banner, app_link_campaign
SITE='https://concertocity.com'
APP='https://apps.apple.com/us/app/concerto-show-go/id6744903414'

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
    webps=list(folder.glob('*.webp'))
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
        return f'<section class="detail-section"><p class="eyebrow">Nearby and related</p><h2>More venue guides.</h2><div class="coming-grid related-grid">{cards}</div></section>'
    cards=''.join(f'<a class="coming-card" href="/tour/{esc(x["tourId"])}"><strong>{esc(x["artist"])}</strong><span>{esc(x["tourName"])} · Setlist available</span></a>' for x in items)
    return f'<section class="detail-section"><p class="eyebrow">Also on the road</p><h2>More tours with setlists.</h2><div class="coming-grid related-grid">{cards}</div></section>'


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
home=head('Concerto | Live Music Near You This Week, and Everything Around the Show',f'Discover concerts near you, {len(venues)} verified venue guides, current tour and setlist information, and Your Night, the plan for everything around the show.','/',home_ld)+f'''<main>
<section class="live-hero"><div class="site-shell"><p class="eyebrow">From the Concert to the City®</p><h1>The concert is only part of the night.</h1><p class="lead">Shows near you, the venue rules that matter, the setlist they have been playing, and the plan for everything around it.</p></div>
<div class="site-shell wide live-near" data-live-near><div class="live-head"><div><h2>Near <span data-live-city>you</span> this week</h2><p data-live-sub>Live music by night, from the same source the app uses.</p></div><form class="live-city" data-live-form><input type="text" name="city" placeholder="Try another city" aria-label="City" autocomplete="off"><button type="submit">Search</button></form></div><div class="live-rail" data-live-rail><div class="live-skeleton"></div><div class="live-skeleton"></div><div class="live-skeleton"></div><div class="live-skeleton"></div></div><p class="live-foot"><a class="text-link" href="/near-me">How Near Me works in the app →</a></p></div></section>
<section class="pieces"><div class="site-shell"><div class="section-head"><p class="eyebrow">Built around the night</p><div><h2>Everything after the ticket, finally connected.</h2><p>Real pieces of the app, built from the same verified data it uses. Save a show and Home tells you where you are going next. One tap opens Your Night with all of it.</p></div></div></div>
<div class="site-shell wide piece-grid"><figure class="piece"><div class="piece-ui">{ui_next_show()}</div><figcaption><span class="number">01 · Home</span><h3>One tap from everything.</h3><p>Your next show, the countdown, and one action.</p><a class="mini-link" href="/your-night">See Your Night</a></figcaption></figure><figure class="piece"><div class="piece-ui">{ui_bag_policy('american-airlines-center')}</div><figcaption><span class="number">02 · Venue Essentials</span><h3>Know before you go.</h3><p>Bag policy, parking, rideshare, entrances, and concessions, dated and sourced. This is American Airlines Center, straight from the data.</p><a class="mini-link" href="/venue/american-airlines-center">Open the venue guide</a></figcaption></figure><figure class="piece"><div class="piece-ui">{ui_setlist('jonas-brothers-the-burning-up-tour-all-over-again')}</div><figcaption><span class="number">03 · Setlist</span><h3>Learn the songs first.</h3><p>The tour's official playlist or confirmed setlist, labeled by source, updated as the run goes on.</p><a class="mini-link" href="/setlists">Browse setlists</a></figcaption></figure><figure class="piece"><div class="piece-ui">{ui_getting_out('american-airlines-center')}</div><figcaption><span class="number">04 · Getting Home</span><h3>The encore is not the end.</h3><p>Official rideshare guidance and pickup zones when the venue publishes them, ready before the lights go up.</p><a class="mini-link" href="/rideshare">Rideshare guides</a></figcaption></figure></div></section>
<section class="product-split"><div class="product-copy"><p class="eyebrow">Concerto+</p><h2>Your whole night, planned around you.</h2><p>Free Concerto gives you the facts. Concerto+ turns your saved show, venue, weather, and nearby places into one plan for the night.</p><div class="feature-list"><div class="feature-row"><div class="feature-icon">✓</div><div><b>Plan My Night</b><span>Dinner, when to leave, arrival, parking, and the ride home, built around this exact show.</span></div></div><div class="feature-row"><div class="feature-icon">✓</div><div><b>AI Bag Check</b><span>Photograph your bag and get a verdict against the venue's published policy.</span></div></div><div class="feature-row"><div class="feature-icon">✓</div><div><b>Show-day alerts</b><span>Forecast at 9am, Before You Go at 5pm, ride-home links at 9pm, recap the next morning.</span></div></div></div><div class="hero-actions"><a class="btn-primary" href="/premium">See Concerto+</a><a class="btn-secondary" style="background:transparent;color:#fff;border-color:rgba(255,255,255,.3)" href="{app_link_campaign('website-home')}">Get the App</a></div></div><div class="product-visual"><div class="yn-card"><div class="yn-head"><span class="ap-kicker">YOUR NIGHT</span><b>Jonas Brothers · American Airlines Center</b><span>Tuesday · Doors 7:30 PM</span></div><div class="yn-row"><span class="yn-time">5:45 PM</span><div><b>Dinner</b><span>Pax &amp; Beneficia, 6 min walk</span></div></div><div class="yn-row"><span class="yn-time">7:10 PM</span><div><b>Leave for the venue</b><span>Gate lines are already built in</span></div></div><div class="yn-row"><span class="yn-time">7:30 PM</span><div><b>Doors</b><span>Bag policy checked. Small clear bag only</span></div></div><div class="yn-row"><span class="yn-time">11:15 PM</span><div><b>Getting home</b><span>Use signed rideshare pickup areas</span></div></div><div class="yn-foot">Example plan. Built from verified venue data and your saved show.</div></div></div></section>
'''
home=home+f'''
<section class="featured-strip"><div class="site-shell wide"><div class="rail-head"><div><h2>What fans are checking now.</h2><p>Current setlists from tours people are planning around.</p></div><a href="/setlists">Explore setlists →</a></div><div class="featured-grid">{''.join(featured_tour(t,'Setlist available') for t in featured_set)}</div></div></section>
<section class="discovery"><div class="site-shell wide"><div class="rail-head"><div><h2>On the road now.</h2><p>Tour guides that connect dates, setlist status, venues, and the rest of the night.</p></div><a href="/tours">View all {len(tours)} tours →</a></div><div class="card-rail">{''.join(tour_card(t) for t in featured)}</div></div></section>
<section class="proof-band"><div class="site-shell"><div class="section-head"><p class="eyebrow">The Concerto standard</p><div><h2>Useful only if you can trust it.</h2><p>Critical venue information is researched from official sources and dated. If something has not been confirmed, Concerto should say so instead of filling the gap with a guess.</p></div></div><div class="traction-grid"><div class="traction"><strong>{len(venues)}</strong><span>structured venue guides</span></div><div class="traction"><strong>8</strong><span>core venue information sections in each verified guide</span></div><div class="traction"><strong>532K+</strong><span>social views in the 90 days to Sep 2026</span><small>Instagram account insights</small></div><div class="traction"><strong>153K</strong><span>Google Search impressions in the 12 months to Sep 2026</span><small>Google Search Console</small></div></div><div class="trust-note"><span>Verified facts stay free. Personalization and orchestration power Concerto+.</span><a class="text-link" href="/about">How Concerto works →</a></div></div></section>
<section class="discovery"><div class="site-shell wide"><div class="rail-head"><div><h2>Know the venue before you arrive.</h2><p>Bag policy, parking, rideshare, concessions, entrances, accessibility, and more.</p></div><a href="/venues">View all {len(venues)} venues →</a></div><div class="card-rail">{''.join(venue_card(v) for v in featured_v)}</div></div></section>
<section class="section partner-band"><div class="shell split"><div><p class="eyebrow">Concerto Partners</p><h2>Built with the places around the show.</h2></div><div><p class="lead">Restaurants, hotels, venues, and artists can work with Concerto to reach fans who already have a ticket, inside the plan for the night.</p><div class="hero-actions"><a class="btn-secondary" href="/partners">Partner with Concerto</a></div></div></div></section>
{photo_slot('city-night','A city street at night after a show')}
<section class="cta-band"><div class="site-shell"><p class="eyebrow">Your next show starts here</p><h2>Less searching. More night.</h2><p>Find the show, save it, know the venue, and let Concerto keep everything around the night connected.</p><div class="hero-actions" style="justify-content:center"><a class="btn-primary" href="{app_link_campaign('website-home')}">Get the App →</a><a class="btn-secondary" href="/near-me">See what’s near you</a></div></div></section>
</main>'''+end()
(ROOT/'index.html').write_text(home)

# Venues hub — editorial context before the full database.
v_cards=[]
for v in sorted(venues,key=lambda x:(x.get('name') or '').lower()):
    v_cards.append(f'''<a class="catalog-card filter-item venue-item" href="/venue/{esc(v['id'])}">{venue_media(v,'thumb')}<div class="body"><span class="micro status-live">Verified venue guide</span><h2>{esc(v['name'])}</h2><p>{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}{' · '+esc(v.get('country')) if v.get('country') else ''}</p></div></a>''')
venue_featured=featured_v[:3]
venues_html=head('Concert Venue Guides, Bag Policies, Parking & More | Concerto','Explore verified concert venue guides with bag policies, parking, rideshare, concessions, accessibility, entrances, and other show-night information.','/venues')+f'''<main><section class="page-hero-v3"><div class="site-shell"><p class="eyebrow">Every venue. Every rule.</p><h1>Know before you go.</h1><p>Verified venue information for arenas, stadiums, theaters, amphitheaters, and festivals, researched from official sources and organized around the questions that actually change show night.</p><div class="hero-meta"><span class="meta-pill">{len(venues)} venue guides</span><span class="meta-pill">Official-source verification</span><span class="meta-pill">Bag policy · Parking · Rideshare · More</span></div><div class="search-wrap"><input aria-label="Search venues" data-filter-target=".venue-item" placeholder="Search venue, city, or state"></div></div></section><section class="featured-strip"><div class="site-shell wide"><div class="rail-head"><div><h2>Start with the venue.</h2><p>Popular guides with real show-night information, not generic location pages. The same guides power the Venues tab in the app.</p></div><a href="{APP}" target="_blank" rel="noopener">Open in the app</a></div><div class="featured-grid">{''.join(featured_venue(v) for v in venue_featured)}</div></div></section><section class="catalog-section"><div class="site-shell wide"><div class="catalog-intro"><h2>All venue guides.</h2><p>Every guide uses the same structured source of truth as the iPhone app. Search above, or browse the complete library.</p></div><div class="catalog-grid">{''.join(v_cards)}</div></div></section></main>'''+end()
(ROOT/'venues.html').write_text(venues_html)

# Tours hub.
t_cards=[]
for t in sorted(tours,key=lambda x:(x.get('artist') or '').lower()):
    status,status_cls=tour_status(t)
    t_cards.append(f'''<a class="catalog-card filter-item tour-item" href="/tour/{esc(t['tourId'])}">{artist_media(t,'thumb')}<div class="body"><span class="micro {status_cls}">{esc(status)}</span><h2>{esc(t['artist'])}</h2><p>{esc(t['tourName'])}</p></div></a>''')
tours_html=head('Concert Tours & Tour Setlists | Concerto','Browse current concert tours, tour guides, setlist status, and venue context on Concerto.','/tours')+f'''<main><section class="page-hero-v3"><div class="site-shell"><p class="eyebrow">On the road now</p><h1>Follow the tour.</h1><p>Browse active tour guides and move directly into current setlists, venue context, and the show-night experience in Concerto.</p><div class="hero-meta"><span class="meta-pill">{len(tours)} tour guides</span><span class="meta-pill">{len(available_setlists)} setlists available now</span></div><div class="search-wrap"><input aria-label="Search tours" data-filter-target=".tour-item" placeholder="Search artist or tour"></div></div></section><section class="featured-strip"><div class="site-shell wide"><div class="rail-head"><div><h2>Featured tours.</h2><p>Current artists with active Concerto tour guides.</p></div><a href="/setlists">See current setlists →</a></div><div class="featured-grid">{''.join(featured_tour(t) for t in featured[:3])}</div></div></section><section class="catalog-section"><div class="site-shell wide"><div class="catalog-intro"><h2>All tour guides.</h2><p>A tour can be tracked before its setlist is available. Concerto says “coming soon” instead of pretending an empty setlist is ready.</p></div><div class="catalog-grid">{''.join(t_cards)}</div></div></section></main>'''+end()
(ROOT/'tours.html').write_text(tours_html)

# Setlists hub — only populated setlists are marketed as setlists; coming-soon records remain tour trackers.
s_cards=[]
for tid,s in sorted(available_setlists.items(),key=lambda kv:(kv[1].get('artist') or '').lower()):
    songs=s.get('songs') or []
    s_cards.append(f'''<a class="catalog-card filter-item setlist-item" href="/setlist/{esc(tid)}"><div class="thumb" data-artist="{esc(s.get('artist'))}"></div><div class="body"><span class="micro status-live">{len(songs)} songs · updated {esc(s.get('updated'))}</span><h2>{esc(s.get('artist'))}</h2><p>{esc(s.get('tour'))}</p></div></a>''')
coming_cards=[]
for tid,s in sorted(coming_setlists.items(),key=lambda kv:(kv[1].get('artist') or '').lower()):
    coming_cards.append(f'''<a class="coming-card filter-item setlist-item" href="/tour/{esc(tid)}"><strong>{esc(s.get('artist'))}</strong><span>{esc(s.get('tour'))} · Setlist Coming Soon!</span></a>''')
setlists_html=head('Concert Setlists & Tour Setlists | Concerto','Find current concert setlists and tour setlists for artists on the road now. Concerto connects each populated setlist to the tour, venue, and show-night experience.','/setlists')+f'''<main><section class="page-hero-v3"><div class="site-shell"><p class="eyebrow">Know every song</p><h1>Setlists, without the hunt.</h1><p>Current tour setlists organized around the artist and tour you care about, with the rest of the night one tap away in Concerto.</p><div class="hero-meta"><span class="meta-pill">{len(available_setlists)} setlists available now</span><span class="meta-pill">{len(coming_setlists)} tours being tracked</span></div><div class="search-wrap"><input aria-label="Search setlists" data-filter-target=".setlist-item" placeholder="Search artist or tour"></div></div></section><section class="featured-strip"><div class="site-shell wide"><div class="rail-head"><div><h2>What fans are checking now.</h2><p>Current setlists with real songs in the library today.</p></div></div><div class="featured-grid">{''.join(featured_tour(t,'Setlist available') for t in featured_set)}</div></div></section><section class="setlist-section"><div class="site-shell wide"><div class="catalog-intro"><h2>Available now.</h2><p>These pages contain the current song list and update date. Setlists can change by show, so Concerto treats them as a current tour reference rather than a guarantee.</p></div><div class="catalog-grid">{''.join(s_cards)}</div></div></section><section class="setlist-section alt"><div class="site-shell wide"><div class="catalog-intro"><h2>Tracking next.</h2><p>These tours are already in Concerto, but a usable setlist is not available yet. Their tour guide stays live and the setlist will appear when there is something real to show.</p></div><div class="coming-grid">{''.join(coming_cards)}</div></div></section></main>'''+end()
(ROOT/'setlists.html').write_text(setlists_html)

# Detail pages.
(ROOT/'venue').mkdir(exist_ok=True)
for v in venues:
    slug=v['id']; info=vi.get(slug,{})
    sections=[]
    order=[('bagPolicy','Bag Policy'),('parking','Parking'),('rideshare','Rideshare'),('concessions','Concessions'),('accessibility','Accessibility'),('reEntry','Re-Entry'),('ticketPickup','Ticket Pickup'),('gates','Entrances & Gates')]
    for key,label in order:
        x=info.get(key) or {}; body=x.get('summary') or x.get('note') or x.get('body') or ''
        if body:
            ver=x.get('verified') or ''; official=x.get('officialLink') or ''
            link=f'<a class="text-link" href="{esc(official)}" target="_blank" rel="noopener">Official source →</a>' if official else ''
            sections.append(f'''<article class="info-card" data-section="{esc(key)}"><div class="label">{esc(label)}</div><h3>{esc(x.get('title') or label)}</h3><p>{esc(body)}</p>{f'<span class="verified">Verified {esc(ver)}</span>' if ver else ''}{f'<div class="link-row">{link}</div>' if link else ''}</article>''')
    desc=f"{v['name']} concert guide with bag policy, parking, rideshare, concessions, accessibility, entrances, and other show-night information."
    ld={'@context':'https://schema.org','@type':'MusicVenue','name':v['name'],'address':{'@type':'PostalAddress','addressLocality':v.get('city') or '','addressRegion':v.get('state') or '','addressCountry':v.get('country') or ''},'url':SITE+'/venue/'+slug}
    ld['geo']={'@type':'GeoCoordinates','latitude':v.get('lat'),'longitude':v.get('lng')} if v.get('lat') else None
    ld={k:x for k,x in ld.items() if x is not None}
    extra=ld_json(ld)+breadcrumb_ld([('Venues','/venues'),(v['name'],f'/venue/{slug}')])
    fb=venue_fallback(v)
    page=head(f"{v['name']} Bag Policy, Parking & Venue Guide | Concerto",desc,f'/venue/{slug}',extra,banner=smart_banner('venue',slug))+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/venues">Venues</a> &nbsp;/&nbsp; {esc(v['name'])}</div><div class="detail-grid"><div><p class="eyebrow">Venue guide</p><h1>{esc(v['name'])}</h1><p class="subtitle">{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}{' · '+esc(v.get('country')) if v.get('country') else ''}</p><div class="hero-meta"><span class="meta-pill">Verified venue information</span><span class="meta-pill">Official sources first</span></div><div class="tonight" data-venue-tonight data-name="{esc(v['name'])}" data-country="{esc(v.get('country') or '')}" data-lat="{esc(v.get('lat'))}" data-lng="{esc(v.get('lng'))}"></div></div><div class="detail-media" data-vphoto data-vname="{esc(v['name'])}" data-vcity="{esc(v.get('city'))}" data-vlat="{esc(v.get('lat'))}" data-vlng="{esc(v.get('lng'))}"{fallback_attr(fb)}></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main"><section class="detail-section"><p class="eyebrow">Know before you go</p><h2>What matters at {esc(v['name'])}.</h2><p>The information that can ruin a night if it is wrong. Every section shows its source and the date Concerto last checked it.</p><div class="info-grid">{''.join(sections)}</div></section>{related_list(related_venues(v),'venue')}<section class="detail-section"><p class="eyebrow">From the Concert to the City®</p><h2>The venue is only one part of the night.</h2><p>Save your show in Concerto to keep venue rules, nearby places, weather, timing, getting there, and getting home attached to the same night.</p><div class="link-row">{app_link('venue',slug,'Open in Concerto')}<a class="btn-secondary" href="/near-me">Explore nearby</a></div></section></div><aside><div class="side-card"><span class="tag">Concerto venue guide</span><h3>Planning a show here?</h3><p>Open this venue in Concerto to save a show here and get the full night around it.</p>{app_link('venue',slug,'Open in Concerto')}<a class="btn-secondary" href="/venues">Browse more venues</a></div></aside></div></section></main>'''+end()
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
    page=head(f"{t['artist']} {t['tourName']} Tour & Setlist | Concerto",desc,f'/tour/{slug}',extra,banner=smart_banner('tour',slug))+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/tours">Tours</a> &nbsp;/&nbsp; {esc(t['artist'])}</div><div class="detail-grid"><div><p class="eyebrow">On tour</p><h1>{esc(t['artist'])}</h1><p class="subtitle">{esc(t['tourName'])}</p><div class="link-row">{official}{app_link('tour',slug,'Open in Concerto')}</div></div><div class="detail-media" data-artist="{esc(t['artist'])}"></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main">{set_teaser}{related_list(related_tours(t),'tour')}<section class="detail-section"><p class="eyebrow">The whole night</p><h2>Tour guide meets show-night guide.</h2><p>Concerto connects the tour to the venue and city around it. Save a show to keep setlists, venue information, nearby places, weather, timing, arrival, and getting home together.</p></section></div><aside><div class="side-card"><span class="tag">Tour guide</span><h3>Going to this tour?</h3><p>Save the show in Concerto and turn a tour date into Your Night.</p>{app_link('tour',slug,'Open in Concerto')}{f'<a class="btn-secondary" href="/setlist/{esc(slug)}">View setlist</a>' if songs else ''}</div></aside></div></section></main>'''+end()
    (ROOT/'tour'/f'{slug}.html').write_text(page)
    if songs:
        note=s.get('note') or ''
        desc2=f"{t['artist']} {t['tourName']} setlist: {len(songs)} songs, updated {s.get('updated','')}. View the current tour setlist on Concerto."
        ld2={'@context':'https://schema.org','@type':'ItemList','name':f"{t['artist']} {t['tourName']} setlist",'url':SITE+'/setlist/'+slug,'numberOfItems':len(songs),'about':{'@type':'MusicGroup','@id':SITE+'/tour/'+slug+'#artist','name':t['artist']},'itemListElement':[{'@type':'ListItem','position':i+1,'name':song} for i,song in enumerate(songs)]}
        extra2=ld_json(ld2)+breadcrumb_ld([('Setlists','/setlists'),(t['artist'],f'/tour/{slug}'),('Setlist',f'/setlist/{slug}')])
        sp=head(f"{t['artist']} {t['tourName']} Setlist | Concerto",desc2,f'/setlist/{slug}',extra2,banner=smart_banner('tour',slug))+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/setlists">Setlists</a> &nbsp;/&nbsp; <a href="/tour/{esc(slug)}">{esc(t['artist'])}</a></div><div class="detail-grid"><div><p class="eyebrow">Tour setlist</p><h1>{esc(t['artist'])}</h1><p class="subtitle">{esc(t['tourName'])} · {len(songs)} songs</p><div class="hero-meta"><span class="meta-pill">Updated {esc(s.get('updated'))}</span><span class="meta-pill">{esc(note) if note else 'Current tour reference'}</span></div></div><div class="detail-media" data-artist="{esc(t['artist'])}"></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main"><section class="detail-section"><p class="eyebrow">Setlist</p><h2>What they’re playing.</h2><ol class="song-list">{''.join('<li>'+esc(x)+'</li>' for x in songs)}</ol></section><section class="detail-section"><p class="eyebrow">Go beyond the songs</p><h2>Plan the rest of the night.</h2><p>The setlist is one part of the show. Concerto connects it with the venue, nearby places, weather, arrival, and getting home.</p><div class="link-row">{app_link('tour',slug,'Open in Concerto')}<a class="btn-secondary" href="/tour/{esc(slug)}">View tour guide</a></div></section></div><aside><div class="side-card"><span class="tag">Setlist</span><h3>{esc(t['tourName'])}</h3><p>Updated {esc(s.get('updated'))}. Setlists can change by date; use this as a current tour reference.</p>{app_link('tour',slug,'Save your show')}<a class="btn-secondary" href="/setlists">More setlists</a></div></aside></div></section></main>'''+end()
        (ROOT/'setlist'/f'{slug}.html').write_text(sp)

print(f'Built public site: home + {len(venues)} venues + {len(tours)} tours + {len(available_setlists)} populated setlists; tracking {len(coming_setlists)} coming soon')
