"""Concerto Guides: articles written by Concerto, built from official sources and Concerto's own
venue data. Each guide is a dict; site_v8.py renders them into /guides/<slug> and the /guides hub.

Rules for every guide: facts about a tour come from the tour's own announcement; facts about a
venue come from Concerto's venue guide (and link to it); nothing is estimated or invented."""
import html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENUES = {v['id']: v for v in json.loads((ROOT / 'data/venues.json').read_text())}
INFO = json.loads((ROOT / 'data/venue_info.json').read_text())
HOUSE = set(json.loads((ROOT / 'data/house/index.json').read_text())) if (ROOT / 'data/house/index.json').exists() else set()

def e(x): return html.escape(str(x or ''), quote=True)
def vlink(slug): return f'<a href="/venue/{slug}">{e(VENUES[slug]["name"])}</a>'
def checked(slug, key):
    d = (INFO.get(slug, {}).get(key) or {}).get('verified')
    if not d: return ''
    import datetime as dt
    return dt.date.fromisoformat(d).strftime('%b %Y')

# ---------------------------------------------------------------- Jingle Ball 2026
JB_SRC = 'https://www.iheartmedia.com/press/iheartmedia-rings-holiday-season-iconic-2026-national-iheartradio-jingle-ball-tour-presented'
JB = [  # from iHeartMedia's tour announcement
 ('Tue, Dec 1', 'Fort Worth, TX', 'ariat-arena', '7:30 p.m.', '106.1 KISS FM', 'KATSEYE, RAYE, Ludacris, Myles Smith, Tove Lo, Kylie Cantrall, The Beaches, JYT'),
 ('Fri, Dec 4', 'Los Angeles, CA', 'intuit-dome', '7:30 p.m.', '102.7 KIIS FM', 'Olivia Rodrigo, Hilary Duff, RAYE, OneRepublic, SIENNA SPIRO, Freya Skye, Bella Kay, Stella Lefty, The Beaches'),
 ('Mon, Dec 7', 'Chicago, IL', 'allstate-arena', '7:00 p.m.', '103.5 KISS FM', 'RAYE, OneRepublic, Ludacris, Dominic Fike, Tove Lo, Freya Skye, The Beaches, JYT'),
 ('Tue, Dec 8', 'Detroit, MI', 'little-caesars-arena', '7:30 p.m.', 'iHeartRadio Channel 95.5', 'Alex Warren, OneRepublic, Ludacris, Tove Lo, Jason Derulo, Bella Kay, Freya Skye, The Beaches, JYT'),
 ('Fri, Dec 11', 'New York, NY', 'madison-square-garden', '7:00 p.m.', 'Z100', 'SOMBR, Alex Warren, Charlie Puth, Hilary Duff, Teddy Swims, SIENNA SPIRO, TOMORROW X TOGETHER & YEONJUN, Stella Lefty, Freya Skye, with special guests Bella Kay and The Beaches'),
 ('Sun, Dec 13', 'Boston, MA', 'td-garden', '6:00 p.m.', 'Kiss 108', 'SOMBR, Hilary Duff, Nickelback, TOMORROW X TOGETHER & YEONJUN, Freya Skye, Stella Lefty, ADÉLA, The Beaches, JYT'),
 ('Mon, Dec 14', 'Washington, D.C.', 'capital-one-arena', '7:30 p.m.', 'HOT 99.5', 'Jonas Brothers, SOMBR, OneRepublic, Ludacris, Nickelback, TOMORROW X TOGETHER & YEONJUN, Kylie Cantrall, The Beaches, JYT'),
 ('Tue, Dec 15', 'Philadelphia, PA', 'wells-fargo-center', '7:30 p.m.', 'Q102', 'SOMBR, Charlie Puth, OneRepublic, Ludacris, ADÉLA, Jason Derulo, Kylie Cantrall, The Beaches, JYT'),
 ('Thu, Dec 17', 'Nashville, TN', 'bridgestone-arena', '7:30 p.m.', '107.5 The River', 'Alex Warren, Hilary Duff, Teddy Swims, OneRepublic, Nickelback, Stella Lefty, The Beaches, JYT'),
]
# Short versions of each arena's rules, written from Concerto's venue guide for it.
JB_BAG = {
 'ariat-arena': 'Bags up to 12 x 6 x 12 in. No backpacks, duffels, laptop bags or oversized totes.',
 'intuit-dome': 'Clutches or clear bags only, up to 10 x 6 x 2 in, and every bag is X-rayed.',
 'allstate-arena': 'No backpacks, totes, or mid-size or large bags. Diaper and medical bags are searched.',
 'little-caesars-arena': 'Nothing larger than 4 x 6 x 1.5 in: wallets, clutches, fanny packs, small clear bags.',
 'madison-square-garden': 'Bags up to 22 x 14 x 9 in that fit under your seat.',
 'td-garden': 'Small bags, clutches, crossbodies and wristlets up to 4 x 6 x 1.5 in. Oversized bags can be stored on site for a fee.',
 'capital-one-arena': 'No bags. Wallet-size clutches up to 5 x 7 in, plus medical and parenting bags.',
 'wells-fargo-center': 'Clutches under 4.5 x 6.5 in go straight in. Bags up to 14 x 14 x 6 in are X-rayed.',
 'bridgestone-arena': 'Bags up to 12 x 12 x 6 in, screened at the door. Bags are discouraged.',
}
JB_RIDE = {
 'ariat-arena': 'Pickup is on Harley Avenue on the north end of the building.',
 'intuit-dome': 'The Mobility Hub on the first level of the East Garage is the only rideshare spot.',
 'allstate-arena': 'No published zone. Walk a block or two from the main exit before you request.',
 'little-caesars-arena': 'Westbound Fisher Service Drive, next to the UWM Garage.',
 'madison-square-garden': 'No zone. Get picked up on 7th or 8th Avenue between 31st and 34th Streets.',
 'td-garden': 'The rideshare zone on Merrimac Street.',
 'capital-one-arena': '6th and E, 7th and E, 5th and G, or 8th and G Streets.',
 'wells-fargo-center': 'Lyft pickup is in Lot D, at the southeast corner of the arena.',
 'bridgestone-arena': 'Drop-off is the eastbound curb lane of Broadway between 5th and 6th Avenues.',
}
JB_REENTRY_NO = ['ariat-arena', 'intuit-dome', 'little-caesars-arena', 'madison-square-garden', 'td-garden', 'wells-fargo-center']

def jingle_ball():
    stops = ''.join(f'<tr><td data-l="Date">{d}</td><td data-l="City">{c}</td><td data-l="Arena">{vlink(s)}</td><td data-l="Starts">{t}</td><td data-l="Lineup">{e(l)}</td></tr>' for d, c, s, t, st, l in JB)
    bags = ''.join(f'<tr><td data-l="Arena">{vlink(s)}</td><td data-l="Bag rule">{e(JB_BAG[s])}</td><td data-l="Checked">{checked(s, "bagPolicy")}</td></tr>' for _, _, s, *_ in JB)
    rides = ''.join(f'<li><b>{e(VENUES[s]["name"])}:</b> {e(JB_RIDE[s])}</li>' for _, _, s, *_ in JB)
    body = f'''
<p class="c-art-answer">The 2026 iHeartRadio Jingle Ball Tour plays nine arenas between December 1 and December 17, starting at Ariat Arena in Fort Worth and ending at Bridgestone Arena in Nashville. Every stop has its own lineup, and every arena has its own bag rule, from 22 x 14 x 9 inches at Madison Square Garden to 4 x 6 x 1.5 inches at TD Garden.</p>

<h2>When and where is Jingle Ball 2026?</h2>
<p>Here is every stop, with the start time and lineup iHeartMedia announced. Times are local. Each arena links to its Concerto venue guide.</p>
<div class="c-art-table"><table><thead><tr><th>Date</th><th>City</th><th>Arena</th><th>Starts</th><th>Lineup</th></tr></thead><tbody>{stops}</tbody></table></div>
<p class="c-art-fine">Lineups are as announced by iHeartMedia, which notes that artists and events can change without notice.</p>

<h2>Who plays the most Jingle Ball stops?</h2>
<p>The Beaches play all nine. OneRepublic plays six: Los Angeles, Chicago, Detroit, Washington, D.C., Philadelphia and Nashville. Ludacris plays five, and SOMBR plays four on the East Coast run from New York to Philadelphia. Olivia Rodrigo plays only Los Angeles, and the Jonas Brothers play only Washington, D.C.</p>

<h2>What bag can you bring to Jingle Ball?</h2>
<p>This is where Jingle Ball catches people out. The tour is the same, but the bag rule is set by each arena, and they are very different. A bag that is fine at Madison Square Garden will not get into TD Garden two nights later.</p>
<div class="c-art-table"><table><thead><tr><th>Arena</th><th>Bag rule</th><th>Checked</th></tr></thead><tbody>{bags}</tbody></table></div>
<p>The smallest limits are at Little Caesars Arena and TD Garden, where anything bigger than a phone wallet is too big. Capital One Arena allows no bags at all beyond a small clutch. If you are not sure, bring the smallest bag you own, or none.</p>

<h2>Can you leave Jingle Ball and come back in?</h2>
<p>Usually not. Ariat Arena, Intuit Dome, Little Caesars Arena, Madison Square Garden, TD Garden and Xfinity Mobile Arena all say there is no re-entry once your ticket is scanned. At Capital One Arena, leaving during a concert means buying a new ticket to get back in. Bridgestone Arena says re-entry depends on the event, and Allstate Arena has not published a rule, so treat leaving as final there too.</p>

<h2>How do you get home after Jingle Ball?</h2>
<p>Every arena empties at once after the last act. Know your pickup spot before the show ends, not after.</p>
<ul class="c-art-list">{rides}</ul>
<p>At Madison Square Garden, Concerto’s <a href="/venue/madison-square-garden">House Map</a> also shows every entrance, food stand and restroom by section.</p>

<h2>Is Jingle Ball on TV?</h2>
<p>Yes. ABC airs an iHeartRadio Jingle Ball 2026 special in December, and it streams the next day on Hulu, Disney+ and on demand. iHeartMedia has not announced the exact air date yet.</p>

<h2>How do you plan your Jingle Ball night?</h2>
<p>Save your Jingle Ball show in Concerto and Your Night puts that arena’s bag rule, entrances, parking and rideshare pickup on one page, with a reminder on the morning of the show. It is free on iPhone and Android.</p>
'''
    faq = [
        ('When does Jingle Ball 2026 start?', 'The tour opens Tuesday, December 1 at Ariat Arena in Fort Worth and ends Thursday, December 17 at Bridgestone Arena in Nashville.'),
        ('Where do you buy Jingle Ball tickets?', 'iHeartMedia sells Jingle Ball tickets through Ticketmaster. General on-sale started Friday, October 2.'),
        ('Can you bring a bag to Jingle Ball?', 'It depends on the arena. Madison Square Garden allows bags up to 22 x 14 x 9 inches, while TD Garden and Little Caesars Arena allow nothing larger than 4 x 6 x 1.5 inches. Check your arena’s rule above.'),
        ('Does Jingle Ball support a charity?', 'Yes. Eight stops support the Ryan Seacrest Foundation, and the Fort Worth show supports Kidd’s Kids. A portion of ticket sales goes to each.'),
        ('Can the Jingle Ball lineup change?', 'Yes. iHeartMedia says artists and events can change or be canceled without notice, so check the lineup close to your show.'),
    ]
    return {
        'slug': 'jingle-ball-2026', 'title': 'Jingle Ball 2026: Dates, Lineups and Arena Guide',
        'h1': 'Jingle Ball 2026: every stop, every lineup, and what to know',
        'desc': 'Every 2026 iHeartRadio Jingle Ball stop from December 1 to 17, the lineup for each city, and each arena’s bag rule, re-entry and rideshare pickup.',
        'kicker': 'Tours', 'date': '2026-11-03', 'body': body, 'faq': faq,
        'sources': [('iHeartMedia: 2026 Jingle Ball Tour announcement', JB_SRC)] + [(f'Concerto venue guide: {VENUES[s]["name"]}', f'https://concertocity.com/venue/{s}') for _, _, s, *_ in JB],
        'tour': 'jingle-ball-2026-tour', 'venues': [s for _, _, s, *_ in JB],
    }

GUIDES = [jingle_ball]
def all_guides(): return [g() for g in GUIDES]
