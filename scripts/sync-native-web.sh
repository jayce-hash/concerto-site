#!/usr/bin/env bash
set -euo pipefail
# Usage: scripts/sync-native-web.sh /path/to/concerto-native
# Exports the native Expo app for web, then overlays only generated app output
# onto this repo. Site-only files that are not in the export remain untouched.
NATIVE="${1:-../concerto-native}"
SITE="$(cd "$(dirname "$0")/.." && pwd)"
NATIVE="$(cd "$NATIVE" && pwd)"
rm -rf "$NATIVE/dist-web"
(
  cd "$NATIVE"
  npx expo export --platform web --output-dir dist-web
)
cp -a "$NATIVE/dist-web/." "$SITE/"
node "$SITE/scripts/validate-release.js"
node - <<'NODE' "$NATIVE" "$SITE"
const fs=require('fs'), cp=require('child_process');
const [native,site]=process.argv.slice(2);
let commit='unknown';
try{commit=cp.execFileSync('git',['-C',native,'rev-parse','HEAD'],{encoding:'utf8'}).trim()}catch{}
fs.writeFileSync(`${site}/.native-web-sync.json`,JSON.stringify({nativeCommit:commit,syncedAt:new Date().toISOString()},null,2)+'\n');
NODE
node "$SITE/scripts/validate-deploy.js"
