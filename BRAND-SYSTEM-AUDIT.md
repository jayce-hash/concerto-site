## Typography baseline

The typography authority is the original user-uploaded concerto-site-main-24 package. Preserve its established Playfair/DM Sans relationship and intentional specialty mono treatments rather than flattening all surfaces into one font treatment.

- Playfair Display 700: major page, section, editorial, venue, tour, and branded headings.
- Playfair Display 500/regular: secondary editorial/entity treatments where the original system used them.
- DM Sans: body, metadata, navigation, controls, buttons, filters, forms, and utility text.
- DM Mono: only where the original site explicitly used it for compact coded/editorial labels (for example Top Picks and selected premium micro-labels).
- Do not replace an established Playfair hierarchy with DM Sans for the sake of appearing more native.

# Concerto Business-Wide Brand System Audit

## Status
This package establishes Concerto Brand & Product Standards v1.0 as the governing design system for native iOS, Expo web, and corporate web surfaces.

## Changes applied
- Added semantic typography roles in `src/theme/tokens.ts`.
- Converted primary product page titles to the shared Playfair page-title role.
- Converted functional section headers to the shared DM Sans section-title role.
- Converted utility/card titles that had drifted into Playfair back to DM Sans.
- Removed forced all-caps treatment from web navigation.
- Standardized corporate card titles as DM Sans functional titles.
- Added the shared spacing/radius scale to corporate CSS.
- Added a business-wide standards manual to native and site repos.
- Added `validate:brand` scripts to both repos.

## Intentional exceptions
Playfair remains appropriate for:
- artist/show hero titles
- venue/tour page hero identity
- branded Concerto+ hero moments
- editorial corporate headlines
- quotes and emotional marketing statements

DM Sans remains appropriate for:
- functional section headers
- card/row titles
- buttons
- tabs/navigation
- metadata
- form controls
- filters
- support/help utility UI

## Release requirement
Before future releases, run:

Native:
`npm run validate:brand && npm run validate`

Site:
`npm run validate:brand && npm run validate`

A release is not visually complete until Home, Your Night, Near Me, Venues, Tours, Account, all corporate pages, and the global footer have been checked on mobile and desktop.
