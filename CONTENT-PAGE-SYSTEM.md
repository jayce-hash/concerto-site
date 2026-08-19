# Concerto Content Page System

The shared visual and structural language for Concerto's standalone
content pages: About, FAQ, Partners, Investors, Premium.

**This is not a new system.** `partners.html` already had most of it,
built during the V2 pass and never carried across to the other pages.
That is the actual problem: About, FAQ, and Premium use an older,
flatter vocabulary (`page-title`, no section kickers, no rules, no
monospace accent) while Partners uses a genuinely editorial one. The
job is bringing the rest up to Partners, not inventing something else.

## What counts as a content page

In scope: **About, FAQ, Partners, Investors, Premium.** These are the
pages someone reads while deciding whether to take Concerto
seriously. They should feel like a real company wrote them.

Out of scope, on purpose:
- **App-mirrored pages** (Home, Venues, Tours, Near Me, Account,
  Settings, Bag Check, Plan Night, Search, Login, Signup). These
  should look like the app, because they are the app. Making them
  editorial would break consistency with the actual product.
- **SEO hub pages** (Bags, Concessions, Parking, Rideshare). Not
  featured anywhere in the app, doing quiet search work. Leave them.
- **Legal** (Privacy, Terms). Plain and scannable is the correct
  register for these; polish works against their job.
- **Top Picks.** Already app-ified and data-driven rather than
  narrative. Revisit after the five above land.

## The type scale

```css
--display: 'Playfair Display', Georgia, serif;   /* headlines */
--body: 'DM Sans', -apple-system, sans-serif;    /* body */
'DM Mono', ui-monospace, monospace;              /* kickers, timestamps, tags */
```

DM Mono is the piece most pages are missing. It carries every
section kicker, every small label, every "01 / 02 / 03" step marker.
It is what makes a page read as documented rather than decorated.

```css
.h1  { font-size: clamp(2.1rem, 5vw, 3.4rem); max-width: 18ch; }
.h2  { font-size: clamp(1.7rem, 3.2vw, 2.5rem); max-width: 20ch; }
.p   { font-size: 1rem; line-height: 1.85; max-width: 58ch; }
```

Every headline gets `letter-spacing: -.025em`, `line-height: 1.12`,
and `text-wrap: balance`. Every paragraph gets `text-wrap: pretty`.
The `max-width` values in `ch` are doing real work: they cap line
length so a headline breaks where it should on any screen, rather
than running to the edge on desktop.

## The section pattern

Every content section follows the same shape:

```html
<section class="sec rv"><div class="pg">
  <p class="sec-k">The mechanic</p>
  <h2 class="h2">Headline goes here.</h2>
  <p class="p">Body copy.</p>
</div></section>
<div class="pg"><div class="rule"></div></div>
```

- `.sec-k` is the monospace kicker: gold, uppercase, `.26em` letter
  spacing. Names what the section is about in two or three words
  ("The mechanic," "The inventory," "Straight answers"). Not a
  heading, a label.
- `.rule` is a one-pixel line between sections. Not decoration:
  it is what makes a long page feel like a document with parts
  rather than an undifferentiated scroll.
- `.sec` uses `padding: clamp(48px, 7vw, 84px) 0` so vertical rhythm
  scales with the viewport instead of sitting at one fixed value.

Numbered kickers ("01 / The problem") are a legitimate variant when a
page has a genuine sequence, as the investors page does. Do not number
sections that have no real order.

## The proof strip

Where a page has real numbers, they get their own strip rather than
being buried in prose:

```
300+   venues        Researched, verified, and dated
80+    live tours    Setlists and show information tracked
1      founder       Product, research, and operations
```

Rules: the number in Playfair, the label in DM Sans, the detail line
in `--ink-faint`. Rounded counts only ("300+", never "346"). Never
invent a stat to fill the third slot; two real numbers beat three
where one is padding.

## Buttons

```css
.b        /* pill, .85rem/1.65rem padding, 700 weight */
.b-gold   /* gold fill, navy text, soft gold shadow. One per page. */
.b-dark   /* navy fill, cream text. Secondary. */
.b-ghost  /* line border, ink text. Tertiary. */
```

One gold button per page, on the single action that matters most.
A page with three gold buttons has no primary action.

## Voice

- **No em-dashes.** Anywhere. This is the rule most easily broken by
  pasting copy from elsewhere, and three SEO hub pages currently
  violate it.
- **Title Case headlines.** Sentence case reads as a different brand.
- **Rounded counts** in all copy: "300+ venues," "80+ tours."
- Calm, specific, confident. Concrete beats clever: "verified and
  dated" says more than "trusted."
- Reference points: Apple, Oura, Bevel Health. Editorial restraint,
  not conventional marketing-site energy.

## What to avoid

Gradients without purpose, glowing blobs, fake 3D, oversized logos,
stock photography, more than one dominant visual per section, filling
negative space because it looks empty. Negative space is the point.

## Current state, page by page

| Page | Uses the system? | What it needs |
|---|---|---|
| Partners | Yes | Nothing structural. Reference implementation. |
| Investors | Partly | Written in the right voice, needs the section vocabulary. |
| About | No | Full pass. Uses `page-title`, no kickers, no rules. |
| Premium | No | Full pass. Highest business value: this is the paywall page. |
| FAQ | No | Full pass. Content is accurate as of Aug 17, structure is flat. |
