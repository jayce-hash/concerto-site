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
