const fs=require('fs'),path=require('path'); const root=path.resolve(__dirname,'..'); const fail=[];
const css=fs.readFileSync(path.join(root,'css/company.css'),'utf8');
const editorial=fs.readFileSync(path.join(root,'css/editorial.css'),'utf8');
const standards=fs.readFileSync(path.join(root,'CONCERTO-BRAND-AND-PRODUCT-STANDARDS.md'),'utf8');
if(!/Playfair defines hierarchy\. DM Sans defines function\./.test(standards)) fail.push('typography principle missing');
if(/\.navlinks a\{[^}]*text-transform:uppercase/.test(css)) fail.push('corporate navigation must be Title Case');
if(!/\.card h3\{font-family:var\(--display\)/.test(css)) fail.push('corporate editorial card titles must use Playfair');
if(/DM Mono/.test(editorial)) fail.push('third brand typeface DM Mono must not be used');
if(!css.includes('--navy:#121E36')||!css.includes('--gold:#C9A84C')) fail.push('canonical brand colors missing');
if(fail.length){console.error('BRAND SYSTEM VALIDATION FAILED');fail.forEach(x=>console.error(' - '+x));process.exit(1)}
console.log('PASS: Concerto Brand & Product Standards v1.1 - unified Playfair hierarchy / DM Sans function');
