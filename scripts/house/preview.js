const { chromium } = require('playwright'); const fs=require('fs');
const repo=process.argv[2], slug=process.argv[3];
(async()=>{const m=JSON.parse(fs.readFileSync(`${repo}/data/house/${slug}.json`));
const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1000,height:800}});
for(const l of m.levels){const svg=fs.readFileSync(repo+l.image,'utf8');
 const col={stand:'#d9480f',bar:'#7048e8',restroom:'#1c7ed6',gate:'#2b8a3e',merch:'#e64980',guest_services:'#0b7285',first_aid:'#c92a2a',atm:'#5c940d',nursing:'#862e9c',escalator:'#495057',rideshare:'#000',box_office:'#f08c00'};
 const pins=m.points.filter(q=>q.level===l.id).map(q=>`<div title="${q.name}" style="position:absolute;left:${q.x*100}%;top:${q.y*100}%;width:9px;height:9px;margin:-4.5px;border-radius:50%;background:${col[q.kind]};border:1px solid #fff"></div>`).join('');
 await p.setContent(`<div style="position:relative;width:1000px">${svg.replace('<svg','<svg style="width:1000px;display:block"')}${pins}</div>`);
 await p.screenshot({path:`${process.argv[4]}/prev-${slug}-${l.id}.png`,fullPage:true});}
await b.close();})();
