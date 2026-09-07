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
const populated=Object.entries(setlists).filter(([,v])=>Array.isArray(v.songs)&&v.songs.length>0);
const coming=Object.entries(setlists).filter(([,v])=>!Array.isArray(v.songs)||v.songs.length===0);
const sitemap=read('sitemap.xml');
const locs=[...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m=>m[1]);
const venueFiles=fs.readdirSync(path.join(root,'venue')).filter(f=>f.endsWith('.html')&&!f.startsWith('['));
const tourFiles=fs.readdirSync(path.join(root,'tour')).filter(f=>f.endsWith('.html')&&!f.startsWith('['));
const setlistFiles=fs.readdirSync(path.join(root,'setlist')).filter(f=>f.endsWith('.html')&&!f.startsWith('['));
ok(venueFiles.length===venues.length,`venue HTML count ${venueFiles.length} != catalog ${venues.length}`);
ok(tourFiles.length===tours.length,`tour HTML count ${tourFiles.length} != catalog ${tours.length}`);
ok(setlistFiles.length===populated.length,`public setlist HTML count ${setlistFiles.length} != populated setlists ${populated.length}`);
ok(!fs.existsSync(path.join(root,'venue','[slug].html')),'generic venue [slug] shell must not be deployable');
ok(!fs.existsSync(path.join(root,'tour','[slug].html')),'generic tour [slug] shell must not be deployable');
ok(!fs.existsSync(path.join(root,'setlist','[slug].html')),'generic setlist [slug] shell must not be deployable');
const redirects=read('_redirects');
ok(!/^\/venue\/\*\s+\/venue\/\[slug\]\.html\s+200/m.test(redirects),'generic venue wildcard rewrite still present');
ok(!/^\/tour\/\*\s+\/tour\/\[slug\]\.html\s+200/m.test(redirects),'generic tour wildcard rewrite still present');
ok(!locs.some(u=>u.includes('/top-picks')||u.includes('[slug]')||u.endsWith('.html')),'sitemap contains redirect, placeholder, or .html URL');
ok(locs.includes('https://concertocity.com/setlists'),'setlists hub missing from sitemap');
ok(locs.filter(u=>u.includes('/venue/')).length===venues.length,'sitemap venue count incorrect');
ok(locs.filter(u=>u.includes('/tour/')).length===tours.length,'sitemap tour count incorrect');
ok(locs.filter(u=>u.includes('/setlist/')).length===populated.length,'sitemap populated setlist count incorrect');
for(const [slug] of coming){ok(!fs.existsSync(path.join(root,'setlist',`${slug}.html`)),`empty setlist detail must not exist: ${slug}`);ok(!locs.includes(`https://concertocity.com/setlist/${slug}`),`empty setlist must not be in sitemap: ${slug}`)}
for(const v of venues){const slug=v.id;const h=read(`venue/${slug}.html`);ok(h.includes(`rel="canonical" href="https://concertocity.com/venue/${slug}"`)||h.includes(`href="https://concertocity.com/venue/${slug}" rel="canonical"`),`bad venue canonical ${slug}`);ok(h.includes('/css/public-v6.css'),`venue is not V6 public-web template ${slug}`);ok(!h.includes('react-native-stylesheet'),`venue still contains app shell ${slug}`)}
for(const t of tours){const slug=t.tourId;const h=read(`tour/${slug}.html`);ok(h.includes(`https://concertocity.com/tour/${slug}`),`bad tour canonical ${slug}`);ok(h.includes('/css/public-v6.css'),`tour is not V6 public-web template ${slug}`);ok(!h.includes('react-native-stylesheet'),`tour still contains app shell ${slug}`);const meta=setlists[slug];if(meta&&!Array.isArray(meta.songs)||meta&&meta.songs.length===0){ok(/Setlist Coming Soon!/i.test(h),`coming-soon tour does not say Setlist Coming Soon: ${slug}`)}}
for(const [slug,meta] of populated){const h=read(`setlist/${slug}.html`);ok(h.includes(`https://concertocity.com/setlist/${slug}`),`bad setlist canonical ${slug}`);ok(h.includes('<ol class="song-list">'),`setlist content missing ${slug}`);ok(!/\b0 songs\b/i.test(h),`zero-song copy present on populated setlist ${slug}`)}
for(const f of ['account.html','search.html','settings.html','plan.html','login.html','signup.html']){if(fs.existsSync(path.join(root,f)))ok(/name=["']robots["'][^>]*content=["']noindex/i.test(read(f))||/content=["']noindex[^"']*["'][^>]*name=["']robots/i.test(read(f)),`${f} should be noindex`)}
ok(read('index.html').includes('The concert is only part of the night.'),'public marketing homepage missing');
// Site chrome must be real HTML on every public page: one header, one footer, no fake phone status bar, no legacy nav.
const publicPages=fs.readdirSync(root).filter(f=>f.endsWith('.html')&&!['account.html','login.html','signup.html','plan.html','settings.html'].includes(f))
  .concat(venueFiles.map(f=>'venue/'+f),tourFiles.map(f=>'tour/'+f),setlistFiles.map(f=>'setlist/'+f));
for(const f of publicPages){const h=read(f);
  ok((h.match(/<header class="site-header">/g)||[]).length===1,`${f}: expected exactly one site header`);
  ok((h.match(/<footer class="site-footer">/g)||[]).length===1,`${f}: expected exactly one site footer`);
  ok(!h.includes('iphone-status')&&!h.includes('iphone-frame'),`${f}: fake phone status bar markup present`);
  ok(!/<nav[^>]*class="(nav|v2nav)[\s"]/.test(h),`${f}: legacy navigation markup present`);
  ok(!h.split('</head>')[0].includes('\\n'),`${f}: literal \\n text in <head>`);
  ok(!h.includes('/img/product/source/'),`${f}: references an uncropped product capture`);
  ok(!/\/img\/product\/screens\/[a-z-]+\.webp/.test(h),`${f}: references an unhashed product screen (rerun build-product-screens.py)`);}
ok(!/\b157 setlists\b/i.test(read('index.html')+read('setlists.html')),'public site must not imply all 157 tracked records are populated setlists');
console.log(`PASS: SEO | ${locs.length} sitemap URLs | ${venues.length} venue pages | ${tours.length} tour pages | ${populated.length} populated setlist pages | ${coming.length} tracked coming soon | public web V6`);
