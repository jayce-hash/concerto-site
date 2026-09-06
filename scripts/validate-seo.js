#!/usr/bin/env node
const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
function fail(m){console.error('FAIL: '+m);process.exit(1)}
function ok(c,m){if(!c)fail(m)}
function read(p){return fs.readFileSync(path.join(root,p),'utf8')}
const venues=JSON.parse(read('data/venues.json'));
const tours=JSON.parse(read('data/tours.json'));
const setlists=JSON.parse(read('setlists.json'));
const sitemap=read('sitemap.xml');
const locs=[...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m=>m[1]);
const venueFiles=fs.readdirSync(path.join(root,'venue')).filter(f=>f.endsWith('.html')&&!f.startsWith('['));
const tourFiles=fs.readdirSync(path.join(root,'tour')).filter(f=>f.endsWith('.html')&&!f.startsWith('['));
const setlistFiles=fs.readdirSync(path.join(root,'setlist')).filter(f=>f.endsWith('.html')&&!f.startsWith('['));
ok(venueFiles.length===venues.length,`venue HTML count ${venueFiles.length} != catalog ${venues.length}`);
ok(tourFiles.length===tours.length,`tour HTML count ${tourFiles.length} != catalog ${tours.length}`);
ok(setlistFiles.length===Object.keys(setlists).length,`setlist HTML count ${setlistFiles.length} != catalog ${Object.keys(setlists).length}`);
ok(!fs.existsSync(path.join(root,'venue','[slug].html')),'generic venue [slug] shell must not be deployable');
ok(!fs.existsSync(path.join(root,'tour','[slug].html')),'generic tour [slug] shell must not be deployable');
const redirects=read('_redirects');
ok(!/^\/venue\/\*\s+\/venue\/\[slug\]\.html\s+200/m.test(redirects),'generic venue wildcard rewrite still present');
ok(!/^\/tour\/\*\s+\/tour\/\[slug\]\.html\s+200/m.test(redirects),'generic tour wildcard rewrite still present');
ok(!/^\/setlists\s+\/tours\s+301/m.test(redirects),'setlists hub still redirects to tours');
ok(!locs.some(u=>u.includes('/top-picks')||u.includes('[slug]')||u.endsWith('.html')),'sitemap contains redirect, placeholder, or .html URL');
ok(locs.includes('https://concertocity.com/setlists'),'setlists hub missing from sitemap');
ok(locs.filter(u=>u.includes('/venue/')).length===venues.length,'sitemap venue count incorrect');
ok(locs.filter(u=>u.includes('/tour/')).length===tours.length,'sitemap tour count incorrect');
ok(locs.filter(u=>u.includes('/setlist/')).length===Object.keys(setlists).length,'sitemap setlist count incorrect');
for(const v of venues){const slug=v.id;const h=read(`venue/${slug}.html`);ok(h.includes(`rel="canonical" href="https://concertocity.com/venue/${slug}"`),`bad venue canonical ${slug}`);ok(h.includes('/css/public-v4.css'),`venue is not public-web template ${slug}`);ok(!h.includes('react-native-stylesheet'),`venue still contains app shell ${slug}`)}
for(const t of tours){const slug=t.tourId;const h=read(`tour/${slug}.html`);ok(h.includes(`rel="canonical" href="https://concertocity.com/tour/${slug}"`),`bad tour canonical ${slug}`);ok(h.includes('/css/public-v4.css'),`tour is not public-web template ${slug}`);ok(!h.includes('react-native-stylesheet'),`tour still contains app shell ${slug}`)}
for(const slug of Object.keys(setlists)){const h=read(`setlist/${slug}.html`);ok(h.includes(`rel="canonical" href="https://concertocity.com/setlist/${slug}"`),`bad setlist canonical ${slug}`);ok(h.includes('<ol class="song-list">'),`setlist content missing ${slug}`)}
for(const f of ['account.html','search.html','settings.html','plan.html','login.html','signup.html']){if(fs.existsSync(path.join(root,f)))ok(/name=["']robots["'][^>]*content=["']noindex/i.test(read(f))||/content=["']noindex[^"']*["'][^>]*name=["']robots/i.test(read(f)),`${f} should be noindex`)}
ok(read('index.html').includes('The concert is only part of the night.'),'public marketing homepage missing');
console.log(`PASS: SEO | ${locs.length} sitemap URLs | ${venues.length} venue pages | ${tours.length} tour pages | ${Object.keys(setlists).length} dedicated setlist pages | public web v4 templates`);
