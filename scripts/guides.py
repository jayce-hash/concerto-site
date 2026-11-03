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

# ---------------------------------------------------------------- Holiday concerts 2026
BYNAME = {v['name'].lower(): k for k, v in VENUES.items()}
def vname(n):
    s = BYNAME.get(n.lower())
    return f'<a href="/venue/{s}">{e(n)}</a>' if s else e(n)

TSO_SRC = 'https://ultimateclassicrock.com/trans-siberian-orchestra-winter-tour-2026/'
TSO_SITE = 'https://trans-siberian.com/pages/tour'
TSO = """Nov 19|Green Bay, WI|Resch Center|2;Nov 19|Council Bluffs, IA|Mid-America Center|1;Nov 21|Cincinnati, OH|Heritage Bank Center|2;Nov 21|Denver, CO|Ball Arena|2;
Nov 22|Youngstown, OH|Covelli Centre|2;Nov 22|Colorado Springs, CO|Broadmoor World Arena|2;Nov 24|Wilkes-Barre, PA|Mohegan Arena at Casey Plaza|1;Nov 24|Salt Lake City, UT|Delta Center|2;
Nov 27|Manchester, NH|SNHU Arena|2;Nov 27|Boise, ID|ExtraMile Arena|2;Nov 28|Worcester, MA|DCU Center|2;Nov 28|Portland, OR|Moda Center|2;Nov 29|Uncasville, CT|Mohegan Sun Arena|2;
Nov 29|Seattle, WA|Climate Pledge Arena|2;Dec 2|Nashville, TN|Bridgestone Arena|1;Dec 2|Sacramento, CA|Golden 1 Center|2;Dec 3|Charleston, WV|Charleston Coliseum|1;Dec 3|Fresno, CA|Save Mart Center|1;
Dec 4|Toledo, OH|Huntington Center|2;Dec 4|Las Vegas, NV|Michelob Ultra Arena|1;Dec 5|Columbus, OH|Nationwide Arena|2;Dec 5|Ontario, CA|Toyota Arena|2;Dec 6|Grand Rapids, MI|Van Andel Arena|2;
Dec 6|Phoenix, AZ|Mortgage Matchup Center|2;Dec 9|Allentown, PA|PPL Center|1;Dec 9|Austin, TX|Moody Center|1;Dec 10|Raleigh, NC|Lenovo Center|1;Dec 10|Bossier City, LA|Brookshire Grocery Arena|1;
Dec 11|Greenville, SC|Bon Secours Wellness Arena|2;Dec 11|Houston, TX|Toyota Center|2;Dec 12|Charlotte, NC|Spectrum Center|2;Dec 12|San Antonio, TX|Frost Bank Center|2;Dec 13|Atlanta, GA|Gas South Arena|2;
Dec 13|Dallas, TX|American Airlines Center|2;Dec 16|Charlottesville, VA|John Paul Jones Arena|1;Dec 16|Birmingham, AL|Legacy Arena at the BJCC|1;Dec 17|Albany, NY|MVP Arena|1;
Dec 17|Jacksonville, FL|VyStar Veterans Memorial Arena|1;Dec 18|Hershey, PA|Giant Center|2;Dec 18|Sunrise, FL|Amerant Bank Arena|1;Dec 19|Pittsburgh, PA|PPG Paints Arena|2;Dec 19|Orlando, FL|Kia Center|2;
Dec 20|Philadelphia, PA|Xfinity Mobile Arena|2;Dec 20|Tampa, FL|Benchmark International Arena|2;Dec 22|Cleveland, OH|Rocket Arena|2;Dec 22|Indianapolis, IN|Gainbridge Fieldhouse|2;
Dec 23|Detroit, MI|Little Caesars Arena|2;Dec 23|Chicago, IL|Allstate Arena|2;Dec 26|Newark, NJ|Prudential Center|2;Dec 26|Milwaukee, WI|Fiserv Forum|2;Dec 27|Washington, D.C.|Capital One Arena|2;
Dec 27|Minneapolis, MN|Target Center|2;Dec 29|Toronto, ON|Scotiabank Arena|2;Dec 29|Kansas City, MO|T-Mobile Center|2;Dec 30|Buffalo, NY|KeyBank Center|2;Dec 30|St. Louis, MO|Enterprise Center|2"""
TSO_ROWS = [r.split('|') for r in TSO.replace('\n', '').split(';')]
PTX_SRC = 'https://www.jambase.com/article/pentatonix-tour-dates-2026-fall'
LADYA_SRC = 'https://musicrow.com/2026/06/lady-a-plots-this-winters-night-tour-2026/'
LADYA = [('Thu, Dec 10', 'Northfield, OH', 'Northfield Park Racino'), ('Fri, Dec 11', 'Gary, IN', 'Hard Rock Casino Northern Indiana'),
         ('Sat, Dec 12', 'Shipshewana, IN', 'Blue Gate Performing Arts Center'), ('Thu, Dec 17', 'New York, NY', 'Beacon Theatre'),
         ('Fri, Dec 18', 'Bensalem, PA', 'Parx Casino'), ('Sat, Dec 19', 'Greensboro, NC', 'Steven Tanger Center for the Performing Arts'),
         ('Mon, Dec 21', 'Nashville, TN', 'Ryman Auditorium (matinee)'), ('Mon, Dec 21', 'Nashville, TN', 'Ryman Auditorium (evening)')]

def holiday():
    n_tso = sum(int(r[3]) for r in TSO_ROWS)
    guides = sum(1 for r in TSO_ROWS if r[2].lower() in BYNAME)
    tso = ''.join(f'<tr><td data-l="Date">{r[0]}</td><td data-l="City">{e(r[1])}</td><td data-l="Arena">{vname(r[2])}</td><td data-l="Starts">{"2 shows" if r[3] == "2" else "1 show"}</td></tr>' for r in TSO_ROWS)
    lady = ''.join(f'<tr><td data-l="Date">{d}</td><td data-l="City">{e(c)}</td><td data-l="Arena">{vname(v.split(" (")[0]) if "(" not in v else vname(v.split(" (")[0]) + " " + e("(" + v.split(" (")[1])}</td></tr>' for d, c, v in LADYA)
    body = f'''
<p class="c-art-answer">Four big holiday tours play North America this season. Trans-Siberian Orchestra brings The Ghosts of Christmas Eve to more than 50 cities from November 19 to December 30. Pentatonix plays arenas from November 5 to December 22. The iHeartRadio Jingle Ball visits nine arenas from December 1 to 17, and Lady A plays eight shows from December 10 to 21.</p>

<h2>What are the biggest holiday tours of 2026?</h2>
<div class="c-art-table"><table><thead><tr><th>Tour</th><th>Dates</th><th>Size</th><th>Starts</th><th>Ends</th></tr></thead><tbody>
<tr><td><a href="/tour/trans-siberian-orchestra-the-ghosts-of-christmas-eve-tour">Trans-Siberian Orchestra: The Ghosts of Christmas Eve</a></td><td>Nov 19 to Dec 30</td><td>{len(TSO_ROWS)} stops, {n_tso} shows</td><td>Green Bay and Council Bluffs</td><td>Buffalo and St. Louis</td></tr>
<tr><td><a href="/tour/pentatonix-christmas-in-the-city-tour">Pentatonix: Christmas in the City Tour</a></td><td>Nov 5 to Dec 22</td><td>Arenas across the U.S. and Canada</td><td>Tacoma Dome, Tacoma</td><td>Kia Forum, Los Angeles</td></tr>
<tr><td><a href="/blog/jingle-ball-2026">iHeartRadio Jingle Ball 2026</a></td><td>Dec 1 to Dec 17</td><td>9 arenas</td><td>Ariat Arena, Fort Worth</td><td>Bridgestone Arena, Nashville</td></tr>
<tr><td><a href="/tour/lady-a-this-winters-night-tour">Lady A: This Winter’s Night Tour</a></td><td>Dec 10 to Dec 21</td><td>8 shows</td><td>Northfield, OH</td><td>Ryman Auditorium, Nashville</td></tr>
</tbody></table></div>

<h2>Where is Trans-Siberian Orchestra playing in 2026?</h2>
<p>This year is the 30th anniversary of The Ghosts of Christmas Eve. On every date the tour plays two cities at once, because two touring groups perform the same show in different parts of North America. Many cities get two shows in one day, so check the time on your ticket.</p>
<div class="c-art-table"><table><thead><tr><th>Date</th><th>City</th><th>Arena</th><th>Shows</th></tr></thead><tbody>{tso}</tbody></table></div>
<p class="c-art-fine">Dates as announced. Concerto has a venue guide for {guides} of these {len(TSO_ROWS)} arenas, linked above. Showtimes are on the Trans-Siberian Orchestra website.</p>

<h2>When is Pentatonix on tour?</h2>
<p>The Christmas in the City Tour opens November 5 at the Tacoma Dome and closes December 22 at the <a href="/venue/kia-forum">Kia Forum</a> in Los Angeles. In between it plays arenas from British Columbia and Ontario to Texas, Georgia and Arizona. The full list of cities is on the <a href="/tour/pentatonix-christmas-in-the-city-tour">Pentatonix tour page</a>.</p>

<h2>Where is Lady A playing this December?</h2>
<p>This Winter’s Night Tour is eight shows between December 10 and 21, and it ends with two shows at the Ryman Auditorium in Nashville on December 21.</p>
<div class="c-art-table"><table><thead><tr><th>Date</th><th>City</th><th>Venue</th></tr></thead><tbody>{lady}</tbody></table></div>

<h2>What should you know before a holiday arena show?</h2>
<p>The tour is the same in every city, but the rules are set by each venue. Bag limits run from a phone-size clutch at some arenas to 22 x 14 x 9 inches at Madison Square Garden, and many arenas do not allow re-entry once your ticket is scanned. Holiday shows also bring big winter coats, so check whether your venue offers coat check or lets you carry one in.</p>
<p>Open your venue’s Concerto guide before you leave. It has the bag rule, entrances, parking, rideshare pickup and re-entry, each checked against the venue’s own sources and dated.</p>

<h2>How do you plan a holiday concert night?</h2>
<p>Save your show in Concerto and Your Night puts your venue’s rules, directions and the setlist on one page, with a reminder on the morning of the show. It is free on iPhone and Android.</p>
'''
    faq = [
        ('When does the Trans-Siberian Orchestra 2026 tour start?', 'November 19, with shows in Green Bay, Wisconsin and Council Bluffs, Iowa. It ends December 30 in Buffalo and St. Louis.'),
        ('Why does Trans-Siberian Orchestra play two cities on the same day?', 'Two touring groups perform The Ghosts of Christmas Eve at the same time in different parts of North America.'),
        ('Where does the Pentatonix Christmas tour start and end?', 'It opens November 5 at the Tacoma Dome in Tacoma, Washington and closes December 22 at the Kia Forum in Los Angeles.'),
        ('Where is Lady A’s last show of the year?', 'The Ryman Auditorium in Nashville on December 21, with a matinee and an evening show.'),
        ('Can I bring a bag to a holiday arena show?', 'It depends on the venue, not the tour. Check your venue’s Concerto guide for its bag rule before you leave.'),
    ]
    return {'slug': 'holiday-concerts-2026', 'title': 'Holiday Concerts 2026: The Biggest Christmas Tours',
            'h1': 'Holiday concerts 2026: the biggest Christmas tours this winter',
            'desc': 'Trans-Siberian Orchestra, Pentatonix, Jingle Ball and Lady A: every big holiday tour of 2026, with dates, stops, and what to know before you go.',
            'kicker': 'Tours', 'date': '2026-11-03', 'body': body, 'faq': faq,
            'sources': [('Ultimate Classic Rock: Trans-Siberian Orchestra 2026 winter tour', TSO_SRC), ('Trans-Siberian Orchestra: tour dates and showtimes', TSO_SITE),
                        ('JamBase: Pentatonix Christmas in the City Tour 2026', PTX_SRC), ('MusicRow: Lady A This Winter’s Night Tour 2026', LADYA_SRC),
                        ('iHeartMedia: 2026 Jingle Ball Tour announcement', JB_SRC)],
            'tour': 'trans-siberian-orchestra-the-ghosts-of-christmas-eve-tour'}

# ---------------------------------------------------------------- First time at MSG
MSG = 'https://www.msg.com/madison-square-garden'
def msg_first_time():
    gates = [('Chase Entrance A', '8th Avenue, toward 31st Street'), ('Chase Entrance B', '8th Avenue, toward 33rd Street. Has a CLEAR lane'),
             ('Chase Entrance C', '33rd Street, toward 8th Avenue. Has a CLEAR lane'), ('Chase Entrance D', '33rd Street, toward 7th Avenue'),
             ('7th Ave Entrance', 'Through Chase Square on 7th Avenue, between 31st and 33rd Streets. Accessible'),
             ('Accessible entrance at 8 Penn', '33rd Street and 8th Avenue')]
    g = ''.join(f'<tr><td data-l="Arena">{e(n)}</td><td data-l="Bag rule">{e(w)}</td></tr>' for n, w in gates)
    food = [('100 Level (Kalshi Concourse)', 'Mighty Quinn’s Barbeque and Carnegie Deli by 105, Daily Burger by 106 and 116, Pat LaFrieda by 107, Brooklyn Dumpling Shop by 108, Veselka by 109, Gluten-Free at The Garden by 112, Shah’s Halal by 114, Simply Vegan by 116, Paulie Gee’s Pizza by 117, TAO Sushi by 118, Fuku by 119'),
            ('200 Level (Pepsi Concourse)', 'Prime Rib and Pat LaFrieda by 203, Mighty Quinn’s by 204, SeoulBird Korean BBQ by 210, Carnegie Deli by 219, Paulie Gee’s Pizza by 224'),
            ('Hyundai Bridge', 'Veselka and Chicken & Things by 304, Daily Burger by 305, Garden Melt by 319')]
    f = ''.join(f'<tr><td data-l="Arena">{e(l)}</td><td data-l="Bag rule">{e(x)}</td></tr>' for l, x in food)
    body = f'''
<p class="c-art-answer">Madison Square Garden allows bags up to 22 x 14 x 9 inches that fit under your seat. Fans enter through Chase Entrances A to D on 8th Avenue and 33rd Street, or the 7th Avenue Entrance through Chase Square, and your ticket shows the entrance for your seat. There is no re-entry, and no rideshare zone: get picked up on 7th or 8th Avenue between 31st and 34th Streets.</p>

<h2>Which entrance should you use at Madison Square Garden?</h2>
<p>Use the entrance printed on your ticket. It is matched to your seat. These are the public entrances on MSG’s own entrance map.</p>
<div class="c-art-table"><table><thead><tr><th>Entrance</th><th>Where it is</th></tr></thead><tbody>{g}</tbody></table></div>
<p>Wheelchair accessible entrances are on all sides of the building. The Box Office and will call are at 7th Avenue and 31st Street, open two hours before the event, with photo ID.</p>

<h2>What bag can you bring to MSG?</h2>
<p>Bags up to 22 x 14 x 9 inches are allowed if they fit under your seat. Anything larger is not. That is one of the more generous bag rules among big arenas, but the full list of prohibited items is on MSG’s FAQ, so check it if you are bringing anything unusual.</p>

<h2>Where should you eat inside Madison Square Garden?</h2>
<p>MSG lists every stand by the section it sits near. These are some of the highlights on each level.</p>
<div class="c-art-table"><table><thead><tr><th>Level</th><th>Stands, by nearest section</th></tr></thead><tbody>{f}</tbody></table></div>
<p>For dietary needs, Gluten-Free at The Garden is near Section 112, Simply Vegan near 116, and Shah’s Halal near 114. In the Concerto app, <a href="/features#venues">House Map</a> shows every stand, bar and restroom by section, and lists what is closest to your seat first.</p>

<h2>Where are Guest Services, first aid and the nursing room?</h2>
<p>All three are together on the 100 Level, the Kalshi Concourse, outside Section 117. Sensory bags are free at Guest Services with an ID. There are also guest experience booths outside Section 206 and on the Hyundai Bridge outside Section 328.</p>

<h2>Can you leave MSG and come back in?</h2>
<p>No. MSG has no re-entry, and leaving voids your ticket. Eat and bring what you need before you go through security.</p>

<h2>Where does the stage sit for concerts?</h2>
<p>On MSG’s concert seat map, the stage is in front of Sections 111 to 113. Layouts can change from show to show, so check your event’s own seat map.</p>

<h2>How do you get home from Madison Square Garden?</h2>
<p>MSG has no designated rideshare zone. Arrange pickup on 7th Avenue or 8th Avenue between 31st and 34th Streets. Penn Station is directly underneath the arena.</p>

<h2>How do you plan your night at MSG?</h2>
<p>Save your MSG show in Concerto. Your Night puts the bag rule, your entrance, the setlist and the ride home on one page, with a reminder on the morning of the show, and House Map finds the nearest food and restroom to your seat. It is free on iPhone and Android.</p>
'''
    faq = [
        ('What size bag can I bring to Madison Square Garden?', 'Bags up to 22 x 14 x 9 inches that fit under your seat. Larger bags are not allowed.'),
        ('Which MSG entrance should I use?', 'The one printed on your ticket. Chase Entrances A to D are on 8th Avenue and 33rd Street, and the 7th Avenue Entrance is through Chase Square.'),
        ('Can you leave MSG and come back?', 'No. MSG has no re-entry, and leaving voids your ticket.'),
        ('Where do I get an Uber after a show at MSG?', 'There is no rideshare zone. Get picked up on 7th or 8th Avenue between 31st and 34th Streets.'),
        ('Where is will call at Madison Square Garden?', 'At the Box Office on 7th Avenue and 31st Street. It opens two hours before the event, and you need a photo ID.'),
    ]
    return {'slug': 'first-time-madison-square-garden', 'title': 'First Time at Madison Square Garden: What to Know',
            'h1': 'First time at Madison Square Garden: bags, entrances, food and getting home',
            'desc': 'Your first show at MSG: the bag rule, which entrance to use, where to eat by section, Guest Services, re-entry, and where to get picked up after.',
            'kicker': 'Venues', 'date': '2026-11-03', 'body': body, 'faq': faq,
            'sources': [('MSG: Entrances', MSG + '/entrances'), ('MSG: Food and drink', MSG + '/food-drink'), ('MSG: FAQs', MSG + '/faqs'),
                        ('MSG: Accessibility services', MSG + '/accessibility-services'), ('MSG: Concert seating map', MSG + '/seating/msg-concerts'),
                        ('Concerto venue guide: Madison Square Garden', 'https://concertocity.com/venue/madison-square-garden')],
            'tour': None}

GUIDES = [jingle_ball, holiday, msg_first_time]
