# Concerto Public Website Screenshot Slots

The public website uses real current app captures from `img/product/source/`. Every product section has its own semantic screenshot slot, so a screenshot can be replaced without touching HTML or Python.

## Replaceable files

- `home.png` — Homepage hero / saved-show context.
- `premium.png` — Homepage Concerto+ section.
- `near-me.png` — Near Me product page.
- `bagcheck.png` — AI Bag Check page.
- `bags.png` — Bag-policy page.
- `parking.png` — Parking page.
- `rideshare.png` — Rideshare page.
- `concessions.png` — Concessions page.

The feature-specific files currently use the strongest relevant venue capture available. They are intentionally separate copies so you can replace one later without changing the other pages.

## Presentation rules

- Use a real current Concerto screen that actually demonstrates the section beside it.
- Keep the screenshot at the same portrait aspect ratio. Current slots are `941 × 2048`.
- Do not crop, rebuild, or retouch the app UI inside the screenshot.
- The website covers only the iOS status-bar area with a standardized marketing status bar: `12:00`, full cellular signal, Wi-Fi, full battery, and no location-services icon.
- Perks intentionally has no fake phone screenshot until there is a real live Perks state worth showing.

## To replace a screenshot

Replace the matching PNG in `img/product/source/`, keep the exact filename, and deploy normally. No public-page rebuild is required just to swap the image.
