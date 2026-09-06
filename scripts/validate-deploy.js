const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
const errors=[]; const ok=(c,m)=>{if(!c)errors.push(m)}; const read=f=>fs.readFileSync(path.join(root,f),'utf8');
const index=read('index.html');
ok(index.includes('/css/public-v6.css'),'public homepage is not on V6 website system');
ok(index.includes('/js/public-v6.js'),'public homepage is not on V6 website runtime');
ok(!index.includes('react-native-stylesheet'),'public homepage still contains an Expo app shell');
const expoDir=path.join(root,'_expo','static','js','web');
ok(fs.existsSync(expoDir),'app-owned Expo bundle directory missing');
if(fs.existsSync(expoDir)){const entries=fs.readdirSync(expoDir).filter(f=>/^entry-.*\.js$/.test(f));ok(entries.length===1,`expected exactly one current Expo entry bundle, found ${entries.length}`)}
const publicRoutes=['index','venues','tours','setlists','near-me','premium','perks','partners','partner-restaurants','partner-hotels','partner-venues','partner-artists','about','investors','press','creators','contact','help','faq','search','bagcheck','bags','parking','rideshare','concessions','privacy','terms','partners-thank-you'];
for(const route of publicRoutes){const f=path.join(root,`${route}.html`);ok(fs.existsSync(f),`public route missing: ${route}`);if(fs.existsSync(f)){const h=fs.readFileSync(f,'utf8');ok(h.includes('/css/public-v6.css'),`${route} is not on V6 website system`);ok(h.includes('/js/public-v6.js'),`${route} is not on V6 website runtime`);ok(!h.includes('react-native-stylesheet'),`${route} still contains Expo shell`)}}
const redirects=read('_redirects'); const catchPos=redirects.lastIndexOf('/* /404.html 404');ok(catchPos>=0,'final 404 catch-all missing');
for(const line of ['/venues /venues.html 200','/tours /tours.html 200','/setlists /setlists.html 200','/search /search.html 200','/help /help.html 200','/venue/* /venue/:splat.html 200','/tour/* /tour/:splat.html 200','/setlist/* /setlist/:splat.html 200']) ok(redirects.indexOf(line)>=0&&redirects.indexOf(line)<catchPos,`public route rewrite invalid or after catch-all: ${line}`);
for(const dead of ['css/public-v5.css','js/public-v5.js','css/public-v4.css','js/public-v4.js','top-picks.html','+not-found.html']) ok(!fs.existsSync(path.join(root,dead)),`dead public artifact still deployable: ${dead}`);
if(errors.length){console.error('DEPLOY VALIDATION FAILED');for(const e of errors)console.error(' - '+e);process.exit(1)}
console.log('PASS: V6 public website + app-owned utility bundle are deployment-ready');
