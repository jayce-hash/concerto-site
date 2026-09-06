# Concerto Brand & Product Standards
Version 1.0 - September 2026

## Purpose
Concerto must feel like one established company across iOS, web, corporate pages, support, investor, partner, creator, press, and marketing surfaces. A surface may adapt to its platform. It may not invent a new Concerto.

## Brand constants
- Primary Navy: `#121E36`
- Gold: `#C9A84C`
- Light Background: `#F8F9F9`
- White: `#FFFFFF`
- Display Typeface: Playfair Display
- Functional Typeface: DM Sans
- Registered slogan: `From the Concert to the City®`

Gold is earned emphasis. Navy is a brand anchor, not a default card background. White space is part of the brand.

## Universal typography hierarchy
| Role | Typeface | Case | Weight | Intent |
| --- | --- | --- | --- | --- |
| Display Hero | Playfair Display | Title Case | 600-700 | Major marketing or emotional statement |
| Page Title | Playfair Display | Title Case | 600-700 | Primary screen/page identity |
| Editorial / Entity Title | Playfair Display | Title Case | 500-700 | Artist, venue, tour, branded feature moment |
| Functional Section Title | DM Sans | Title Case | 700 | Venue Essentials, Getting There, Featured Tours |
| Card / Row Title | DM Sans | Title Case | 600 | Parking, Bag Policy, restaurant, utility cards |
| Eyebrow / Status | DM Sans | ALL CAPS | 700 | YOUR NEXT SHOW, VERIFIED, CONCERTO+ |
| Button / Action | DM Sans | Title Case | 600-700 | View Your Night, Save Show |
| Body | DM Sans | Sentence case | 400 | Descriptions and explanatory copy |
| Metadata | DM Sans | Sentence case | 500 | Date, venue, distance, time |
| Navigation | DM Sans | Title Case | 500-600 | Tabs, web nav, menus |

### Typography hard rules
1. ALL CAPS is reserved for eyebrows, status, and compact category labels.
2. Page titles are never DM Sans ALL CAPS.
3. Playfair is never used for buttons, tabs, form labels, filters, or utility metadata.
4. DM Sans does not replace the editorial headline layer merely to look more native.
5. The same semantic role receives the same treatment everywhere.

## Spacing
Use only the shared scale: `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96`.
- iOS page gutter: 20pt
- Standard card padding: 20-24pt
- Functional section gap: 32-48pt
- Marketing section gap: 64-96px

Do not introduce one-off spacing values without a documented platform requirement.

## Radius
- Small controls and chips: 10-12
- Standard cards: 16
- Hero / premium cards: 20
- Pills: only status, filter, or true pill controls
- Native sheets/modals: use platform-native presentation where possible

## Color behavior
- Gold: premium emphasis, selected states, verified accents, restrained brand detail.
- Navy: brand anchors, hero moments, footer/header surfaces, major premium moments.
- Do not use gold for paragraphs or arbitrary headings.
- Do not make every card navy.
- Contrast must remain readable in light/dark themes and web states.

## Platform expression
### iOS
Prefer native hierarchy, progressive disclosure, sheets, menus, rows, haptics, safe-area behavior, and contextual actions. Reduce nested containers and branded chrome.

### Web / Corporate
Use the same semantic typography and color rules with a larger editorial scale, wider compositions, and more generous whitespace. Corporate pages must never look like a separate template family.

## Voice
Concerto is concise, informed, premium, calm, and useful.
- No unnecessary exclamation marks.
- No jargon for its own sake.
- No fake urgency.
- No exaggerated claims.
- No inconsistent naming for the same feature.
- Use `Your Night`, `Concerto+`, and `From the Concert to the City®` consistently.

## Logo standards
- Maintain clear space around the lockup.
- Never place a navy/blue logo on a navy background without a high-contrast treatment.
- Use the white lockup on dark navy surfaces.
- Never stretch, recolor arbitrarily, or recreate the mark in text.

## Business-wide navigation and footer standard
- Navigation labels use DM Sans, Title Case, medium/semi-bold.
- Footer group labels are eyebrows and may be uppercase.
- Footer content groups remain: Explore, Company, Work With Us, Support.
- Active social destinations: Instagram, TikTok, YouTube only.

## Governance
Every new component or page must map text to a semantic role before styling. If a role is missing, extend the design system first rather than creating a one-off style.

Before release, run the brand-system validator and complete visual QA on:
1. Home
2. Your Night
3. Near Me
4. Venues
5. Tours
6. Account
7. Concerto+
8. About
9. Press & Media
10. Investors
11. Partners
12. Creators
13. Contact
14. Help / FAQ / legal
15. Global footer and navigation on desktop and mobile

The test is simple: moving between any two Concerto surfaces should feel like changing rooms inside the same company, not changing companies.
