const fs=require('fs'), path=require('path'), cp=require('child_process');
const root=path.resolve(__dirname,'..'); const errors=[]; const ok=(c,m)=>{if(!c)errors.push(m)};
const J=(p)=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const venues=J('data/venues.json'), info=J('data/venue_info.json'), tours=J('data/tours.json'), setlists=J('setlists.json');
const ids=venues.map(v=>v.id); ok(new Set(ids).size===ids.length,'duplicate venue ids');
ok(venues.length===346,`expected 346 venues, got ${venues.length}`); ok(Object.keys(info).length===346,`expected 346 venue info records, got ${Object.keys(info).length}`);
for(const id of ids){ok(info[id],`venue_info missing ${id}`); ok(fs.existsSync(path.join(root,'data/nearby',`${id}.json`)),`nearby missing ${id}`)}
const fields=['bagPolicy','parking','rideshare','concessions','accessibility','reEntry','ticketPickup','gates'];
for(const [id,v] of Object.entries(info)) for(const f of fields){const x=v[f]; ok(x&&typeof x==='object',`${id}.${f} missing`); if(x){ok(/^https:\/\//.test(x.officialLink||''),`${id}.${f} officialLink missing/non-https`); ok(/^\d{4}-\d{2}-\d{2}$/.test(x.verified||''),`${id}.${f} verified date invalid`);}}
ok(new Set(tours.map(t=>t.tourId)).size===tours.length,'duplicate tour ids');
const unmatched=[]; for(const t of tours){const matches=Object.keys(setlists).filter(k=>t.tourId.startsWith(k)); if(matches.length!==1) unmatched.push([t.tourId,matches.length]);}
const allowed=new Set(['franklin-jonas-the-byzantines-first-of-many-tour']);
for(const [id,n] of unmatched) ok(allowed.has(id)&&n===0,`setlist mapping ${id}: ${n} matches`);

const netlify=fs.readFileSync(path.join(root,'netlify.toml'),'utf8');
ok(netlify.includes('data/venue_info.json'),'netlify.toml must package venue_info.json for Bag Check');
ok(fs.existsSync(path.join(root,'scripts/sync-native-web.sh')),'native web sync script missing');
const bannedVenueSources=['Education-After-School-Grants-2024-2025-Guidelines.pdf','2017-OSF-Food-Vendor-App.pdf','2022-SXSW-General-Exhibitons-FAQ','/miami2024','/shows/calendar/2025-08'];
const infoText=JSON.stringify(info);
for(const stale of bannedVenueSources) ok(!infoText.includes(stale),`known stale venue source remains: ${stale}`);


const companyPages=['about.html','premium.html','partners.html','creators.html','press.html','investors.html','contact.html','faq.html','privacy.html','terms.html'];
for(const f of companyPages){
  const fp=path.join(root,f); ok(fs.existsSync(fp),`company page missing: ${f}`);
  if(fs.existsSync(fp)){ const html=fs.readFileSync(fp,'utf8'); ok(!/noindex/i.test(html),`company page unexpectedly noindex: ${f}`); }
}
const aasa=fs.readFileSync(path.join(root,'.well-known/apple-app-site-association'),'utf8');
ok(aasa.includes('/show/*'),'AASA must include /show/* for saved-show universal links');
const sitemap=fs.readFileSync(path.join(root,'sitemap.xml'),'utf8');
for(const slug of ['partners','creators','press','investors','contact']) ok(sitemap.includes(`https://concertocity.com/${slug}`),`sitemap missing /${slug}`);
const publicText=companyPages.map(f=>fs.readFileSync(path.join(root,f),'utf8')).join('\n');
for(const stale of ['Three things. AI Bag Check','Three tools. One night.','first plan free to preview','Concerto Premium']) ok(!publicText.includes(stale),`stale public product copy remains: ${stale}`);
ok(publicText.includes('From the Concert to the City&reg;') || publicText.includes('From the Concert to the City®'),'registered slogan missing from company pages');
for(const f of fs.readdirSync(root).filter(x=>x.endsWith('.html'))){ const html=fs.readFileSync(path.join(root,f),'utf8'); const n=(html.match(/<script src="\/?auth\.js"><\/script>/g)||[]).length; ok(n<=1,`${f} loads auth.js more than once`); }
ok(fs.existsSync(path.join(root,'BRAND-LANGUAGE-2.5.md')),'2.5 brand language source of truth missing');
ok(fs.existsSync(path.join(root,'LAUNCH-2.5.md')),'2.5 launch pack missing');

for(const f of fs.readdirSync(path.join(root,'netlify/functions')).filter(x=>x.endsWith('.js'))){try{cp.execFileSync(process.execPath,['--check',path.join(root,'netlify/functions',f)],{stdio:'ignore'});}catch{errors.push(`syntax error netlify/functions/${f}`)}}
if(errors.length){console.error('RELEASE VALIDATION FAILED'); for(const e of errors)console.error(' - '+e); process.exit(1)}
console.log(`PASS: site | ${venues.length} venues | ${tours.length} tours | ${Object.keys(setlists).length} setlists | ${fields.length} verified venue sections each`);
