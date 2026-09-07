#!/usr/bin/env bash
set -euo pipefail
# Usage: scripts/sync-native-web.sh /path/to/concerto-native
#
# Concerto web architecture:
#   - The native repo remains the source of truth for app code/data.
#   - The public website owns presentation for /, /venues, /venue/*,
#     /tours, /tour/*, /setlists, /setlist/*, /near-me, /premium,
#     /perks, corporate pages, and SEO content.
#   - Only app-owned utility routes and generated web assets are synced
#     from Expo. This prevents an Expo export from turning the public
#     website back into a stretched app shell.
NATIVE="${1:-../concerto-native}"
SITE="$(cd "$(dirname "$0")/.." && pwd)"
NATIVE="$(cd "$NATIVE" && pwd)"
rm -rf "$NATIVE/dist-web"
(
  cd "$NATIVE"
  npx expo export --platform web --output-dir dist-web
)

rm -rf "$SITE/_expo"
cp -a "$NATIVE/dist-web/_expo" "$SITE/_expo"
if [ -d "$NATIVE/dist-web/assets" ]; then
  rm -rf "$SITE/assets"
  cp -a "$NATIVE/dist-web/assets" "$SITE/assets"
fi

for f in account search settings plan login signup; do
  if [ -f "$NATIVE/dist-web/$f.html" ]; then cp "$NATIVE/dist-web/$f.html" "$SITE/$f.html"; fi
done

if [ -d "$NATIVE/dist-web/show" ]; then
  rm -rf "$SITE/show"
  cp -a "$NATIVE/dist-web/show" "$SITE/show"
fi

python3 "$SITE/scripts/build-public-site.py"
python3 "$SITE/scripts/build-public-features.py"
python3 "$SITE/scripts/build-company-pages.py"
python3 "$SITE/scripts/build-support-pages.py"
python3 "$SITE/scripts/apply-public-chrome.py"
python3 "$SITE/build_sitemap.py"
node "$SITE/scripts/validate-brand-system.js"
node "$SITE/scripts/validate-release.js"
node "$SITE/scripts/validate-seo.js"
node - <<'NODE' "$NATIVE" "$SITE"
const fs=require('fs'), cp=require('child_process');
const [native,site]=process.argv.slice(2);
let commit='unknown';
try{commit=cp.execFileSync('git',['-C',native,'rev-parse','HEAD'],{encoding:'utf8'}).trim()}catch{}
fs.writeFileSync(`${site}/.native-web-sync.json`,JSON.stringify({nativeCommit:commit,syncedAt:new Date().toISOString(),architecture:'public-web-v5'},null,2)+'\n');
NODE
node "$SITE/scripts/validate-deploy.js"
