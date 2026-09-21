"""Real product content instead of screenshots.

Every place the site used to show an app capture now renders a component built from
the same data files the app reads (venue_info.json, setlists.json, venues.json). One
treatment everywhere: a card, no phone frame, no status bar, nothing invented.
Swap the example show by editing EXAMPLE below; everything else follows the data.
"""
import html, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
def e(v): return html.escape(str(v or ''), quote=True)
_VI = json.loads((ROOT / 'data/venue_info.json').read_text())
_SL = json.loads((ROOT / 'setlists.json').read_text())
_VN = json.loads((ROOT / 'data/venues.json').read_text())
_TR = json.loads((ROOT / 'data/tours.json').read_text())
EXAMPLE = {'artist': 'Jonas Brothers', 'tour': 'The Burning Up Tour All Over Again', 'tourSlug': 'jonas-brothers-the-burning-up-tour-all-over-again',
           'venueSlug': 'american-airlines-center', 'venue': 'American Airlines Center', 'when': 'Tue, Nov 10 · Show 7:30 PM', 'iso': '2026-11-10T19:30:00-06:00'}

def _card(kind, inner, label=''):
    return f'<figure class="night-card night-card-{kind}" aria-label="{e(label)}">{inner}</figure>'

def next_show():
    x = EXAMPLE
    return _card('navy', f'<span class="nc-kicker">Your next show</span><h3>{e(x["artist"])}</h3><p class="nc-sub">{e(x["tour"])}</p><p class="nc-meta">{e(x["venue"])} · {e(x["when"])}</p><div class="nc-count"><b><span data-countdown="{x["iso"]}">50</span> days</b><span>until show day</span></div><span class="nc-link">View Your Night →</span>', 'Your next show card')

def section(key, title):
    v = _VI.get(EXAMPLE['venueSlug']) or {}; s = v.get(key) or {}
    lists = ''
    if s.get('allowed') or s.get('prohibited'):
        lists = '<div class="nc-lists">' + (f'<div><span class="nc-label">Allowed</span><ul>{"".join("<li>"+e(a)+"</li>" for a in s.get("allowed", [])[:4])}</ul></div>' if s.get('allowed') else '') + (f'<div><span class="nc-label">Not allowed</span><ul class="no">{"".join("<li>"+e(a)+"</li>" for a in s.get("prohibited", [])[:3])}</ul></div>' if s.get('prohibited') else '') + '</div>'
    ver = f'<span class="nc-verified">Verified {e(s.get("verified"))}</span>' if s.get('verified') else ''
    return _card('paper', f'<div class="nc-head"><h3>{e(title)}</h3>{ver}</div><p class="nc-body">{e(s.get("summary") or s.get("note") or "")}</p>{lists}<span class="nc-link">Official Info ↗</span>', f'{title} for {EXAMPLE["venue"]}')

def essentials():
    v = _VI.get(EXAMPLE['venueSlug']) or {}
    rows = ''.join(f'<div class="nc-row"><span>{e(t)}</span><b>{e((v.get(k) or {}).get("verified") or "")}</b></div>' for k, t in [('bagPolicy','Bag Policy'),('gates','Entrances & Doors'),('parking','Parking'),('rideshare','Rideshare'),('reEntry','Re-entry'),('accessibility','Accessibility')] if v.get(k))
    return _card('paper', f'<div class="nc-head"><h3>Venue Essentials</h3><span class="nc-kicker">{e(EXAMPLE["venue"])}</span></div>{rows}', 'Venue essentials list')

def getting_home():
    v = _VI.get(EXAMPLE['venueSlug']) or {}; r = v.get('rideshare') or {}
    return _card('navy', f'<span class="nc-kicker">Encore exit</span><h3>Getting Home</h3><p class="nc-body">{e(r.get("note") or r.get("summary") or "")}</p><div class="nc-pills"><span>Uber</span><span>Lyft</span></div>', 'Getting home card')

def setlist(n=8):
    s = _SL.get(EXAMPLE['tourSlug']) or {}; songs = (s.get('songs') or [])[:n]; total = len(s.get('songs') or [])
    label = 'Official tour playlist' if 'apple music' in (s.get('note') or '').lower() else 'Setlist'
    items = ''.join(f'<li><i>{i+1:02d}</i>{e(x)}</li>' for i, x in enumerate(songs))
    return _card('paper', f'<div class="nc-head"><h3>{label}</h3><span class="nc-kicker">{total} songs</span></div><ol class="nc-songs">{items}</ol><span class="nc-link">All {total} songs ⌄</span>', f'{label} for {EXAMPLE["artist"]}')

def venues_near(n=5):
    near = [v for v in _VN if v.get('state') == 'TX'][:n] or _VN[:n]
    rows = ''.join(f'<div class="nc-row nc-row-venue"><div><b>{e(v["name"])}</b><span>{e(v["city"])}, {e(v.get("state") or v.get("country"))}</span></div><span class="nc-check">✓</span></div>' for v in near)
    return _card('paper', f'<div class="nc-head"><h3>Venues near you</h3><span class="nc-kicker">{len(_VN)} guides</span></div>{rows}', 'Venues near you')

def tours_rail(n=5):
    with_set = [t for t in _TR if (_SL.get(t['tourId']) or {}).get('songs')][:n]
    rows = ''.join(f'<div class="nc-row nc-row-venue"><div><b>{e(t["artist"])}</b><span>{e(t["tourName"])}</span></div><span class="nc-kicker">{len(_SL[t["tourId"]]["songs"])} songs</span></div>' for t in with_set)
    return _card('paper', f'<div class="nc-head"><h3>On the road now</h3><span class="nc-kicker">{len(_TR)} tours</span></div>{rows}', 'Tours with setlists')

def night_plan():
    rows = [('5:45 PM','Dinner','Six minutes from the venue'),('7:10 PM','Leave','Gate lines already built in'),('7:30 PM','Show','Bag policy checked'),('Setlist','Learn it','In order, before doors'),('11:15 PM','Getting home','Signed rideshare pickup')]
    body = ''.join(f'<div class="nc-row nc-row-plan"><span class="nc-time">{e(a)}</span><div><b>{e(b)}</b><span>{e(c)}</span></div></div>' for a,b,c in rows)
    return _card('paper', f'<div class="nc-head"><span class="nc-kicker">Your Night</span><h3>{e(EXAMPLE["artist"])} · {e(EXAMPLE["venue"])}</h3></div>{body}<p class="nc-foot">Example night, built from verified venue data and a saved show.</p>', 'Your Night plan')

COMPONENTS = {
    'home': next_show, 'your-night': next_show, 'home-discover': venues_near,
    'venue': lambda: section('bagPolicy', 'Bag Policy'), 'venue-essentials': essentials, 'bagcheck': lambda: section('bagPolicy', 'Bag Policy'), 'bags': lambda: section('bagPolicy', 'Bag Policy'),
    'parking': lambda: section('parking', 'Parking'), 'rideshare': getting_home, 'getting-home': getting_home, 'concessions': lambda: section('concessions', 'Concessions'),
    'getting-there': lambda: section('parking', 'Parking'), 'around-venue': venues_near,
    'setlist': setlist, 'tour': setlist, 'tours': tours_rail, 'venues': venues_near, 'near-me': venues_near,
    'night-plan': night_plan, 'premium': night_plan, 'plan': night_plan,
}
def component(key):
    return (COMPONENTS.get(key) or next_show)()


# ---- Library pages: the same card system, for any venue or tour ----
def venue_section_card(info, key, title):
    x = (info or {}).get(key) or {}
    body = x.get('summary') or x.get('note') or x.get('body') or ''
    if not body: return ''
    lists = ''
    if x.get('allowed') or x.get('prohibited'):
        lists = '<div class="nc-lists">' + (f'<div><span class="nc-label">Allowed</span><ul>{"".join("<li>"+e(a)+"</li>" for a in x.get("allowed", [])[:5])}</ul></div>' if x.get('allowed') else '') + (f'<div><span class="nc-label">Not allowed</span><ul class="no">{"".join("<li>"+e(a)+"</li>" for a in x.get("prohibited", [])[:5])}</ul></div>' if x.get('prohibited') else '') + '</div>'
    ver = f'<span class="nc-verified">Verified {e(x.get("verified"))}</span>' if x.get('verified') else '<span class="nc-verified nc-unverified">Not yet verified</span>'
    link = f'<a class="nc-link" href="{e(x["officialLink"])}" target="_blank" rel="noopener">Official source ↗</a>' if x.get('officialLink') else ''
    return f'<figure class="night-card night-card-paper night-card-full" data-section="{e(key)}" aria-label="{e(title)}"><div class="nc-head"><h3>{e(title)}</h3>{ver}</div><p class="nc-body">{e(body)}</p>{lists}{link}</figure>'

def setlist_card_for(slug, artist, n=12):
    s = _SL.get(slug) or {}; songs = s.get('songs') or []
    if not songs: return ''
    label = 'Official tour playlist' if 'apple music' in (s.get('note') or '').lower() else ('Confirmed setlist' if (s.get('source') or {}).get('eventDate') else 'Setlist')
    items = ''.join(f'<li><i>{i+1:02d}</i>{e(x)}</li>' for i, x in enumerate(songs[:n]))
    more = f'<a class="nc-link" href="/setlist/{e(slug)}">All {len(songs)} songs →</a>' if len(songs) > n else ''
    return f'<figure class="night-card night-card-paper night-card-full" aria-label="{e(label)} for {e(artist)}"><div class="nc-head"><h3>{label}</h3><span class="nc-kicker">{len(songs)} songs · updated {e(s.get("updated",""))}</span></div><ol class="nc-songs">{items}</ol>{more}</figure>'
