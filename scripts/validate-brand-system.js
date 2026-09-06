const fs=require('fs'),path=require('path'); const root=path.resolve(__dirname,'..'); const fail=[];
const css=fs.readFileSync(path.join(root,'css/company.css'),'utf8');
if(!fs.existsSync(path.join(root,'CONCERTO-BRAND-AND-PRODUCT-STANDARDS.md'))) fail.push('brand standards missing');
if(/\.navlinks a\{[^}]*text-transform:uppercase/.test(css)) fail.push('corporate navigation must be Title Case');
if(!/\.card h3\{font-family:var\(--body\)/.test(css)) fail.push('corporate card titles must use DM Sans');
if(!css.includes('--navy:#121E36')||!css.includes('--gold:#C9A84C')) fail.push('canonical brand colors missing');
if(fail.length){console.error('BRAND SYSTEM VALIDATION FAILED');fail.forEach(x=>console.error(' - '+x));process.exit(1)}
console.log('PASS: Concerto Brand & Product Standards v1.0 enforced in corporate web CSS');
