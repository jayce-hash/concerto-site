"""Quick answers for a venue: the questions fans ask before they go, answered only when the
venue guide states the answer plainly. Nothing here is guessed: a fact that cannot be read
with confidence from the guide text is left out, and every answer links to its full section.

Rules that keep it honest (each one came from an independent review against the guide text):
- A policy written for sports events, or published by a team, keeps its scope: only the bag
  sentence (which names the scope) is shown, never an unscoped yes or no.
- A guide that says its own sources conflict, or that the event has no current policy, shows
  only its bag sentence.
- "Clear bag required" counts a clutch exception as clear-required for anything larger, never
  as "not required".
- Bag check means a place to leave a bag (bag check, bag drop, lockers, cloakroom), never a
  seasonal coat check or merch check. Both "yes" and "no" in the same guide means no answer.
- Words like "most events" or "generally" soften a re-entry answer instead of being dropped.

Used by site_v8.py for the venue page, and written into data/venue_info/<slug>.json
(field "glance") so the app shows the same answers."""
import re

def _t(sec):
    if not isinstance(sec, dict): return ''
    parts = [sec.get('summary') or '', sec.get('body') or '', sec.get('note') or '']
    return ' '.join(' '.join(parts).split())

def _lists(sec):
    if not isinstance(sec, dict): return [], []
    return [str(x) for x in (sec.get('allowed') or [])], [str(x) for x in (sec.get('prohibited') or [])]

def _sents(t):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', (t or '').strip()) if s.strip()]

def _first(t):
    s = _sents(t)
    return s[0] if s else ''

NOT_STATED = re.compile(r"not (explicitly |specifically )?(detailed|confirmed|stated|published|specified|listed)|does not (state|specify|publish)|no current bag policy|not scheduled|not being held|is off in|varies by (event|show)|vary by (event|show)|set by the (tour )?promoter|event-specific", re.I)
DIM = re.compile(r'(\d+(?:\.\d+)?\s*(?:"|”|″|in\b|inches|cm)?\s*[x×X]\s*\d+(?:\.\d+)?|\bA[34]\b|\d+\s*(?:litres|liters|L)\b)')
BOILER = re.compile(r'encourag|to ensure|to enhance|to expedite|for the safety|safety and security|enforces a (strict |clear )?bag policy\b(?![^.]*\d)|has implemented', re.I)
SCOPED = re.compile(r"\b(athletics?|athletic events|game ?days?|games\b|for (sports|football|basketball|baseball|hockey)|nfl|wnba|nba|mlb|nhl|home team|published by the|posted policy for|written for|team's|ballpark policy|general ballpark)\b", re.I)
CONFLICT = re.compile(r'contradict|conflicting|mixes answers|inconsistent', re.I)

def bag_answer(sec):
    """The sentence a fan needs: the first one that states a size, else the first real rule.
    A bare ban ("strict no bag policy") keeps its exceptions from the next sentence."""
    t = ' '.join(((sec or {}).get('summary') or (sec or {}).get('body') or (sec or {}).get('note') or '').split())
    sents = _sents(t)
    if not sents: return None
    if NOT_STATED.search(sents[0]) and not DIM.search(t): return sents[0].rstrip('.') if len(sents[0]) <= 160 else None
    for i, s in enumerate(sents[:3]):
        if DIM.search(s) and len(s) <= 170:
            # "Bags must be clear ... 12x6x12." followed by "Clutches up to 6x9 need not be clear."
            nxt = sents[i + 1] if i + 1 < len(sents) else ''
            if (re.search(r'must be clear|only clear', s, re.I) and re.search(r'clutch|wristlet|fanny|non-clear|need not|do not (need|have) to', nxt, re.I)
                    or re.search(r'encourag', s, re.I) and re.search(r'prohibited|not (allowed|permitted)|banned', nxt, re.I)) and len(s) + len(nxt) <= 240:
                return (s.rstrip('.') + '. ' + nxt).rstrip('.')
            return s.rstrip('.')
    real = [s for s in sents[:3] if not BOILER.search(s)] or sents[:1]
    s = real[0]
    idx = sents.index(s)
    nxt = sents[idx + 1] if idx + 1 < len(sents) else ''
    if re.search(r'\bno bags?\b|no-bag|not allowed|prohibited|banned', s, re.I) and re.search(r'clutch|except|allowed|permitted|medical|parenting|diaper', nxt, re.I) and len(s) + len(nxt) <= 240:
        s = s.rstrip('.') + '. ' + nxt
    s = s.rstrip('.')
    return s if len(s) <= 240 else None

def _scoped(sec):
    return bool(SCOPED.search(_t(sec)))

def clear_bag(sec):
    t = _t(sec); a, p = _lists(sec)
    if not t: return None
    low = t.lower(); allowed = ' | '.join(a).lower(); prohibited = ' | '.join(p).lower()
    everything = low + ' || ' + allowed + ' || ' + prohibited
    clutch_ok = re.search(r'clutch|wristlet|fanny|small (non-clear )?(bag|purse)|non-clear|wallet', everything)
    required = (re.search(r"(must be|only|all bags must be) clear|clear bag polic|clear bags? only|only clear|clear[- ]bag venue|requires bags to be clear|non-clear bags?[^.|]{0,40}(prohibited|not (allowed|permitted))|(any|all) (type of )?non-clear bags?", everything)
                or (re.search(r'allows? (only )?clear (plastic )?(tote )?bags? up to', low) and clutch_ok))
    small_ok = any(re.search(r'clutch|wristlet|purse|wallet|fanny', x.lower()) and DIM.search(x) for x in a)
    other_bags = any(re.search(r'\b(bags?|purses?|backpacks?|totes?|handbags?)\b', x.lower()) and 'clear' not in x.lower()
                     and not re.match(r'\s*(one |a )?(small|clutch|wristlet|wallet|fanny|diaper|medical|parenting|one[- ]gallon|gallon|ziploc|freezer)', x.lower()) for x in a)
    if not required and not other_bags and 'clear' in low and any('clear' in x.lower() and 'bag' in x.lower() for x in a) and small_ok:
        required = True  # a clear bag plus a small clutch is the whole allowance: anything larger must be clear
    not_required = re.search(r"clear bags? (is|are) not required|no clear[- ]bag (policy|requirement)|not a clear[- ]bag (venue|policy)|(?<!medical )(?<!diaper )(?<!parenting )(bags|purses|bags and purses)[^.]{0,40}(do not|don't|need not) (need to |have to )?be clear", low)
    if not_required and re.search(r'(medical|diaper|parenting)[^.]{0,20}$', low[:not_required.start()]): not_required = None
    if required and not_required:
        return None
    # Soft wording ("clear bags are encouraged") or a hydration-pack exception is not a yes or no.
    if re.search(r'clear[^.]{0,60}encourag|encourag[^.]{0,60}clear|hydration|camelbak', everything):
        return None
    if required:
        return 'Yes, for anything larger than a small clutch' if clutch_ok else 'Yes'
    if not_required and not re.search(r'clutch|fanny|wristlet', not_required.group(0)):
        return 'Not required'
    return None

def backpacks(sec):
    t = _t(sec); a, p = _lists(sec)
    low = t.lower(); allowed = ' | '.join(a).lower(); prohibited = ' | '.join(p).lower()
    both = low + ' || ' + prohibited
    if re.search(r'hydration|camelbak', both + allowed):
        return None
    if re.search(r'clear backpacks?', allowed + ' ' + low) and re.search(r"only clear|must be clear|clear bag polic|non-clear (bags?|backpacks?)[^.|]{0,40}(prohibited|not)", both) \
       and not re.search(r'including clear backpacks|clear backpacks? (are |is )?(not|prohibited)', both):
        return 'Clear backpacks only'
    explicit = (re.search(r'(back|ruck)packs? of any (size|kind|type)|\bno (back|ruck)packs\b|(back|ruck)packs? (are |is )?(not (allowed|permitted)|prohibited|banned|never allowed)|(back|ruck)packs?, including clear', both)
                or any(re.fullmatch(r'\s*(all )?(back|ruck)packs?( \([^)]*\))?( of any (size|kind|type))?\s*', x) for x in prohibited.split(' | ')))
    qualified = (re.search(r'(large|larger|oversized|full[- ]size[d]?|camping|hiking|big)\s+(\w+\s+)?(back|ruck)packs?', both)
                 or re.search(r'(back|ruck)packs?( and| or)? (bags? )?(larger|bigger|exceeding|over \d|with dimensions|than)', both)
                 or re.search(r'(bags?|purses?),? (or|and) (back|ruck)packs?[^.;|]{0,40}(may not exceed|up to|no larger|must|allowed)', both))
    if explicit and not (qualified and not re.search(r'of any (size|kind|type)|\bno (back|ruck)packs', both)):
        return 'Not allowed'
    return None

def re_entry(sec):
    t = _t(sec)
    first = _first(t).lower()
    if not first or NOT_STATED.search(first): return None
    if _scoped(sec) or SPORTS.search(first): return None
    soft = re.search(r'\b(most|generally|typically|usually|in most cases)\b', first)
    if re.search(r'\bno re-?entry\b|re-?entry (is |are )?(not|never) (permitted|allowed)|(not|never) (permitted|allowed)|does not permit re-?entry|exit (is|are) final|voids? (your|the) ticket|cannot (re-?enter|return)|may not (re-?enter|return)|no in-and-out|no in and out', first) and re.search(r're-?ent|return|exit|leave|in-and-out|in and out', first):
        return 'Usually not. Check your event' if soft else 'No'
    if re.search(r're-?entry (is )?(generally )?(permitted|allowed)|permits re-?entry', first) and not re.search(r'\bnot\b', first):
        return 'Allowed, with conditions'
    return None

def bag_check(bag, gates):
    t = (_t(bag) + ' ' + _t(gates))
    low = t.lower()
    place = r'(bag check|bag drop|bag storage|lockers?|left luggage|binbox)'  # a cloakroom is for coats; often small bags only
    no = re.search(r'no (bag )?(check|storage|lockers|left luggage)|no bag or coat check|not (offer|provide)[^.]{0,30}' + place + r'|cannot (hold|store)|staff cannot hold|no storage area|prohibited (bags|items) cannot be stored', low)
    if no and re.search(r'(is|are) (described|listed|mentioned)', low[no.start():no.end() + 25]): no = None
    yes = None; cands = []
    for s in _sents(t):
        ls = s.lower()
        if re.search(r'coat check|merch check|cloakroom', ls) and not re.search(r'bag check|bag drop|lockers?|left luggage', ls): continue
        if re.search(r'\bonly\b[^.]{0,40}(academy|room|hall|level|stage)', ls): continue  # priced for one part of the venue only
        if re.search(place + r'[^.]{0,80}((?:\$|€|£)\s?\d+(?:\.\d{2})?|\d+(?:[.,]\d{2})?\s?(?:euros?|eur))', ls) or re.search(r'checked for|' + place + r'[^.]{0,40}(available|offered|provided|on site|is just|costs?)|(available|offered|rent)[^.]{0,30}' + place, ls):
            cands.append(s)
    # A place for bags beats a cloakroom for coats.
    cands.sort(key=lambda x: 0 if re.search(r'bag (check|drop|storage)|lockers?|binbox|left luggage', x, re.I) else 1)
    yes = cands[0] if cands else None
    if yes and no: return None
    if no: return 'Not available'
    if yes:
        prices = re.findall(r'((?:\$|€|£)\s?\d+(?:\.\d{2})?|\d+(?:[.,]\d{2})?\s?(?:euros?|EUR))', yes, re.I)
        return f"Available ({prices[0].strip()})" if len(prices) == 1 else 'Available'
    return None

SPORTS = re.compile(r'game|tip-?off|kickoff|first pitch|puck|basketball|football|baseball|hockey|athletic|wrestling|volleyball|match|raiders|cubs|kings|senators|monsters', re.I)
def doors(gates):
    t = _t(gates)
    if not t or NOT_STATED.search(_first(t)): return None
    for sent in _sents(t):
        if SPORTS.search(sent) or re.search(r'box office|lobb|member gate|parking|described on the linked page', sent, re.I): continue
        m = re.search(r'\b(?:doors|gates)\b[^.]{0,40}?\bopen\w*\b[^.]{0,25}?\b((?:about |approximately |at least )?(?:\d+(?:\.\d+)?|one|two|three)(?:\s*(?:to|or|–|-)\s*(?:\d+|one|two|three))?\s*(?:hours?|hrs?|minutes|mins?))\s*(?:before|prior to)\s*(?:the\s+)?(?:scheduled\s+|posted\s+|listed\s+)?(show|showtime|performance|event|concert|start|time)', sent, re.I)
        if m: return "Usually " + re.sub(r"^approximately ", "about ", m.group(1)) + " before showtime"
    return None

def glance(rec):
    rec = rec or {}
    bag = rec.get('bagPolicy') or {}
    out = []
    def add(key, label, value, anchor):
        if value: out.append({'key': key, 'label': label, 'value': value, 'anchor': anchor})
    bt = _t(bag)
    line = bag_answer(bag)
    if line and _scoped(bag) and not SCOPED.search(line):
        line += ' (posted for sports events; concerts may differ)'
    add('bag', 'Bags', line, 'bag-policy')
    limited = (not bt) or NOT_STATED.search(_first(bt)) or _scoped(bag) or CONFLICT.search(bt)
    if not limited:
        add('clear', 'Clear bag required', clear_bag(bag), 'bag-policy')
        add('backpacks', 'Backpacks', backpacks(bag), 'bag-policy')
        add('bagcheck', 'Bag check', bag_check(bag, rec.get('gates')), 'bag-policy')
    add('reentry', 'Re-entry', re_entry(rec.get('reEntry')), 're-entry')
    add('doors', 'Doors', doors(rec.get('gates')), 'entrances')
    return out
