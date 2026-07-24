# Nearby split for the native app

Drop the `data/nearby/` folder into the site repo root (next to
data/nearby.json) and deploy. Nothing on the site changes; the app
fetches `/data/nearby/<slug>.json` per venue (~10 KB) instead of the
3.7 MB monolith. Keep data/nearby.json as-is for the site.

To keep them in sync, add to build_static.py after nearby.json is
written: iterate its keys and write each entry to
data/nearby/<slug>.json.
