# Madison Square Garden, read from msg.com on 2026-11-02 (Claude in Chrome).
# Positions are the centers of MSG's own seat-map elements (concert configuration),
# in thousandths of the map's width and height (map box 853 x 632 px).
SEATMAP = 'https://www.msg.com/madison-square-garden/seating/msg-concerts'
FOOD = 'https://www.msg.com/madison-square-garden/food-drink'
FAQ = 'https://www.msg.com/madison-square-garden/faqs'
ACCESS = 'https://www.msg.com/madison-square-garden/accessibility-services'
ENTRANCES = 'https://www.msg.com/madison-square-garden/entrances'
CHECKED = '2026-11-02'

MAIN = """211:498,163 212:434,160 210:562,160 209:625,181 213:371,178 208:678,211 214:320,222 216:235,362 217:211,448 218:211,546 219:235,632 227:680,784 221:320,784 226:625,817 222:370,817 223:434,843 225:562,834 224:498,838 207:717,293 201:717,701 203:770,599 202:753,646 206:753,348 220:280,715 204:791,497 215:285,259 109:381,335 110:330,355 105:612,340 103:697,416 111:292,410 113:292,584 112:278,497 102:717,497 114:330,639 120:665,639 115:381,666 119:615,665 118:554,683 116:442,683 117:498,692 104:665,356 101:697,579 106:554,300 108:443,300 107:498,294 3:628,440 2:630,497 1:628,554 F:550,434 E:550,497 D:550,560 C:464,434 B:461,497 A:464,560 420:258,761 419:232,707 418:206,627 417:192,542 416:192,452 415:206,367 414:232,287 413:258,233 421:275,793"""
STAGE = (378, 497)

BRIDGE = """328:676,734 327:614,739 326:501,742 325:387,740 324:323,736 323:287,714 322:258,656 321:236,577 320:228,498 319:236,416 318:258,341 317:286,284 316:319,260 315:374,256 314:437,253 313:500,252 312:563,253 311:625,256 310:680,261 309:713,284 308:738,331 307:756,383 306:764,441 305:768,499 304:764,558 303:756,615 302:737,668 301:712,714"""
BRIDGE_POI = "restroom:205,575"

# Official amenity icons. Level 2 on MSG's map = the 100 Level (Kalshi Concourse); level 4 = the 200 Level (Pepsi Concourse).
POI_100 = "m:337,296 m:529,744 m:650,289 w:417,735 w:716,644 w:751,436 w:573,258 w:473,251 retail:312,315 retail:276,637 retail:676,687 retail:748,420 elevator:410,261 elevator:660,296"
POI_200 = "m:350,210 m:349,785 m:467,819 m:647,786 m:706,246 m:529,176 w:466,177 w:404,188 w:404,807 w:529,818 w:591,806 w:647,208 w:591,188 retail:372,102 retail:368,890"
POI_ALL = "escalator:747,161 escalator:252,161 escalator:252,834 escalator:749,834 elevator:294,143 elevator:826,304 elevator:826,690"

# msg.com/madison-square-garden/food-drink, as listed.
STANDS_100 = {  # 100 Level | Kalshi Concourse
 '101': 'Courtside/Rinkside Bar', '102': 'Craft Beer Garden', '103': 'Mixed Drinks', '104': 'Garden Market',
 '105': 'Mighty Quinn’s Barbeque, Carnegie Deli, Bar at the Garden', '106': 'Daily Burger', '107': 'Rafters Bar, Pat LaFrieda',
 '108': 'Monster Energy Bodega, Brooklyn Dumpling Shop', '109': 'Chicken & Things, Veselka', '110': 'Draft Beer, Beverage Grab & Go, Ice Cream',
 '111': 'Chickies, Garden Market Express', '112': 'Farley’s Bar, Garden Market, Gluten-Free at The Garden, TopDog, Luchini Italian Sandwich Shop, Avenue Cantina',
 '114': 'Mixed Drinks, Garden Market & Drinks, Shah’s Halal', '115': 'Garden Market, Dunkin’ Donuts, Mike’s Hot Honey', '116': 'Daily Burger, Simply Vegan',
 '117': 'Paulie Gee’s Pizza', '118': 'TAO Sushi, Rock N’ Lobster', '119': 'Bar at the Garden, Fuku', '120': 'Eats, Popcorn & Drinks, Insomnia Cookies'}
STANDS_200 = {  # 200 Level | Pepsi Concourse
 '201': 'Garden Market', '202': 'Dunkin’ Donuts', '203': 'Prime Rib, Pat LaFrieda', '204': 'Chicken & Things, Bar at the Garden, Mighty Quinn’s Barbeque',
 '206': 'Bar at the Garden', '207': 'Garden Market', '209': 'Garden Pub', '210': 'SeoulBird Korean BBQ, Daily Burger, Draft Beer', '211': 'The Trophy Bar',
 '212': 'Draft Beer, Garden Market', '213': 'Popcorn & Drinks', '215': 'Mixed Drinks', '216-218': 'Garden Market, Garden Melt', '219': 'Carnegie Deli',
 '220-221': 'Mixed Drinks', '223': 'Draft Beer', '224': 'Paulie Gee’s Pizza, Draft Beer, 7th Street Burger', '225': 'Garden Market Express, Draft Beer',
 '226': 'Garden Pub', '227': 'Mixed Drinks, Ice Cream, Bud Light'}
STANDS_400 = {'416,417,419': 'Garden Market'}  # Blue Seats
STANDS_BRIDGE = {'304': 'Chicken & Things, Veselka', '305': 'Bar at the Garden, Daily Burger, Chicken & Things', '319': 'Garden Melt'}
# Not placed: "Bridge Bar" (Hyundai Bridge, West Balcony, Column 37): no section given.
