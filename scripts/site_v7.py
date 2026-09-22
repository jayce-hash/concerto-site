"""Concerto consumer site, V7. A product experience built on the library.

Home, Your Night, and Concerto+ are composed here. Everything the visitor sees is
either real data (venues, setlists, tours), a live lookup (tonight near you), or an
interaction that demonstrates the product (type a venue, read its bag policy).
Library pages keep their URLs, canonicals, and structured data untouched.
"""
import html, json
from pathlib import Path
from public_chrome import page_end, app_link_campaign
from night_components import component, EXAMPLE, _SL, _VN, _TR

ROOT = Path(__file__).resolve().parent.parent
def e(v): return html.escape(str(v or ''), quote=True)
LIVE = sum(1 for s in _SL.values() if s.get('songs'))
V7_JS = '<script src="/js/public-v7.js" defer></script>'

def cta(ct, label='Get Concerto for iPhone', cls='btn-gold'):
    return f'<a class="{cls}" href="{app_link_campaign(ct)}">{label}</a>'

def hero_home():
    x = EXAMPLE
    return f'''<section class="v7-hero"><div class="v7-shell v7-hero-grid"><div class="v7-hero-copy reveal"><p class="v7-eyebrow">Concerto · The concert-night companion</p><h1>Everything after<br>the ticket.</h1><p class="v7-lead">Save your show. The venue rules, the setlist, the timing, the places nearby, and the way home, on one page that changes as the night gets closer.</p><div class="v7-actions">{cta('website-home')}<a class="btn-ghost" href="#try">Try it with your venue ↓</a></div></div><div class="v7-ticket reveal" data-live-ticket><span class="v7-ticket-kicker" data-ticket-kicker>Example night</span><h2 class="v7-ticket-artist" data-ticket-artist>{e(x['artist'])}</h2><p class="v7-ticket-venue" data-ticket-venue>{e(x['venue'])} · Dallas, TX</p><p class="v7-ticket-when" data-ticket-when>{e(x['when'])}</p><div class="v7-ticket-count"><b><span data-countdown="{x['iso']}">50</span></b><span>days to show day</span></div><div class="v7-ticket-row"><span>Bag policy</span><b>Verified</b></div><div class="v7-ticket-row"><span>Setlist</span><b>32 songs</b></div><div class="v7-ticket-row"><span>Way home</span><b>Rideshare zone</b></div><a class="v7-ticket-link" data-ticket-link href="/venue/{e(x['venueSlug'])}">Open this night →</a></div></div></section>'''

def try_it():
    return f'''<section class="v7-try" id="try"><div class="v7-shell"><div class="v7-try-head reveal"><p class="v7-eyebrow">Know before you go</p><h2>Type a venue.<br>Read the rules.</h2><p class="v7-lead">The same verified information the app shows, for {len(_VN)} venues. No download needed to see how it works.</p><label class="v7-search"><span class="sr-only">Venue name</span><input type="search" data-venue-search placeholder="American Airlines Center, Kia Forum, The O2…" autocomplete="off" spellcheck="false"><span class="v7-search-hint" data-venue-hint>Start typing</span></label></div><div class="v7-try-result" data-venue-result aria-live="polite"><div class="v7-try-cards">{component('venue')}{component('parking')}{component('getting-home')}</div><p class="v7-try-foot"><a data-venue-page href="/venue/{e(EXAMPLE['venueSlug'])}">Full guide for {e(EXAMPLE['venue'])} →</a>{cta('website-try','Save a show here in Concerto','btn-navy')}</p></div></div></section>'''

PHASES = [
  ('weeks','Weeks out','Learn the songs. Know the rules.','The setlist arrives as the tour plays. Bag policy, entry, and parking are already checked and dated.','setlist'),
  ('week','Show week','The forecast, the plan, the table.','Weather lands seven days out. Dinner gets booked six minutes from the door.','night-plan'),
  ('day','Show day','Leave on time. Walk in ready.','A leave-by built around the show time, the gate lines, and your bag against the rule at the door.','venue'),
  ('after','After the encore','The way home is already on the page.','The venue’s published pickup zone and your ride links, kept with the show.','getting-home'),
]
def night_timeline(title='One page.<br>The whole night.'):
    steps=''.join(f'<div class="v7-phase reveal" data-phase="{k}" data-phase-label="{e(l)}" data-phase-index="0{i+1}"><div class="v7-phase-copy"><span class="v7-eyebrow">{e(l)}</span><h3>{e(h)}</h3><p>{e(d)}</p></div>{component(c)}</div>' for i,(k,l,h,d,c) in enumerate(PHASES))
    return f'''<section class="v7-night" id="the-night"><div class="v7-shell v7-night-grid"><div class="v7-night-sticky"><p class="v7-eyebrow">Your Night</p><h2>{title}</h2><div class="v7-phase-dial"><b data-phase-num>01</b><span data-phase-name>Weeks out</span></div></div><div class="v7-night-steps">{steps}</div></div></section>'''

def marquee():
    titles=[]
    for slug,s in _SL.items():
        for song in (s.get('songs') or [])[:2]: titles.append(f'{song} · {s.get("artist","")}')
        if len(titles)>=28: break
    line=''.join(f'<span>{e(t)}</span>' for t in titles)
    return f'<div class="v7-marquee" aria-hidden="true"><div class="v7-marquee-track">{line}{line}</div></div>'

def numbers():
    items=[(len(_VN),'venue guides','researched from official sources, dated'),(len(_TR),'tours','followed as the run goes on'),(LIVE,'live setlists','labeled by source, never guessed'),(8,'essentials per venue','bag, entry, parking, rideshare and more')]
    return '<section class="v7-numbers"><div class="v7-shell v7-numbers-grid">'+''.join(f'<div class="reveal"><b data-count="{n}">{n}</b><span>{e(l)}</span><p>{e(d)}</p></div>' for n,l,d in items)+'</div></section>'

def plus():
    return f'''<section class="v7-plus"><div class="v7-shell v7-plus-grid"><div class="reveal"><p class="v7-eyebrow">Concerto+</p><h2>Make a plan<br>of it.</h2><p class="v7-lead">Plan My Night builds the evening around your show: dinner, arrival, the encore, and home. AI Bag Check reads your bag against the venue’s rule. The essentials stay free.</p><p class="v7-price"><b>$7.99</b> a month · <b>$69.99</b> a year · 7-day trial</p><a class="text-link" href="/premium">Explore Concerto+ <span aria-hidden="true">↗</span></a></div><div class="reveal">{component('night-plan')}</div></div></section>'''

def close(title='Your next show<br>starts here.', ct='website-footer'):
    return f'<section class="v7-close"><div class="v7-shell reveal"><h2>{title}</h2><div class="v7-close-actions">{cta(ct)}<img class="v7-qr" src="/img/appstore-qr.png" width="96" height="96" alt="QR code for Concerto on the App Store" loading="lazy"></div><p class="v7-fine">Free to download. Concerto+ available in the app.</p></div></section>'

def home_page(head, schema):
    return head('Concerto | Everything After the Ticket, in One Place','Save your show. Concerto keeps the venue rules, setlist, timing, places nearby, and the way home on one page. 346 verified venue guides.','/',schema)+V7_JS+'<main class="v7">'+hero_home()+try_it()+night_timeline()+marquee()+numbers()+plus()+close()+'</main>'+page_end()

def your_night_page(head):
    hero=f'''<section class="v7-hero v7-hero-short"><div class="v7-shell"><div class="v7-hero-copy reveal"><p class="v7-eyebrow">Your Night · Free in Concerto</p><h1>The show is yours.<br>So is the night.</h1><p class="v7-lead">Save a concert and the evening gets a home. It changes as show day gets closer, so the top of the page always says what to do next.</p><div class="v7-actions">{cta('website-your-night','Save your next show')}</div></div></div></section>'''
    free='<section class="v7-numbers"><div class="v7-shell v7-numbers-grid v7-three"><div class="reveal"><b>Free</b><span>always</span><p>Saving shows, venue essentials, setlists, directions.</p></div><div class="reveal"><b>Dated</b><span>and sourced</span><p>Every venue section shows where it came from and when it was checked.</p></div><div class="reveal"><b>Honest</b><span>by default</span><p>When something is not confirmed, the page says so instead of guessing.</p></div></div></section>'
    return head('Your Night | Every Part of Your Show | Concerto','Save a concert and keep venue rules, available setlists, nearby places, and the way home together.','/your-night')+V7_JS+'<main class="v7">'+hero+night_timeline('From the ticket<br>to the way home.')+marquee()+free+close('Save your next show.','website-your-night')+'</main>'+page_end()

def premium_page(head):
    schema='<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@type':'Product','name':'Concerto+','description':'Personalized concert-night planning inside Concerto.','brand':{'@type':'Brand','name':'Concerto'},'offers':[{'@type':'Offer','price':'7.99','priceCurrency':'USD','url':'https://concertocity.com/premium','name':'Monthly'},{'@type':'Offer','price':'69.99','priceCurrency':'USD','url':'https://concertocity.com/premium','name':'Yearly'}]})+'</script>'
    hero=f'''<section class="v7-hero v7-hero-short"><div class="v7-shell v7-hero-grid"><div class="v7-hero-copy reveal"><p class="v7-eyebrow">Concerto+</p><h1>Good plans.<br>Great nights.</h1><p class="v7-lead">A plan around your show and your taste. A little less to figure out before you leave.</p><div class="v7-actions">{cta('website-premium','Start your 7-day trial in the app')}</div><p class="v7-price"><b>$7.99</b> a month · <b>$69.99</b> a year</p></div><div class="reveal">{component('night-plan')}</div></div></section>'''
    feats='<section class="v7-numbers"><div class="v7-shell v7-numbers-grid v7-three"><div class="reveal"><b>Plan My Night</b><span>the evening, built</span><p>Dinner, arrival, the encore, and home, in a timeline you can change.</p></div><div class="reveal"><b>AI Bag Check</b><span>before you leave</span><p>Your bag against the venue’s published policy, with the rule it used.</p></div><div class="reveal"><b>Show-day alerts</b><span>in venue time</span><p>Forecast in the morning, leave-by in the afternoon, the way home after.</p></div></div></section>'
    free=f'<section class="v7-plus"><div class="v7-shell v7-plus-grid"><div class="reveal"><p class="v7-eyebrow">What stays free</p><h2>The essentials.<br>Always.</h2><p class="v7-lead">Bag policy, entry, parking, rideshare, accessibility, setlists, and directions never sit behind Concerto+.</p></div><div class="reveal">{component("venue")}</div></div></section>'
    return head('Concerto+ | Your Whole Night, Planned Around You','Personalized concert-night planning, AI Bag Check, and show-day alerts with Concerto+.','/premium',schema)+V7_JS+'<main class="v7">'+hero+feats+free+close('Start with the app.','website-premium')+'</main>'+page_end()
