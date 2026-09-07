#!/usr/bin/env node
// Every internal href on every page must resolve to a real file or a _redirects rule.
const fs=require('fs'),path=require('path');const root=path.resolve(__dirname,'..');
const rules=fs.readFileSync(path.join(root,'_redirects'),'utf8').split('\n').map(l=>l.split('#')[0].trim()).filter(Boolean).map(l=>l.split(/\s+/));
function resolves(p){p=p.split('?')[0].split('#')[0];if(p==='/')return true;
  const f=path.join(root,p.replace(/^\//,''));if(fs.existsSync(f)&&fs.statSync(f).isFile())return true;
  for(const [from,to]of rules){if(from===p)return true;if(from.endsWith('/*')&&p.startsWith(from.slice(0,-1)))return true;}
  return false;}
const pages=[];for(const d of ['.','venue','tour','setlist']){const dir=path.join(root,d);if(!fs.existsSync(dir))continue;for(const f of fs.readdirSync(dir))if(f.endsWith('.html'))pages.push(path.join(d,f));}
const bad=new Map();let total=0;
for(const pg of pages){const h=fs.readFileSync(path.join(root,pg),'utf8');for(const m of h.matchAll(/href="(\/[^"]*)"/g)){total++;if(!resolves(m[1])){if(!bad.has(m[1]))bad.set(m[1],pg);}}}
if(bad.size){console.error('LINK VALIDATION FAILED');for(const [l,pg]of bad)console.error(` - ${l} (first seen in ${pg})`);process.exit(1);}
console.log(`PASS: links | ${total} internal links across ${pages.length} pages all resolve`);
