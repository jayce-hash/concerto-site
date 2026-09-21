# Native app brand alignment — September 2026

The native app is the source of truth for Concerto’s visual identity. Website layout and copy may adapt to the web; fonts, colors, logo, and brand identity must remain aligned with the app. This replaces the previous website-only typography and color direction.

## Typography

- Playfair Display 700: page, hero, section, and editorial headings.
- Playfair Display 500: secondary editorial and card headings.
- DM Sans 400: body copy; 500: metadata; 600: controls and navigation; 700: eyebrows.
- No replacement sans-serif headline system, third typeface, or decorative italic headline treatment.

## Colors

Use the light-mode values from `src/theme/tokens.ts` in the native app:

- Navy and primary text: `#121E36`; soft navy: `#1C2B4A`.
- Gold: `#C9A84C`; light gold: `#E5C365`; soft gold: `#F2EBD6`.
- Background: `#F8F9F9`; surface: `#FFFFFF`.
- Muted text: `#5A6478`; faint text: `#8A91A3`; silver: `#C0C0C0`.
- Dividers: `rgba(18,30,54,0.11)`.

No lilac or alternate warm off-white palette. Gold is selective emphasis. Preserve the existing Concerto logo, product names, and “From the Concert to the City®” slogan.

## Presentation

Keep open layouts, clear hierarchy, concise writing, and controls consistent with the app’s rounded shapes. Real screenshots retain their natural aspect ratio. Do not add simulated phones, decorative screenshot frames, or invented app interfaces.

Keep the company story precise. Describe actual features, partner processes, and available perks. Do not invent audience counts, offers, exclusivity claims, or guaranteed business outcomes.

Preserve existing canonical routes, sitemap coverage, robots directives, verification metadata, factual guides, and form contracts. Public website pages remain separate from native utility exports.

`scripts/experience_pages.py`, `scripts/company_pages.py`, and `css/public-v6.css` own public presentation. `SCREENSHOT-REPLACEMENT-GUIDE.md` describes replacement captures. Automated checks verify structure and brand declarations; rendered browser review is a separate check and must not be claimed when unavailable.
