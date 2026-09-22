# Concerto update — September 22, 2026

The website uses original concert artwork, a before/at/after-show walkthrough, concise explanations and existing guides. No app screenshots or screenshot-upload workflow remain. App branding and existing SEO routes, canonical URLs, robots rules and verification metadata are preserved.

Tours adds Favorite Tours and Favorite Artists. Venues adds Favorite Venues. Saved-show images now use the saved event photo first, with artist fallback and image-error handling. Home and Your Night share calendar-day countdowns and date-only-safe formatting. Carousel state resets when saved shows change. Saved-show synchronization waits for local data and ignores stale account results after sign-out. The existing Account location control remains.

Automated checks cover source types, native bundle generation, existing brand/release/SEO checks, saved-show regressions, site links, Perks and HTML structure. Browser rendering and real-device purchase/notification flows were not verified in this environment. This is not a guarantee that every possible bug is eliminated.

Save both ZIPs and both push scripts in Downloads, replacing older copies. Use bash push-site-v7.sh for the website and bash push-native-2-6.sh for the app. The app script pushes and starts your existing production EAS build with auto-submit. Both scripts support --prepare-only. Renamed root folders inside repacked ZIPs are accepted. Keep the archive filenames unchanged.
