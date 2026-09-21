"""Company and partner pages: one product, specific benefits, no audience promises."""
import html
from pathlib import Path
from public_chrome import page_end, APP

ROOT = Path(__file__).resolve().parent.parent
def e(value): return html.escape(str(value), quote=True)

TRACKS = {
 'restaurants': ('Restaurants & bars', 'Be part of their plans before the show.', 'Help fans choose a meal or a drink that fits the venue and the evening.', 'A concert menu, a reservation window, or a clearly defined dining benefit.', 'Introduce your business while fans are deciding where to eat. Agree on the venue, dates, placement, and action before launch.', 'Menu or reservation link', 'Dining area and nearby venues', 'Reservations, offer uses, or tracked visits to your booking page.'),
 'hotels': ('Hotels', 'Give fans a reason to stay for the night.', 'Make a concert trip easier with a stay that works for the venue and the date.', 'A concert rate, late checkout, or an included parking benefit with clear conditions.', 'Present a relevant stay to fans planning around nearby venues. Start with selected dates or one property, with scope agreed in advance.', 'Booking link or rate details', 'Property location and nearby venues', 'Tracked booking-link visits; bookings only where your reporting supports attribution.'),
 'venues': ('Venues', 'Help fans arrive informed.', 'Put your published guidance within reach of fans planning their visit.', 'Current entry rules, useful arrival information, or an optional parking or hospitality offer.', 'Improve the information fans find before arrival. Approved venue access supports guide updates and event timing; commercial placements are agreed separately.', 'Official venue website', 'Venue name and city', 'Guide visits and arrival-link activity where tracking is available.'),
 'artists': ('Artists & tours', 'Carry the connection beyond the ticket.', 'Give fans useful information and a reason to engage around your tour dates.', 'Confirmed tour information, a merch benefit, or an authorized fan-access offer.', 'Connect a benefit to your tour or selected venues. Work with Concerto on the relevant dates, source material, and fan action.', 'Official artist or tour website', 'Artist, tour, and relevant markets', 'Tour-page activity and tracked offer-link visits where available.'),
}

def intro(kicker, title, description, action='', href=''):
    cta = f'<a class="btn-primary" href="{href}">{action} ↗</a>' if action else ''
    return f'<section class="type-hero company-hero"><div class="site-shell"><p class="eyebrow">{kicker}</p><h1>{title}</h1><div class="hero-bottom"><p>{description}</p>{cta}</div></div></section>'

def section(kicker, title, body):
    return f'<section class="section"><div class="site-shell editorial-grid"><div><p class="eyebrow">{kicker}</p><h2>{title}</h2></div><div class="company-copy">{body}</div></div></section>'

def wrap(head, slug, title, description, body):
    route = '/partners/' + slug[len('partner-'):] if slug.startswith('partner-') else '/' + slug
    return head(title + ' | Concerto', description, route) + f'<main class="company-page page-{slug}">' + body + '</main>' + page_end()

def process():
    return section('Working together', 'A clear path to launch.', '<ol class="night-sequence"><li><h3>1. Tell us the fit.</h3><p>Share your business, audience, location or tour, and an initial idea. An inquiry is not a commitment.</p></li><li><h3>2. Agree on the details.</h3><p>We review the fan benefit, dates, placements, responsibilities, pricing if applicable, and what can be measured.</p></li><li><h3>3. Prepare and review.</h3><p>Provide the approved copy, links, eligibility, and redemption instructions. The Partner Console lets you prepare an offer; publication follows review.</p></li><li><h3>4. Launch and learn.</h3><p>Activate the agreed placement, keep the offer current, and review available results. Reach, bookings, and sales are not guaranteed.</p></li></ol>')

def partner_form(slug):
    label, _, _, _, _, link_label, market_label, _ = TRACKS[slug]
    return f'''<section class="section" id="interest"><div class="site-shell editorial-grid"><div><p class="eyebrow">Start a conversation</p><h2>Tell us what<br>you have in mind.</h2><p>No finished proposal is required. We will review the fit and follow up if more information is needed.</p><p>Already approved? <a class="text-link" href="/console/">Open the Partner Console →</a></p></div>
<form action="/partners-thank-you" class="partner-form" data-netlify="true" method="POST" name="partner-{slug}-interest" netlify-honeypot="bot-field">
<input name="form-name" type="hidden" value="partner-{slug}-interest"><input name="partner_type" type="hidden" value="{e(label)}"><p class="hidden-field"><label>Leave blank <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>
<div class="form-grid"><label class="field"><span>Organization *</span><input name="organization" autocomplete="organization" required maxlength="160"></label><label class="field"><span>Your name *</span><input name="contact_name" autocomplete="name" required maxlength="100"></label><label class="field"><span>Email *</span><input name="email" autocomplete="email" type="email" required></label><label class="field"><span>{e(link_label)}</span><input name="website" type="url" placeholder="https://"></label><label class="field full"><span>{e(market_label)} *</span><input name="market" required maxlength="240"></label><label class="field full"><span>What would you like to explore? *</span><textarea name="notes" rows="4" required maxlength="2000" placeholder="Your idea, timing, and what would make it worthwhile."></textarea></label></div>
<label class="consent"><input name="agreement" type="checkbox" required><span>I understand this is an inquiry, not a confirmed partnership or placement.</span></label><button class="btn-primary" type="submit">Send partnership inquiry</button><p class="form-note">Please do not include confidential account details. See our <a href="/privacy">Privacy Policy</a>.</p></form></div></section>'''

def build_company_pages(head):
    rows = ''.join(f'<a class="partner-track" href="/partners/{slug}"><span class="eyebrow">{e(v[0])}</span><h3>{v[1]}</h3><p>{v[2]}</p><span class="text-link">Explore the fit →</span></a>' for slug, v in TRACKS.items())
    body = intro('Concerto Partners', 'A better concert night.<br>A useful place in it.', 'Connect your business or tour with the decisions fans make around a show. Start with something useful for them and a clear objective for you.')
    body += f'<section class="section"><div class="site-shell partner-tracks">{rows}</div></section>' + process()
    body += section('What a partnership means', 'Specific scope.<br>Shared expectations.', '<p>Concerto is a founder-led business building its partner program. Opportunities can include relevant app or website placements and agreed content collaborations. Availability, fees, duration, and reporting are discussed for each opportunity.</p><p>A Perk is a redeemable fan benefit. A sponsored placement is paid visibility. Venue information is useful guidance. We keep those distinctions clear.</p><a class="text-link" href="/perks">How Concerto Perks work →</a>')
    (ROOT/'partners.html').write_text(wrap(head,'partners','Concerto Partners','Partnerships for restaurants, hotels, venues, and artists around concert nights.',body))
    for slug, v in TRACKS.items():
        label,title,desc,benefit,value,_,_,measure = v
        body = intro(label,title,desc,'Discuss a partnership','#interest')
        body += section('The opportunity','Useful for fans.<br>Relevant to you.',f'<h3>What fans receive</h3><p>{benefit}</p><h3>What you can explore</h3><p>{value}</p><h3>What success can mean</h3><p>{measure} Confirm measurement capabilities before launch; clicks are not confirmed purchases.</p>')
        body += process() + partner_form(slug)
        (ROOT/f'partner-{slug}.html').write_text(wrap(head,'partner-'+slug,label+' partnerships',desc,body))
        form = '<form' + partner_form(slug).split('<form',1)[1].split('</form>',1)[0] + '</form>'
        (ROOT/'scripts/forms'/f'{slug}.html').write_text(form)
    body = intro('Concerto Perks','Something extra<br>for your night.', 'Benefits from Concerto Partners, with the details you need to use them. Availability depends on the venue, tour, and dates.')
    body += '<section class="section"><div class="site-shell"><h2>Available Perks</h2><div data-live-perks aria-live="polite"><p>Loading current partner benefits…</p></div><noscript><p>Enable JavaScript to check current availability, or open Concerto.</p></noscript></div></section>'
    body += section('Before you use one','Know what is included.', '<p>Read the offer’s redemption instructions, dates, eligibility, and restrictions. Some benefits require a reservation, booking, purchase, or code.</p><p>Concerto Partner identifies a business relationship. Paid placements are labeled sponsored; a nearby recommendation by itself is not a Perk. Each offer states any membership requirement.</p><a class="text-link" href="'+APP+'">Find your night in Concerto →</a>')
    (ROOT/'perks.html').write_text(wrap(head,'perks','Concerto Perks','Current partner benefits, eligibility, dates, and redemption details for concert fans.',body))
    body = intro('Investors','A focused product.<br>A practical next step.', 'Concerto helps concert fans prepare for the night around their ticket. We welcome conversations with people who understand live music, hospitality, and building a useful consumer business.', 'Contact the founder','/contact?topic=investor')
    body += section('The company today','Built around<br>one fan experience.', '<p>Founded by Jayce Wells in Dallas–Fort Worth, Concerto brings venue guidance, tour information, nearby discovery, and planning together around a saved show.</p><p>The app and website are built. Concerto+ is the paid planning offering; the partner program is an opportunity being developed. Product coverage is not a measure of active users or revenue.</p>')
    body += section('The conversation','Relevant experience<br>and introductions.', '<p>We are interested in thoughtful connections across venues, hospitality, artists, and consumer products. Current operating figures, priorities, and any proposed terms should be discussed directly rather than inferred from website traffic or content counts.</p>')
    (ROOT/'investors.html').write_text(wrap(head,'investors','Investors','A conversation about Concerto with founder Jayce Wells.',body))
    body = intro('Press & media','Concerto, in brief.', 'Concerto helps concert fans plan the night around their ticket.', 'Media inquiry','/contact?topic=media')
    body += section('Company background','One show.<br>The night around it.', '<p>Concerto is an iPhone app and website founded by Jayce Wells in Dallas–Fort Worth. Fans can save a show and find venue guidance, available tour setlists, nearby places, and transportation information. Concerto+ adds personalized planning.</p><p>Concerto is independent from artists, venues, teams, and promoters. Listed guides do not imply a partnership or endorsement.</p><p>For current screenshots, logo files, interviews, or confirmed company figures, please contact us. <a class="text-link" href="/about">Read the founder story →</a></p>')
    (ROOT/'press.html').write_text(wrap(head,'press','Press & Media','Company background and media inquiries for Concerto.',body))
    thanks = intro('Partnership inquiry received','Thank you for reaching out.', 'We have received your inquiry. Concerto will review the fit and contact you at the email you provided if there is a next step. This does not activate a partnership or publish an offer.', 'Back to Partners','/partners')
    (ROOT/'partners-thank-you.html').write_text(wrap(head,'partners-thank-you','Partnership inquiry received','Your Concerto partnership inquiry has been received.',thanks).replace('index,follow,max-image-preview:large','noindex,follow'))

def build_support_pages(head):
    body = intro('About Concerto','The ticket is the start<br>of the night.', 'Concerto brings the practical details around a concert into one place, so fans can spend less time piecing them together.')
    body += section('The founder','Jayce Wells.<br>Founder of Concerto.', '<p>Jayce founded Concerto in Dallas–Fort Worth around a straightforward problem: having a ticket does not mean having the rest of the night figured out.</p><p>The bag policy, parking, dinner, setlist, and ride home can each send a fan somewhere different. Concerto brings those questions back to the show they are going to.</p><p>It is a founder-led business with a focused aim: make preparing for a concert easier and the night around it more enjoyable.</p>')
    body += section('The product','Save the show.<br>Keep the details together.', '<p>Your Night is the home for a saved concert. Venue guidance, available setlists, nearby places, and transportation information stay connected to that show.</p><p>Essential information stays free. Concerto+ adds planning tools for fans who want help shaping the evening.</p><a class="text-link" href="/your-night">Explore Your Night →</a>')
    body += section('Our approach','Useful information.<br>Clear limits.', '<p>We prioritize official venue sources and show when information was checked. Missing information, estimates, and venue-confirmed details should be distinguishable.</p><p>Concerto is independent from artists and venues. A listing is not an endorsement, and a plan cannot guarantee entry, timing, or availability.</p>')
    (ROOT/'about.html').write_text(wrap(head,'about','About Concerto','Meet founder Jayce Wells and the concert-night problem behind Concerto.',body))
    body = intro('Creators','Help fans see<br>the whole night.', 'Bring a useful point of view to a concert, venue, or city. We welcome specific ideas from music, food, travel, and local creators.', 'Pitch a collaboration','/contact?topic=creator')
    body += section('Ideas worth discussing','A real night.<br>Your perspective.', '<p>A pre-show dining guide. An accessible venue walkthrough. A concert-weekend itinerary. A practical tip you wish you had known before arriving.</p><p>Tell us the audience, location or tour, proposed format, timing, and your rates or collaboration expectations. We agree on deliverables, usage rights, compensation, and disclosures before work begins.</p><p>An inquiry does not guarantee an invitation, paid project, tickets, or travel.</p>')
    (ROOT/'creators.html').write_text(wrap(head,'creators','Creator collaborations','Pitch useful concert-night content to Concerto.',body))
    form = (ROOT/'scripts/forms/contact.html').read_text()
    body = intro('Contact','Let’s get you<br>to the right place.', 'Questions about your concert experience, an idea for a collaboration, or a company inquiry? Start here.')
    body += '<section class="section"><div class="site-shell editorial-grid"><div class="company-copy"><h2>How can we help?</h2><p>For app support: <a href="mailto:support@concertocity.com">support@concertocity.com</a> or the <a href="/help">Help Center</a>.</p><p>For business partnerships: <a href="/partners">choose your partner category</a> or contact partnerships@concertocity.com.</p><p>For media, creator, investor, or general company inquiries, use this form.</p></div>'+form+'</div></section>'
    (ROOT/'contact.html').write_text(wrap(head,'contact','Contact Concerto','Contact Concerto for support, partnerships, media, and company inquiries.',body))
