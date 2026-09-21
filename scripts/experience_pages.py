"""The public experience: a concert-night story, with real, unframed app captures."""
import html
import json
from pathlib import Path
from public_chrome import APP, page_end, app_link_campaign
from night_components import component, EXAMPLE

ROOT = Path(__file__).resolve().parent.parent
def e(value): return html.escape(str(value), quote=True)

def capture(key, alt, fallback='your-night'):
    # Feature pages still call this; it now returns the data component for the key.
    return component(key)

def _cta(ct, label='Get Concerto for iPhone'):
    return f'<a class="btn-primary" href="{app_link_campaign(ct)}">{label}</a>'

def _rail(keys, label):
    cards=''.join(component(k) for k in keys)
    return f'<div class="moment-rail" role="region" aria-label="{e(label)}" tabindex="0">{cards}</div>'

def _pillars(items):
    return '<div class="pillars">'+''.join(f'<div><span class="pillar-verb">{e(v)}</span><p>{e(t)}</p></div>' for v,t in items)+'</div>'

def _grid(items):
    return '<div class="feature-grid">'+''.join(f'<div><h3>{e(h)}</h3><p>{e(t)}</p></div>' for h,t in items)+'</div>'

def _proof(items):
    return '<div class="proof">'+''.join(f'<div><b>{e(h)}</b><p>{e(t)}</p></div>' for h,t in items)+'</div>'

def close(title='Your next show starts here.', ct='website-footer'):
    return f'<section class="last-call"><div class="site-shell"><h2>{title}</h2><div class="last-call-actions">{_cta(ct)}<img class="qr" src="/img/appstore-qr.png" width="96" height="96" alt="QR code for Concerto on the App Store" loading="lazy"></div><p class="small-print">Free to download. Concerto+ available in the app.</p></div></section>'

def home_page(head, schema):
    hero=f'''<section class="stage-hero"><div class="site-shell"><h1>Everything after the ticket,<br>in one place.</h1><p class="lead">Save your show. Concerto keeps the venue rules, setlist, timing, places nearby, and the way home together.</p>{_cta('website-home')}</div><div class="site-shell wide">{_rail(['home','venue','setlist'], 'A saved show, its venue rules, and its setlist')}</div></section>'''
    statement='''<section class="statement"><div class="site-shell"><p>Concerto is the concert-night companion. Save the show, and the night organizes itself.</p></div></section>'''
    pillars='<section class="pillars-section"><div class="site-shell">'+_pillars([('Save','Find your show, or let your calendar suggest it.'),('Know','Bag policy, entry, parking, and rideshare, from official sources, dated.'),('Plan','Setlist, timing, dinner, and the way home on one page.')])+'</div></section>'
    how='''<section class="how-para"><div class="site-shell"><p>Concerto works by attaching everything about a night to the show you saved: the venue’s verified rules, the tour’s setlist, the timing, the places nearby, and the route home. It is organized before you ask, so the night stays yours instead of your phone’s.</p></div></section>'''
    night=f'''<section class="moments"><div class="site-shell"><h2>A page for every show you go to.</h2></div><div class="site-shell wide">{_rail(['your-night','venue-essentials','setlist','getting-home','night-plan'], 'Your Night, from the countdown to the way home')}</div></section>'''
    plus=f'''<section class="plus-moment"><div class="site-shell plus-grid"><div><p class="eyebrow">Concerto+</p><h2>Make a plan of it.</h2><p>Dinner, arrival, and the way home, shaped around your show and your taste. Plan My Night and AI Bag Check, with the essentials always free.</p><a class="text-link" href="/premium">Explore Concerto+ <span aria-hidden="true">↗</span></a></div>{component('night-plan')}</div></section>'''
    grid='<section class="features"><div class="site-shell"><p class="section-intro">Concerto turns a ticket into a night you can see. These are the pieces.</p>'+_grid([('Your Night','One page per saved show: countdown, essentials, setlist, nearby, and the way home.'),('Venue Essentials','Bag policy, entry, parking, rideshare, and accessibility for 346 venues, with the source and date on every section.'),('Setlists','What the tour is playing, labeled by source, so you can learn it before doors.'),('Getting Home','The venue’s published pickup guidance and ride links, kept with the show.'),('AI Bag Check','Compare your bag with the venue’s policy before you leave the house.'),('Show-day alerts','Quiet reminders on the day, in venue time, only for shows you saved.')])+'</div></section>'
    proof='<section class="proof-section"><div class="site-shell"><h2>Built for fans who show up.</h2>'+_proof([('346 venue guides','Researched from official sources, each section dated.'),('Honest by default','When something is not confirmed, Concerto says so instead of guessing.'),('Free where it matters','Bag policy, entry, parking, and accessibility never sit behind Concerto+.')])+'</div></section>'
    return head('Concerto | Everything After the Ticket, in One Place','Save your show. Concerto keeps the venue rules, setlist, timing, places nearby, and the plan for getting there and home together.','/',schema)+'<main class="experience-home">'+hero+statement+pillars+night+plus+grid+proof+close()+'</main>'+page_end()

def your_night_page(head):
    hero=f'''<section class="stage-hero"><div class="site-shell"><p class="eyebrow">Your Night · Free in Concerto</p><h1>The show is yours.<br>So is the night.</h1><p class="lead">Save a concert and the whole evening gets a home: the venue, the music, the places nearby, and the way back.</p>{_cta('website-your-night','Save your next show')}</div><div class="site-shell wide">{_rail(['your-night','venue-essentials','setlist','getting-home'], 'Your Night, section by section')}</div></section>'''
    pillars='<section class="pillars-section"><div class="site-shell">'+_pillars([('Weeks out','Learn the songs and the rules. Book dinner.'),('Show day','The forecast, when to leave, and where to enter.'),('After','The way home, and the setlist you heard.')])+'</div></section>'
    free='<section class="proof-section"><div class="site-shell"><h2>Free, and honest about what it knows.</h2>'+_proof([('Always free','Saving shows, venue essentials, setlists, and directions.'),('Dated and sourced','Every venue section shows where it came from and when it was checked.'),('Concerto+','Plan My Night, AI Bag Check, and richer alerts, when you want them.')])+'</div></section>'
    return head('Your Night | Every Part of Your Show | Concerto','Save a concert and keep venue rules, available setlists, nearby places, and the way home together.','/your-night')+'<main class="experience-product">'+hero+pillars+free+close('Save your next show.','website-your-night')+'</main>'+page_end()

def premium_page(head):
    schema='<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@type':'Product','name':'Concerto+','description':'Personalized concert-night planning inside Concerto.','brand':{'@type':'Brand','name':'Concerto'},'offers':[{'@type':'Offer','price':'7.99','priceCurrency':'USD','url':'https://concertocity.com/premium','name':'Monthly'},{'@type':'Offer','price':'69.99','priceCurrency':'USD','url':'https://concertocity.com/premium','name':'Yearly'}]})+'</script>'
    hero=f'''<section class="stage-hero plus-hero"><div class="site-shell"><p class="eyebrow">Concerto+</p><h1>Good plans.<br>Great nights.</h1><p class="lead">A plan around your show and your preferences. A little less to figure out before you leave.</p>{_cta('website-premium','Start with the app')}</div><div class="site-shell wide">{_rail(['night-plan','bagcheck'], 'Plan My Night and AI Bag Check')}</div></section>'''
    grid='<section class="features"><div class="site-shell">'+_grid([('Plan My Night','A timeline for the evening from your saved show: dinner, arrival, the encore, and home.'),('AI Bag Check','Your bag against the venue’s published policy, with the rule it used.'),('Show-day alerts','Forecast in the morning, leave-by in the afternoon, the way home after the encore.')])+'</div></section>'
    pricing=f'''<section class="pricing"><div class="site-shell"><h2>Meet your +.</h2><p class="lead">The essentials stay free. Add Concerto+ when you want a personal plan.</p><div class="price-row"><div><b>$7.99</b><span>per month</span></div><div><b>$69.99</b><span>per year</span></div></div>{_cta('website-premium','Start your 7-day trial in the app')}<p class="small-print">Cancel anytime in your Apple ID settings.</p></div></section>'''
    return head('Concerto+ | Your Whole Night, Planned Around You','Personalized concert-night planning, AI Bag Check, and show-day alerts with Concerto+.','/premium',schema)+'<main class="experience-product">'+hero+grid+pricing+'</main>'+page_end()
