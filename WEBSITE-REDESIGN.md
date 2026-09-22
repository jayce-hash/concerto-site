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

## V7 (Sep 21, 2026): a product experience on the library
Home, Your Night, and Concerto+ are composed in `scripts/site_v7.py` with `js/public-v7.js`
and the `.v7-*` layer in `css/public-v6.css`. No screenshots anywhere: every visual is
real data (`night_components.py`) or a live interaction:
- Hero ticket: "Tonight near you" from Ticketmaster via `/geo` + `/tm`, example night otherwise.
- Venue lookup: type a venue, read its bag policy, parking, and rideshare from
  `data/venue_lookup.json` (built from `venue_info.json`, 405 KB, loaded on focus).
- Night timeline: sticky phase dial that follows the step in view.
- Setlist marquee from real song titles; counted numbers from the data.
- Reveal, count-up, and marquee all disabled under Reduce Motion.
Library pages (venue, tour, setlist) keep their URLs, canonicals, structured data, and
sitemap; their layout uses the same card system (`venue_section_card`, `setlist_card_for`).

## V8 (Sep 21, 2026): the company site, written from zero
`scripts/site_v8.py` runs last in `rebuild-consumer-site.py`. For every public page it keeps
the `<head>` exactly as generated (title, description, robots, canonical, Open Graph, smart
banner, structured data) and authors a new body, so Search Console sees the same 624 URLs
and the same metadata. Verified: 631 of 631 heads identical to the prior site.
- No screenshots, no imitation app UI. The site sells with a point of view (the name, the
  principles), real venue photography (`img/cityguides/*/<Venue>.webp`), and the guide itself.
- Madison-Square-Garden.webp is a watermarked Getty image and must never be used.
- Design system: the `.v8` layer at the end of `css/public-v6.css`; behaviors appended to
  `js/public-v6.js` (reveal, guide table of contents, directory group filtering).
- Venue guide sections keep `.info-card[data-section]`, `p`, `.verified`, `.link-row a` so the
  Partner Console overlay and Report wrong info keep working.
- Secondary pages (press, partners, investors, creators, help, faq, contact, legal, near-me,
  perks, search) keep their content inside the new chrome (`body.v8.v8-legacy`).

## V8.1 (Sep 21, 2026): heroes that fit, and every page in the new voice
- One hero system, `hero()` in `scripts/site_v8.py`: navy, cream, white, or gold tone; type sized by
  width and screen height together (`min(vw, svh)`), so the first screen fits on 2560x1440 down to
  a 360x640 phone and a sideways phone. The home hero fills the first screen exactly; its stats
  strip hides on screens under 560px tall. The Kia Forum photo is off the home hero.
- Rewritten in the V8 voice: Press, Investors, Creators, Partners and the four partner pages,
  Contact, Near Me, Perks, Search, the thank-you pages, and 404. Facts are carried over from the
  previous pages; nothing new is claimed.
- Help, FAQ, Privacy, and Terms keep their exact text (FAQ matches its FAQPage schema, 15 of 15)
  inside a new document layout; the legal effective date shows in the hero.
- Netlify forms, the Perks feed, and site search keep their original markup and hooks.
- Tested: 377 heroes (13 screens x 29 pages) fit with no overflow; the pipeline runs on Python 3.9.
