const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const errors = [];
const ok = (cond, msg) => { if (!cond) errors.push(msg); };

const markerPath = path.join(root, '.native-web-sync.json');
ok(fs.existsSync(markerPath), 'native web sync marker missing; run the Sync native web workflow after the final native commit');

if (fs.existsSync(markerPath)) {
  try {
    const marker = JSON.parse(fs.readFileSync(markerPath, 'utf8'));
    ok(Boolean(marker.nativeCommit && marker.nativeCommit !== 'unknown'), 'native web sync marker has no native commit');
    ok(Boolean(marker.syncedAt), 'native web sync marker has no timestamp');
  } catch {
    errors.push('native web sync marker is invalid JSON');
  }
}

const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
for (const stale of [
  'first plan free to preview',
  '>Try It<',
  'Plan Night',
  'Nearby Restaurants</',
  'Nearby Hotels</',
  'Nearby Things to Do</',
]) {
  ok(!index.includes(stale), `generated web app still contains stale 2.4 copy/layout: ${stale}`);
}
ok(index.includes('From the Concert to the City®') || index.includes('From the Concert to the City&reg;') || index.includes('From the Concert to the City'), 'generated web app is missing Concerto brand lockup/copy');

const expoDir = path.join(root, '_expo', 'static', 'js', 'web');
ok(fs.existsSync(expoDir), 'generated Expo web bundle directory missing');
if (fs.existsSync(expoDir)) {
  const bundles = fs.readdirSync(expoDir).filter(f => f.endsWith('.js'));
  ok(bundles.length > 0, 'generated Expo web bundle missing');
}

if (errors.length) {
  console.error('DEPLOY VALIDATION FAILED');
  for (const e of errors) console.error(' - ' + e);
  process.exit(1);
}
console.log('PASS: synchronized native web build is deployment-ready');
