#!/usr/bin/env node
// Every internal href on every page must resolve to a real file or a _redirects rule.
const fs=require('fs'),path=require('path');const root=path.resolve(__dirname,'..');
const rules=fs.readFileSync(path.join(root,'_redirects'),'utf8').split('\n').map(l=>l.split('#')[0].trim()).filter(Boolean).map(l=>l.split(/\s+/));
const isFile=p=>{const f=path.join(root,p.replace(/^\//,''));return fs.existsSync(f)&&fs.statSync(f).isFile();};
function match(p){for(const r of rules){const [from]=r;if(from===p)return r;if(from.endsWith('/*')){const base=from.slice(0,-2);if(p===base||p.startsWith(base+'/'))return r;}}return null;}
function resolves(p,depth=0){p=p.split('?')[0].split('#')[0];if(p==='/')return true;if(depth>4)return false;
  const r=match(p);const forced=r&&/!$/.test(r[2]||'');
  if(!forced&&isFile(p))return true;            // Netlify serves a real file before any unforced rule
  if(!r)return isFile(p+'.html')&&false;        // no rule and no file: broken (pretty URLs are not relied on)
  let [from,to,code='301']=r;code=code.replace('!','');
  if(from.endsWith('/*')){const base=from.slice(0,-2);const splat=p===base?'':p.slice(base.length+1);to=to.replace(':splat',splat);}
  if(code==='200'||code==='404')return isFile(to)||isFile(to+'.html')&&false;
  if(to.startsWith('http'))return true;
  return resolves(to,depth+1);}
const pages=[];for(const d of ['.','venue','tour','setlist']){const dir=path.join(root,d);if(!fs.existsSync(dir))continue;for(const f of fs.readdirSync(dir))if(f.endsWith('.html'))pages.push(path.join(d,f));}
const bad=new Map();let total=0;
for(const pg of pages){const h=fs.readFileSync(path.join(root,pg),'utf8');for(const m of h.matchAll(/href="(\/[^"]*)"/g)){total++;if(!resolves(m[1])){if(!bad.has(m[1]))bad.set(m[1],pg);}}}
if(bad.size){console.error('LINK VALIDATION FAILED');for(const [l,pg]of bad)console.error(` - ${l} (first seen in ${pg})`);process.exit(1);}
console.log(`PASS: links | ${total} internal links across ${pages.length} pages all resolve`);
