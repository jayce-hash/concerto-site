# Concerto website redesign

Prepared September 21, 2026. This replaces the website presentation from the earlier aligned release. The native app was not changed in this redesign.

## The direction

“Make a night of it.” The app’s brand carried through an open, concise website: Playfair Display headings, DM Sans body text and controls, navy (#121E36), gold (#C9A84C), snow (#F8F9F9), and white. Soft-gold sections use the app’s #F2EBD6 token. Real screenshots appear directly on the page, with no simulated phones, floating frames, or invented app interfaces.

The homepage has five focused sections: the product promise, a three-part concert-night walkthrough, venue/tour/setlist discovery, Concerto+, and a download invitation. The walkthrough supports pointer and keyboard selection. It does not autoplay.

The same design extends through Your Night, Near Me, Concerto+, venue-information features, directory and detail pages, About, Partners, Perks, Press, Investors, Creators, Contact, FAQ, and shared navigation/footer. Corporate copy remains specific and restrained. Each partner category retains its own inquiry form and explains a relevant fan benefit, business opportunity, and practical process. Perks show actual available offers, with distinct empty and error states.

## Designed to stay useful

- No hardcoded concert countdown or seasonal promotion on the homepage.
- No unsupported audience counts, popularity claims, guaranteed partnership results, or “world’s only” positioning.
- Marketing screenshots are explicitly examples; new captures replace shared assets through one manifest.
- No new frontend framework or runtime dependency.
- Public website presentation stays separate from native utility exports, so the app sync cannot overwrite the new homepage.

Real venue policies, tour information, prices, and partner offers still require normal content maintenance. A lasting visual design does not make changing facts permanent.

## Files and local review

Download the latest `concerto-site-aligned.zip` and `push-site-v7.sh` into Downloads, replacing older copies with the same names. The archive contains `concerto-site-2-8/`. The script expects the existing website checkout at `~/Downloads/concerto-website`.

Prepare the existing checkout without committing or pushing:

```bash
cd ~/Downloads
bash push-site-v7.sh --prepare-only
cd ~/Downloads/concerto-website
python3 -m http.server 8000
```

Open `http://localhost:8000/index.html`. Python’s server serves files but does not apply Netlify’s clean-URL rewrites or serverless functions. Use `.html` page URLs during this local review. Full navigation, forms, Perks, and app links need an existing Netlify preview/deployment environment.

The script pulls with `--ff-only`, creates a backup, preserves local configuration and screenshots, rebuilds the pages, and runs validation. It stops if the checkout already has uncommitted work. Prepare-only deliberately leaves the finished changes uncommitted for review.

After reviewing those prepared changes, commit and push from the checkout to trigger the existing deployment:

```bash
git add -A
git commit -m "Rebuild Concerto website around the concert night"
git push
```

Running `bash push-site-v7.sh` without `--prepare-only` performs the prepare, commit, and push flow directly. Do not rerun it on the uncommitted prepare-only checkout. No live repository, deployment, database, billing, or outbound message was changed while preparing this package.

## SEO retained

All 624 sitemap URLs are unchanged. Existing public page canonicals, robots directives, Google verification metadata, redirects, and `robots.txt` were compared with the previous package and preserved. Venue, tour, and setlist data files are unchanged. The public pages remain generated HTML with crawlable navigation and structured data. Netlify's existing function and routing configuration is retained; a build command was added to process committed screenshots and regenerate public pages automatically.

Keep the existing domain and Search Console property. A visual rebuild on these same URLs does not require starting Search Console over. Rankings and crawl timing cannot be guaranteed; copy and layout changes may still affect search performance.

## Validation completed

- Website brand, release, deployment, SEO, and internal-link validators passed.
- 28,841 internal links resolved across 631 HTML files.
- HTML audit checked 628 public pages for a single main/H1, unique IDs, working skip targets, image alternatives/assets, tab targets, and unchanged SEO identity.
- Perks API regression checks passed; these use a fake database.
- JavaScript and deployment-script syntax checks passed.
- The SEO audit reports no blocking issues. Concise company pages and some guides retain informational short-page warnings.

## Review still needed

The browser security policy blocked both local HTTP and self-contained preview URLs. No desktop/mobile rendered visual sign-off is claimed. Before publishing, review Home, Your Night, Concerto+, Partners, one category form, About, a venue, a tour/setlist, search, and help/legal at 1440, 1024, 768, 390, and 320 px. Check focus visibility, the mobile menu, all three walkthrough tabs, reduced-motion behavior, forms, and app links. Live form delivery, live Perks service, and App Store opening were not tested here.

The eight requested captures are listed in `SCREENSHOT-REPLACEMENT-GUIDE.md`. Existing screenshots remain temporary. A real completed plan will replace the Your Night fallback on Concerto+; AI Bag Check will gain its screenshot automatically when supplied.

For the pre-existing partner approval/database setup, retain the instructions in `ALIGNED-RELEASE.md` and `supabase/README-partners.md`. This visual redesign does not apply that migration.

## Editing map

| Area | Source |
| --- | --- |
| Homepage, walkthrough, Your Night, Concerto+ | `scripts/experience_pages.py` |
| Partner and corporate content | `scripts/company_pages.py` |
| Shared header/footer | `scripts/public_chrome.py` |
| Guide and directory pages | `scripts/build-public-site.py` |
| Other product pages | `scripts/build-public-features.py` |
| Shared visual system | `css/public-v6.css`, editorial section |
| Menu, walkthrough, search, and live data | `js/public-v6.js` |
| Product capture lookup | `img/product/screens/manifest.json` |

Edit templates, then run `python3 scripts/rebuild-consumer-site.py` and `python3 scripts/apply-public-chrome.py`. Avoid editing generated page HTML directly.
