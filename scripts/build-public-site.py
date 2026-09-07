#!/usr/bin/env python3
import json, html, re, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from public_chrome import header_html, page_end, HEAD_ASSETS, product_screen, photo_slot
SITE='https://concertocity.com'
APP='https://apps.apple.com/us/app/concerto-show-go/id6744903414'

def esc(x): return html.escape(str(x or ''), quote=True)
def head(title,desc,canonical,extra='',robots='index,follow,max-image-preview:large'):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="apple-itunes-app" content="app-id=6744903414"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><meta name="robots" content="{esc(robots)}"><link rel="canonical" href="{esc(SITE+canonical)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{esc(SITE+canonical)}"><meta property="og:image" content="{SITE}/ConcertoSocialPreview.png"><meta property="og:site_name" content="Concerto"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE}/ConcertoSocialPreview.png"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png">{HEAD_ASSETS}{extra}</head><body class="public-site">'''+header_html(canonical)
def end(): return page_end()

tours=json.loads((ROOT/'data/tours.json').read_text())
venues=json.loads((ROOT/'data/venues.json').read_text())
vi=json.loads((ROOT/'data/venue_info.json').read_text())
setlists=json.loads((ROOT/'setlists.json').read_text())
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
def venue_media(v, cls='rail-media'):
    fb=venue_fallback(v)
    return f'<div class="{cls}" data-vphoto data-vname="{esc(v["name"])}" data-vcity="{esc(v.get("city"))}" data-vlat="{esc(v.get("lat"))}" data-vlng="{esc(v.get("lng"))}"{f" data-fallback-src=\"{esc(fb)}\"" if fb else ""}></div>'

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
    return f'''<a class="featured-card" href="/venue/{esc(v['id'])}"><div class="featured-media" data-vphoto data-vname="{esc(v['name'])}" data-vcity="{esc(v.get('city'))}" data-vlat="{esc(v.get('lat'))}" data-vlng="{esc(v.get('lng'))}"{f" data-fallback-src=\"{esc(fb)}\"" if fb else ""}></div><div class="featured-copy-overlay"><span class="tag">Verified venue guide</span><h3>{esc(v['name'])}</h3><p>{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}</p></div></a>'''

# Homepage — product/company story first; directories stay discoverable but do not dictate the design.
home_ld=ld_json({'@context':'https://schema.org','@graph':[{'@type':'Organization','@id':SITE+'/#org','name':'Concerto','url':SITE,'logo':SITE+'/img/app-icon.png','slogan':'From the Concert to the City','sameAs':['https://instagram.com/theconcertoapp','https://www.tiktok.com/@theconcertoapp','https://www.youtube.com/@theconcertoapp',APP]},{'@type':'WebSite','@id':SITE+'/#site','url':SITE,'name':'Concerto','publisher':{'@id':SITE+'/#org'},'potentialAction':{'@type':'SearchAction','target':SITE+'/search?q={search_term_string}','query-input':'required name=search_term_string'}},{'@type':'SoftwareApplication','name':'Concerto','operatingSystem':'iOS','applicationCategory':'EntertainmentApplication','url':APP,'offers':{'@type':'Offer','price':'0','priceCurrency':'USD'}}]})
home=head('Concerto | From the Concert to the City®','Concerto is the concert companion for the show, venue, and city around it. Find tours and setlists, know the venue, discover what is nearby, and plan your night.','/',home_ld)+f'''
<main>
<section class="hero-public"><div class="site-shell wide hero-grid"><div class="hero-copy"><p class="eyebrow">From the Concert to the City®</p><h1>The concert is only part of the night.</h1><p class="lead">Concerto connects the show, the venue, and the city around it, so the questions after you buy the ticket stop living across ten different apps and tabs.</p><div class="hero-actions"><a class="btn-primary" href="{APP}" target="_blank" rel="noopener">Get Concerto for iPhone →</a><a class="btn-secondary" href="/near-me">Explore what’s on</a></div><div class="hero-proof"><div class="proof"><strong>{len(venues)}</strong><span>venue guides</span></div><div class="proof"><strong>{len(tours)}</strong><span>tour guides</span></div><div class="proof"><strong>{len(available_setlists)}</strong><span>setlists available now</span></div></div></div><div class="device-stage single" aria-label="Concerto app preview"><div class="device"><div class="iphone-screen"><img src="{product_screen('home')}" width="1206" height="2622" alt="Concerto Home screen: next show countdown, setlist status, and nearby restaurants"></div></div><div class="device-badge"><strong>One show. One connected night.</strong><span>Setlist, venue rules, nearby places, weather, arrival, and getting home stay attached to the show you saved.</span></div></div></div></section>
<div class="logo-strip"><div class="site-shell logo-strip-inner"><span><b>Discover</b> the show</span><span><b>Know</b> the venue</span><span><b>Plan</b> the night</span><span><b>Go</b> with confidence</span></div></div>
<section class="story-section"><div class="site-shell"><div class="section-head"><p class="eyebrow">Built around the night</p><div><h2>Everything after the ticket, finally connected.</h2><p>Concerto is not another place to buy a ticket. It is the layer that helps you use the ticket: find the information that matters, understand the venue, and turn a saved show into an actual night.</p></div></div></div>
<div class="site-shell wide"><div class="product-row"><figure><div class="device"><div class="iphone-screen"><img src="{product_screen('near-me')}" width="1206" height="2622" alt="Concerto Near Me: live music by location and date" loading="lazy"></div></div><figcaption><span class="number">01 · Discover</span><h3>Find what is happening.</h3><p>Near Me, active tours, live setlists, and {len(venues)} venue guides, without starting from a blank search box.</p><a class="mini-link" href="/near-me">Explore Near Me</a></figcaption></figure><figure><div class="device"><div class="iphone-screen"><img src="{product_screen('venue')}" width="1206" height="2622" alt="Concerto venue guide with bag policy, parking, and AI Bag Check" loading="lazy"></div></div><figcaption><span class="number">02 · Know the venue</span><h3>Know before you go.</h3><p>Verified bag policy, parking, rideshare, concessions, entrances, and accessibility, researched from official sources and dated.</p><a class="mini-link" href="/venues">Browse venue guides</a></figcaption></figure><figure><div class="device"><div class="iphone-screen"><img src="{product_screen('your-night')}" width="1206" height="2622" alt="Your Night: the show-specific page for a saved concert" loading="lazy"></div></div><figcaption><span class="number">03 · Your Night</span><h3>One tap. Everything about that night.</h3><p>Home tells you where you are going next. Your Night brings the venue, weather, setlist, nearby places, Perks, and the way home together for that exact show.</p><a class="mini-link" href="/your-night">See Your Night</a></figcaption></figure></div></div></section>
{photo_slot('crowd','A concert crowd facing the stage under the lights')}
<section class="product-split"><div class="product-copy"><p class="eyebrow">Concerto+</p><h2>Your whole night, planned around you.</h2><p>Free Concerto gives you trusted facts. Concerto+ uses the show you saved, the venue, timing, weather, and nearby context to help you decide what to do with them.</p><div class="feature-list"><div class="feature-row"><div class="feature-icon">✓</div><div><b>Show-aware planning</b><span>A plan built around the concert you are actually attending.</span></div></div><div class="feature-row"><div class="feature-icon">⌁</div><div><b>AI Bag Check</b><span>Compare what you are bringing against the published venue policy before you leave.</span></div></div><div class="feature-row"><div class="feature-icon">↗</div><div><b>Context that travels</b><span>Venue facts, nearby places, timing, weather, and the trip home stay connected.</span></div></div></div><div class="hero-actions"><a class="btn-primary" style="background:#C9A84C;color:#121E36!important" href="/premium">Explore Concerto+</a><a class="btn-secondary" style="border-color:rgba(255,255,255,.18);color:#fff;background:transparent" href="{APP}">Get the App</a></div></div><div class="product-visual"><div class="device"><div class="iphone-screen"><img src="{product_screen('premium')}" width="1206" height="2622" alt="Concerto venue page with AI Bag Check and Plan Night" loading="lazy"></div></div></div></section>
<section class="featured-strip"><div class="site-shell wide"><div class="rail-head"><div><h2>What fans are checking now.</h2><p>Current setlists from tours people are planning around.</p></div><a href="/setlists">Explore setlists →</a></div><div class="featured-grid">{''.join(featured_tour(t,'Setlist available') for t in featured_set)}</div></div></section>
<section class="discovery"><div class="site-shell wide"><div class="rail-head"><div><h2>On the road now.</h2><p>Tour guides that connect dates, setlist status, venues, and the rest of the night.</p></div><a href="/tours">View all {len(tours)} tours →</a></div><div class="card-rail">{''.join(tour_card(t) for t in featured)}</div></div></section>
<section class="proof-band"><div class="site-shell"><div class="section-head"><p class="eyebrow">The Concerto standard</p><div><h2>Useful only if you can trust it.</h2><p>Critical venue information is researched from official sources and dated. If something has not been confirmed, Concerto should say so instead of filling the gap with a guess.</p></div></div><div class="traction-grid"><div class="traction"><strong>{len(venues)}</strong><span>structured venue guides</span></div><div class="traction"><strong>8</strong><span>core venue information sections in each verified guide</span></div><div class="traction"><strong>532K+</strong><span>social views in the last 90 days</span><small>Instagram account insights</small></div><div class="traction"><strong>153K</strong><span>Google Search impressions over 12 months</span><small>Google Search Console</small></div></div><div class="trust-note"><span>Verified facts stay free. Personalization and orchestration power Concerto+.</span><a class="text-link" href="/about">How Concerto works →</a></div></div></section>
<section class="discovery"><div class="site-shell wide"><div class="rail-head"><div><h2>Know the venue before you arrive.</h2><p>Bag policy, parking, rideshare, concessions, entrances, accessibility, and more.</p></div><a href="/venues">View all {len(venues)} venues →</a></div><div class="card-rail">{''.join(venue_card(v) for v in featured_v)}</div></div></section>
<section class="section partner-band"><div class="shell split"><div><p class="eyebrow">Concerto Partners</p><h2>Built with the places around the show.</h2></div><div><p class="lead">Restaurants, hotels, venues, and artists create real fan benefits, and Concerto places them inside Your Night at the moment they matter. Every Perk comes from a Concerto Partner, and every Partner is labeled.</p><div class="hero-actions"><a class="btn-secondary" href="/partners">Partner with Concerto</a><a class="btn-secondary" href="/perks">See Concerto Perks</a></div></div></div></section>
{photo_slot('city-night','A city street at night after a show')}
<section class="cta-band"><div class="site-shell"><p class="eyebrow">Your next show starts here</p><h2>Less searching. More night.</h2><p>Find the show, save it, know the venue, and let Concerto keep everything around the night connected.</p><div class="hero-actions" style="justify-content:center"><a class="btn-primary" href="{APP}">Get the App →</a><a class="btn-secondary" href="/near-me">See what’s near you</a></div></div></section>
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
            sections.append(f'''<article class="info-card"><div class="label">{esc(label)}</div><h3>{esc(x.get('title') or label)}</h3><p>{esc(body)}</p>{f'<span class="verified">Verified {esc(ver)}</span>' if ver else ''}{f'<div class="link-row">{link}</div>' if link else ''}</article>''')
    desc=f"{v['name']} concert guide with bag policy, parking, rideshare, concessions, accessibility, entrances, and other show-night information."
    ld={'@context':'https://schema.org','@type':'MusicVenue','name':v['name'],'address':{'@type':'PostalAddress','addressLocality':v.get('city') or '','addressRegion':v.get('state') or '','addressCountry':v.get('country') or ''},'url':SITE+'/venue/'+slug}
    ld['geo']={'@type':'GeoCoordinates','latitude':v.get('lat'),'longitude':v.get('lng')} if v.get('lat') else None
    ld={k:x for k,x in ld.items() if x is not None}
    extra=ld_json(ld)+breadcrumb_ld([('Venues','/venues'),(v['name'],f'/venue/{slug}')])
    fb=venue_fallback(v)
    page=head(f"{v['name']} Bag Policy, Parking & Venue Guide | Concerto",desc,f'/venue/{slug}',extra)+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/venues">Venues</a> &nbsp;/&nbsp; {esc(v['name'])}</div><div class="detail-grid"><div><p class="eyebrow">Venue guide</p><h1>{esc(v['name'])}</h1><p class="subtitle">{esc(v.get('city'))}{', '+esc(v.get('state')) if v.get('state') else ''}{' · '+esc(v.get('country')) if v.get('country') else ''}</p><div class="hero-meta"><span class="meta-pill">Verified venue information</span><span class="meta-pill">Official sources first</span></div></div><div class="detail-media" data-vphoto data-vname="{esc(v['name'])}" data-vcity="{esc(v.get('city'))}" data-vlat="{esc(v.get('lat'))}" data-vlng="{esc(v.get('lng'))}"{f' data-fallback-src="{esc(fb)}"' if fb else ''}></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main"><section class="detail-section"><p class="eyebrow">Know before you go</p><h2>What matters at {esc(v['name'])}.</h2><div class="info-grid">{''.join(sections)}</div></section>{related_list(related_venues(v),'venue')}<section class="detail-section"><p class="eyebrow">From the Concert to the City®</p><h2>The venue is only one part of the night.</h2><p>Save your show in Concerto to keep venue rules, nearby places, weather, timing, getting there, and getting home attached to the same night.</p><div class="link-row"><a class="btn-primary" href="{APP}">Open Concerto →</a><a class="btn-secondary" href="/near-me">Explore nearby</a></div></section></div><aside><div class="side-card"><span class="tag">Concerto venue guide</span><h3>Planning a show here?</h3><p>Use Concerto on iPhone for the full saved-show experience around {esc(v['name'])}.</p><a class="btn-primary" href="{APP}">Get the App</a><a class="btn-secondary" href="/venues">Browse more venues</a></div></aside></div></section></main>'''+end()
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
        set_teaser=f'''<section class="detail-section"><p class="eyebrow">Latest setlist</p><h2>{len(songs)} songs, ready.</h2><ol class="song-list">{''.join('<li>'+esc(x)+'</li>' for x in first)}</ol><div class="link-row"><a class="btn-secondary" href="/setlist/{esc(slug)}">View full setlist →</a></div></section>'''
    elif s:
        set_teaser=f'''<section class="detail-section"><p class="eyebrow">Setlist</p><h2>Setlist Coming Soon!</h2><p>Concerto is already tracking this tour. When there is a usable current setlist, the songs will appear here instead of an empty or guessed list.</p></section>'''
    else: set_teaser=''
    official=f'<a class="btn-secondary" href="{esc(t.get("tourWebsite"))}" target="_blank" rel="noopener">Official tour site ↗</a>' if t.get('tourWebsite') else ''
    page=head(f"{t['artist']} {t['tourName']} Tour & Setlist | Concerto",desc,f'/tour/{slug}',extra)+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/tours">Tours</a> &nbsp;/&nbsp; {esc(t['artist'])}</div><div class="detail-grid"><div><p class="eyebrow">On tour</p><h1>{esc(t['artist'])}</h1><p class="subtitle">{esc(t['tourName'])}</p><div class="link-row">{official}<a class="btn-primary" href="{APP}">Open in Concerto →</a></div></div><div class="detail-media" data-artist="{esc(t['artist'])}"></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main">{set_teaser}{related_list(related_tours(t),'tour')}<section class="detail-section"><p class="eyebrow">The whole night</p><h2>Tour guide meets show-night guide.</h2><p>Concerto connects the tour to the venue and city around it. Save a show to keep setlists, venue information, nearby places, weather, timing, arrival, and getting home together.</p></section></div><aside><div class="side-card"><span class="tag">Tour guide</span><h3>Going to this tour?</h3><p>Save the show in Concerto and turn a tour date into Your Night.</p><a class="btn-primary" href="{APP}">Get the App</a>{f'<a class="btn-secondary" href="/setlist/{esc(slug)}">View setlist</a>' if songs else ''}</div></aside></div></section></main>'''+end()
    (ROOT/'tour'/f'{slug}.html').write_text(page)
    if songs:
        note=s.get('note') or ''
        desc2=f"{t['artist']} {t['tourName']} setlist: {len(songs)} songs, updated {s.get('updated','')}. View the current tour setlist on Concerto."
        ld2={'@context':'https://schema.org','@type':'ItemList','name':f"{t['artist']} {t['tourName']} setlist",'url':SITE+'/setlist/'+slug,'numberOfItems':len(songs),'about':{'@type':'MusicGroup','@id':SITE+'/tour/'+slug+'#artist','name':t['artist']},'itemListElement':[{'@type':'ListItem','position':i+1,'name':song} for i,song in enumerate(songs)]}
        extra2=ld_json(ld2)+breadcrumb_ld([('Setlists','/setlists'),(t['artist'],f'/tour/{slug}'),('Setlist',f'/setlist/{slug}')])
        sp=head(f"{t['artist']} {t['tourName']} Setlist | Concerto",desc2,f'/setlist/{slug}',extra2)+f'''<main><section class="detail-hero"><div class="site-shell"><div class="breadcrumbs"><a href="/setlists">Setlists</a> &nbsp;/&nbsp; <a href="/tour/{esc(slug)}">{esc(t['artist'])}</a></div><div class="detail-grid"><div><p class="eyebrow">Tour setlist</p><h1>{esc(t['artist'])}</h1><p class="subtitle">{esc(t['tourName'])} · {len(songs)} songs</p><div class="hero-meta"><span class="meta-pill">Updated {esc(s.get('updated'))}</span><span class="meta-pill">{esc(note) if note else 'Current tour reference'}</span></div></div><div class="detail-media" data-artist="{esc(t['artist'])}"></div></div></div></section><section class="detail-content"><div class="site-shell detail-layout"><div class="detail-main"><section class="detail-section"><p class="eyebrow">Setlist</p><h2>What they’re playing.</h2><ol class="song-list">{''.join('<li>'+esc(x)+'</li>' for x in songs)}</ol></section><section class="detail-section"><p class="eyebrow">Go beyond the songs</p><h2>Plan the rest of the night.</h2><p>The setlist is one part of the show. Concerto connects it with the venue, nearby places, weather, arrival, and getting home.</p><div class="link-row"><a class="btn-primary" href="{APP}">Open Concerto →</a><a class="btn-secondary" href="/tour/{esc(slug)}">View tour guide</a></div></section></div><aside><div class="side-card"><span class="tag">Setlist</span><h3>{esc(t['tourName'])}</h3><p>Updated {esc(s.get('updated'))}. Setlists can change by date; use this as a current tour reference.</p><a class="btn-primary" href="{APP}">Save your show</a><a class="btn-secondary" href="/setlists">More setlists</a></div></aside></div></section></main>'''+end()
        (ROOT/'setlist'/f'{slug}.html').write_text(sp)

print(f'Built public site: home + {len(venues)} venues + {len(tours)} tours + {len(available_setlists)} populated setlists; tracking {len(coming_setlists)} coming soon')
