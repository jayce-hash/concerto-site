# Put screenshots in the repo after publishing

The website can be pushed now with its existing example images. Later, upload or replace these PNGs in the website repository under `img/product/source/` and commit them to the deployment branch. Netlify's build refreshes the image manifest and public pages automatically. You do not need to edit page HTML or manually replace hashed image files.

| Your screenshot | Exact filename | Website placement |
| --- | --- | --- |
| Homepage | home.png | Homepage “Before the show” view |
| Venues home | venues.png | The App / Your Night screenshot gallery |
| Tours home | tours.png | The App / Your Night screenshot gallery |
| Near Me | near-me.png | Near Me page |
| Example tour | tour.png | The App / Your Night screenshot gallery |
| Example venue | venue.png | The App / Your Night screenshot gallery |
| Concerto+ | night-plan.png | Concerto+ product section; ideally capture a completed Plan My Night timeline |
| Your Night | your-night.png | Your Night overview |

The first eight views are your requested set. Existing detail screenshots remain in the site for venue essentials, getting home, parking, and concessions; you do not need to replace those now. AI Bag Check remains text-only unless bag-check.png is supplied later.

Use original full-resolution PNGs from the same iPhone and appearance. Set the location in Account first. Use the same tour, venue, and saved concert for related screens. Wait for data to load. No added device frame, backgrounds, captions, stitched screenshots, or private information.

## Publish the website now

Replace the old Downloads copies with the latest `concerto-site-aligned.zip` and `push-site-v7.sh`, then:

```bash
cd ~/Downloads
bash push-site-v7.sh
```

This validates, commits, and pushes the site to your existing repository. Its existing Netlify deployment connection publishes the commit. If you previously ran prepare-only and have uncommitted changes, review/commit or stash those first; the script deliberately stops on a dirty checkout.

## Add screenshots later

GitHub's upload interface works: open `img/product/source/`, upload the correctly named files, and commit to the deployment branch. Alternatively, copy the files into your local website checkout, then:

```bash
cd ~/Downloads/concerto-website
git add img/product/source/
git commit -m "Update Concerto app screenshots"
git push
```

The new build command is `python3 scripts/prepare-site.py`. It encodes WebP when Pillow is available; otherwise it publishes an unchanged PNG with a new content-hashed URL. Both paths refresh the pages and run validation. A changed filename/hash prevents the old screenshot from being reused from cache.

For local regeneration, run that same command. The Netlify configuration uses its documented [build command setting](https://docs.netlify.com/build/configure-builds/file-based-configuration/).

The existing site is fully populated; no missing-image placeholders block launch. The local build and both image-processing paths were checked. Actual Netlify deployment, device screenshots, and desktop/iPhone visual sign-off still need checking in your environment.
