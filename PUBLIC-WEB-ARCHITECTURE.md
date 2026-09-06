# Concerto Public Web Architecture

## Principle

**One content system. Two presentation systems.**

The app and website use the same underlying Concerto data, but they do not have the same job.

### Public website

The website explains, demonstrates, and exposes Concerto. It is designed for discovery, search, trust, partners, press, investors, and first-time visitors.

Public-web-owned routes include:

- `/`
- `/venues` and `/venue/*`
- `/tours` and `/tour/*`
- `/setlists` and `/setlist/*`
- `/near-me`
- `/premium`
- `/perks`
- corporate, partner, support, and legal pages

These pages must remain website-native and crawlable. They must not be overwritten by Expo output.

### App/web utility layer

The native Expo project remains the source of truth for the interactive application and shared product data. Utility routes such as account, search, plan, authentication, and saved-show pages may continue to use exported app UI on the web.

### Sync law

Never copy the entire Expo `dist` folder over the site root again.

Use:

```bash
scripts/sync-native-web.sh /path/to/concerto-native
```

The script copies only app-owned assets/routes, regenerates public pages from the shared data, rebuilds the sitemap, and validates SEO.

## SEO law

Every public venue, tour, and setlist URL must have:

- unique static HTML
- a self-referencing canonical
- useful page-specific copy/data in initial HTML
- internal links from a crawlable hub
- inclusion in `sitemap.xml`
- no generic app-shell rewrite

Dedicated setlist pages live at `/setlist/{tourId}` so setlist search intent is not forced to compete with a duplicate tour page.
