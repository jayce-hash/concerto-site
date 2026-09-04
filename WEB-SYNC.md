# Native ↔ Website sync

`concerto-native` is the source of truth for the app experience. The site repository remains the source of truth for venue/tour content, SEO/editorial pages, and Netlify functions.

The **Sync native web** GitHub Action checks out `jayce-hash/concerto-native`, runs a fresh Expo static web export, overlays that generated output onto this repository, validates the site, and commits only when something changed. Site-only files remain because the overlay does not delete files absent from Expo's export.

Run the workflow manually after a native release. The hourly schedule is a safety net so a forgotten web export cannot leave `concertocity.com` on an old app build indefinitely.

If `concerto-native` is private and the website repository's default `GITHUB_TOKEN` cannot read it, create a fine-grained read-only GitHub token for that repository and save it in the website repo as `CONCERTO_NATIVE_REPO_TOKEN`.
