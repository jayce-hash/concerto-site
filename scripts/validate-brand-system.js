const fs=require('fs'),path=require('path'); const root=path.resolve(__dirname,'..'); const fail=[];
const css=fs.readFileSync(path.join(root,'css/public-v6.css'),'utf8');
const editorial=css;
const standards=fs.readFileSync(path.join(root,'CONCERTO-BRAND-AND-PRODUCT-STANDARDS.md'),'utf8');
if(!/Playfair defines hierarchy\. DM Sans defines function\./.test(standards)) fail.push('typography principle missing');
if(/\.site-nav a\{[^}]*text-transform:uppercase/.test(css)) fail.push('site navigation must be Title Case');
for(const f of ['css/company.css','css/editorial.css','css/concerto.css','css/global-footer.css']) if(fs.existsSync(path.join(root,f))) fail.push('retired stylesheet still present: '+f);
if(!/\.card h3\{font-family:var\(--display\)/.test(css)) fail.push('corporate editorial card titles must use Playfair');
if(/font-weight:700/.test(css.match(/\.hero h1\{[^}]*\}/)?.[0]||'')) fail.push('display headings must be Playfair 500, not 700');
if(/DM Mono/.test(editorial)) fail.push('third brand typeface DM Mono must not be used');
if(!css.includes('--navy:#121E36')||!css.includes('--gold:#C9A84C')) fail.push('canonical brand colors missing');
if(fail.length){console.error('BRAND SYSTEM VALIDATION FAILED');fail.forEach(x=>console.error(' - '+x));process.exit(1)}
console.log('PASS: Concerto Brand & Product Standards v1.3 - one public stylesheet');
