# Concerto — aligned app and website

Historical app-and-site handoff. The current website is superseded by `WEBSITE-REDESIGN.md`; its new screenshot requirements and design replace the website framing described below. The app portion remains a record of the prior release.

Prepared September 21, 2026 from `concerto-native-2-8(5).zip` and `concerto-site-2-8(3).zip`.

## What changed

- **Website:** a shorter homepage, simpler Your Night and Concerto+ pages, quieter navigation/footer, consistent typography and spacing, and full-height screenshot frames. Existing public venue, tour, and setlist routes remain available.
- **Company:** concise About, Press, Investors, Creators, Contact, and FAQ copy. Jayce's founder story stays grounded in the problem Concerto solves. No invented audience numbers, revenue, endorsements, or guaranteed results.
- **Partners:** distinct restaurant/bar, hotel, venue, and artist/tour paths. Each explains the fan benefit, business objective, possible measurement, and inquiry-to-launch process. Existing Netlify form names are retained.
- **Perks:** live offers feed both the app and website. Offers require a real benefit and redemption terms; future, expired, and invalid-date offers are filtered. Links accept HTTPS without embedded credentials. Empty results and service failures have different messages. Artist offers can be tied to a tour; venues can submit offers too.
- **App:** existing colors, typography, tabs, and component styling are preserved. The first saved show opens Your Night. Generated plans can be saved on the device, have their stop names/times edited, and be shared as readable text. Previous-day shows support private notes stored on the device. Your Night sharing includes useful details instead of relying on the recipient having the sender's saved show.
- **Accuracy:** planning instructions restrict named recommendations to supplied places and distinguish unknown timing. Show-day wording avoids declaring a concert over based only on its scheduled start. Exact event IDs take priority when matching venue-provided stage times.
- **Build workflow:** Expo, expo-constants, and expo-updates are aligned to the SDK's recommended patch versions. App-backed website utilities were re-exported. Future syncs preserve public search and mark private utilities noindex. Push scripts use the lockfile, keep backups, preserve local configuration/screenshots, and stop on uncommitted work or failed checks.

## Use the files

Download these four files into `~/Downloads`, keeping their names:

- `concerto-site-aligned.zip`
- `concerto-native-aligned.zip`
- `push-site-v7.sh`
- `push-native-2-6.sh`

Do not rename the ZIPs to the old names. You do not need to unzip them yourself. The updated scripts expect the new names but keep your existing repository folders: `concerto-website` and `concerto-native-repo`.

Website first:

```bash
cd ~/Downloads
chmod +x push-site-v7.sh
./push-site-v7.sh
```

Then the app:

```bash
cd ~/Downloads
chmod +x push-native-2-6.sh
./push-native-2-6.sh
```

The website script commits and pushes, which can trigger your existing Netlify deploy. The app script commits and pushes, then runs your existing production EAS build with `--auto-submit` to App Store Connect. This is not a claim that Apple will approve or publish the app automatically. Neither script was run against your live repositories while preparing these files.

Both scripts make a backup in Downloads before replacing files. They preserve environment files, relevant local build/configuration folders, and existing ignore rules. The website script also preserves captures already in `img/product/source`, `img/product/screens`, and `img/photo`. Commit or stash existing local work before running. If a command fails, the script stops; inspect the message and backup before retrying.

For local review without committing, pushing, or submitting, run either script with `--prepare-only`. This leaves deliberate uncommitted changes in the checkout; review and commit them before rerunning the default script. The mode still pulls with `--ff-only`, installs native dependencies where applicable, and rebuilds local files.

## One-time Perks setup

Before accepting partner offers, apply `supabase/migration-perk-review-2026-09-21.sql` from the website ZIP in Supabase. It retains data and replaces the old broad write policy with draft-only partner permissions. Until that migration is applied, the old policy still permits a partner to publish directly.

If the partner tables do not exist yet, first follow `supabase/README-partners.md`. That document also explains review, publication, pausing offers, required environment settings, sign-in redirects, and form notifications. This release does not apply a live migration, create real offers, send emails, or activate billing.

## Screenshots

Use `SCREENSHOT-REPLACEMENT-GUIDE.md` in the website ZIP. Replace the matching PNGs in `img/product/source`; the shared manifest supplies the homepage and product pages. The new refresh script compresses captures without repainting the status bar or cropping their contents. Pillow is required to encode replacements. If it is unavailable, the push script keeps the existing manifest and explains how to update later.

Newer screenshots have not been supplied. The included captures are existing assets, not proof of the revised app running on a device.

## Validation and remaining checks

Passed locally: native TypeScript, brand/release/SEO checks, accuracy checks, focused offer/plan regressions, Expo's offline installed-SDK dependency check, iOS JavaScript/Hermes export, and web export. Website brand/release/deploy/SEO/link checks and the SEO audit passed. Shared venue IDs, venue information, tours, and setlists match between app and site. Push scripts pass Bash syntax checks. Short-page SEO warnings are intentional; the site is meant to be concise.

The cloud browser could not open the local preview, so visual QA remains outstanding. No signed iOS binary, physical-device test, live Supabase integration test, payment test, or live form-delivery test was performed. The API regressions use a fake database. Before release, check the site at desktop and iPhone widths and test on TestFlight: first save, reopen/edit/share a plan, save a past-show note, Perks loading/retry/redemption, and existing purchase/restore flows.

Plans and notes are local to the device in this release. Sharing sends text; it is not a live collaborative itinerary. Offers depend on approved partner content. Reporting counts recorded activity and does not prove purchases or redemptions. AI instructions reduce unsupported suggestions but cannot guarantee model accuracy.
