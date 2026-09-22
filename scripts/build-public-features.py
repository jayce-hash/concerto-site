#!/usr/bin/env python3
from pathlib import Path
import html, sys, re
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from public_chrome import header_html, page_end, HEAD_ASSETS, product_screen
SITE='https://concertocity.com'; APP='https://apps.apple.com/us/app/concerto-show-go/id6744903414'
def e(x): return html.escape(str(x),quote=True)
def head(title,desc,canonical): return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="apple-itunes-app" content="app-id=6744903414"><title>{e(title)}</title><meta name="description" content="{e(desc)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{SITE+canonical}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{SITE+canonical}"><meta property="og:image" content="{SITE}/ConcertoSocialPreview.png"><meta property="og:site_name" content="Concerto"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE}/ConcertoSocialPreview.png"><link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple-touch-icon.png">{HEAD_ASSETS}</head><body class="public-site">'''+header_html(canonical)
def end(): return page_end()
from experience_pages import capture, close
def feature_page(slug,eyebrow,title,desc,visual,sections,secondary='/venues'):
    keys={'bags':'venue-essentials','parking':'getting-there','bagcheck':'bag-check','rideshare':'getting-home'}
    actual=keys.get(visual,visual)
    import json
    manifest=json.loads((ROOT/'img/product/screens/manifest.json').read_text())
    plain_title=re.sub(r'<[^>]+>', ' ', title)
    picture=capture(actual,plain_title+' in Concerto') if actual in manifest else ''
    features=''.join(f'<div><span class="eyebrow">{num}</span><h3>{h}</h3><p>{p}</p>{("<a class=text-link href="+href+">"+link+" ↗</a>") if href else ""}</div>' for num,h,p,klass,href,link in sections)
    body=f'<section class="type-hero"><div class="site-shell"><p class="eyebrow">{eyebrow}</p><h1>{title}</h1><div class="hero-bottom"><p>{desc}</p><a class="btn-primary" href="{APP}">Get Concerto for iPhone ↗</a></div></div></section>'
    layout='product-story-grid' if picture else 'product-story-grid no-capture'
    body+=f'<section class="product-story"><div class="site-shell {layout}"><div class="feature-lines">{features}<a class="text-link" href="{secondary}">Explore the venue guides ↗</a></div>{picture}</div></section>'
    return head(f'{plain_title} | Concerto',desc,'/'+slug)+'<main class="experience-product">'+body+close()+'</main>'+end()

near=feature_page('near-me','Find your next night out','Something good.<br>Somewhere near you.','Discover concerts by location and date. Save the one you’re going to, then bring the rest of the night together.','near-me',[
('01 / DISCOVER','Find a show.','Explore what is happening around you. Choose a date and find a reason to go.','','/tours','Browse tours'),
('02 / SAVE','Give the night a home.','A saved concert opens Your Night, with the venue and available show details together.','','/your-night','Meet Your Night'),
('03 / GO','Make it your kind of night.','Explore nearby food, stays, and useful venue guidance in the app.','','/venues','Explore venues')])
(ROOT/'near-me.html').write_text(near)



from consumer_pages import your_night_page
(ROOT/'your-night.html').write_text(your_night_page(head))

pages={
'bagcheck':('Concerto+ · AI Bag Check','Check the bag before the door.','Use AI Bag Check to compare what you plan to bring against the published bag policy for your venue. It helps you prepare; the venue always makes the final entry decision.','bagcheck',[
('01 · Start','Pick the venue.','Bag Check begins with the same verified venue policy used throughout Concerto.','light','/venues','Browse venues'),('02 · Compare','Show Concerto the bag.','Use the app to compare your bag against the venue’s published limits and rules.','sand','', ''),('03 · Decide','Leave with context.','Concerto explains the match and the uncertainty instead of pretending it can guarantee entry.','','/premium','Meet Concerto+')]),
'bags':('Venue intelligence','Bag policies, without the hunt.','Concerto organizes published venue bag rules into clear, dated guides so you can find the answer before you leave.','bags',[
('01 · Verified','Official sources first.','Critical bag rules are researched from venue-published guidance whenever available.','light','/venues','Browse venues'),('02 · Dated','See when it was checked.','Verification dates make it clear when Concerto last confirmed critical information.','sand','',''),('03 · Connected','Attached to Your Night.','The policy stays with the show instead of becoming another screenshot or browser tab.','','/bagcheck','Try AI Bag Check')]),
'parking':('Venue intelligence','Parking that starts with the venue.','Find official parking guidance, named lots, and venue-specific notes inside Concerto venue guides.','parking',[
('01 · Official','Start with venue guidance.','Concerto prioritizes parking information published by the venue or its official partners.','light','/venues','Browse venues'),('02 · Practical','Know what is actually named.','Lots, garages, reservations, and arrival notes are surfaced when they are published.','sand','',''),('03 · Connected','Keep it with the show.','Parking lives alongside the rest of Your Night instead of in a separate planning thread.','','/near-me','Explore Near Me')]),
'rideshare':('Venue intelligence','Know where the ride should go.','Concerto surfaces official rideshare, pickup, and drop-off guidance when venues publish it, and says when a dedicated zone cannot be confirmed.','rideshare',[
('01 · Arrival','Get to the right place.','Use venue-specific pickup and drop-off notes instead of guessing from the pin alone.','light','/venues','Browse venues'),('02 · Honesty','No invented zones.','If a venue has not published a dedicated rideshare area, Concerto says so.','sand','',''),('03 · Getting home','Plan the exit too.','Rideshare context becomes part of the full night, including how you get home.','','/premium','Meet Concerto+')]),
'concessions':('Venue intelligence','Know what is inside.','Concerto organizes published food, drink, and concession information so the venue experience is easier to understand before you arrive.','concessions',[
('01 · Venue first','Published options.','Food, drink, cashless policies, and notable stands are included when the venue confirms them.','light','/venues','Browse venues'),('02 · Useful','Skip the generic filler.','Concerto focuses on information that can actually change your plan for the night.','sand','',''),('03 · Connected','Before and inside.','Concessions can sit beside nearby dining and Your Night context without mixing the two.','','/near-me','Explore nearby')])
}
for slug,(ey,title,desc,vis,secs) in pages.items(): (ROOT/f'{slug}.html').write_text(feature_page(slug,ey,title,desc,vis,secs))
print('built V6 public feature pages + Your Night')
