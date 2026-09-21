const fs=require('fs'),path=require('path'); const root=path.resolve(__dirname,'..'); const fail=[];
const css=fs.readFileSync(path.join(root,'css/public-v6.css'),'utf8');
const editorial=css;
const standards=fs.readFileSync(path.join(root,'CONCERTO-BRAND-AND-PRODUCT-STANDARDS.md'),'utf8');
if(!standards.includes('Native app brand alignment — September 2026')) fail.push('current website standards missing');
if(/\.site-nav a\{[^}]*text-transform:uppercase/.test(css)) fail.push('site navigation must be Title Case');
for(const f of ['css/company.css','css/editorial.css','css/concerto.css','css/global-footer.css']) if(fs.existsSync(path.join(root,f))) fail.push('retired stylesheet still present: '+f);
for(const file of ['index.html','your-night.html','premium.html','partners.html','about.html']){
 const page=fs.readFileSync(path.join(root,file),'utf8');
 if(/class="(?:device|iphone-screen)/.test(page)) fail.push(file+': decorative device container present');
 if((page.match(/href="\/css\/public-v6.css"/g)||[]).length!==1) fail.push(file+': expected one shared public stylesheet');
}
if(/DM Mono/.test(editorial)) fail.push('third brand typeface DM Mono must not be used');
if(!css.includes('--navy:#121E36')||!css.includes('--gold:#C9A84C')) fail.push('canonical brand colors missing');
for(const token of ['--cream:#F8F9F9','--muted:#5A6478','--gold-soft:#F2EBD6',"--display:'Playfair Display'","--body:'DM Sans'"]) if(!css.includes(token)) fail.push('app brand token missing: '+token);
if(/#(?:DAD4ED|F7F6F2|FCFCFA|F6F4EE)\b/i.test(css)) fail.push('unapproved website palette present');
const chrome=fs.readFileSync(path.join(root,'scripts/public_chrome.py'),'utf8');
if(!chrome.includes('Playfair+Display:wght@500;700')) fail.push('app display font weights missing');
if(fail.length){console.error('BRAND SYSTEM VALIDATION FAILED');fail.forEach(x=>console.error(' - '+x));process.exit(1)}
console.log('PASS: native brand alignment - app fonts and palette, one public stylesheet, unframed product captures');
