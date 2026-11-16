// Puts each capture inside an iPhone: bezel, Dynamic Island, status bar and home indicator.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const sharp = (() => { try { return require('sharp'); } catch { return null; } })();
const KEYS = fs.readdirSync(path.join(__dirname, 'raw')).filter((f) => /^[a-z-]+\.png$/.test(f) && !/^(s\d|z)\.png$/.test(f)).map((f) => f.replace('.png', ''));
const html = (src) => `<!doctype html><meta charset=utf-8><style>
*{box-sizing:border-box;margin:0}html,body{background:transparent}
body{width:438px;height:902px;font-family:-apple-system,"SF Pro Text","DM Sans","Helvetica Neue",Arial,sans-serif}
.ph{position:absolute;left:4px;top:0;width:430px;height:902px;border-radius:66px;background:linear-gradient(135deg,#55565a,#1d1d1f 22%,#2b2b2e 55%,#4a4b4f 100%);padding:3px}
.in{width:100%;height:100%;border-radius:63px;background:#050506;padding:11px}
.sc{position:relative;width:402px;height:874px;border-radius:52px;overflow:hidden;background:var(--top)}
.sc img{position:absolute;left:0;top:59px;width:402px;height:815px;display:block}
.sb{position:absolute;inset:0 0 auto 0;height:59px;transform:scaleY(-1);color:var(--ink);font-weight:600;font-size:17px;letter-spacing:-.2px}
.sb .t{position:absolute;left:52px;bottom:20px;transform:scaleY(-1)}.sb .r{position:absolute;right:30px;bottom:22px;display:flex;gap:6px;align-items:center;transform:scaleY(-1)}
.di{position:absolute;left:50%;top:12px;width:124px;height:36px;margin-left:-62px;border-radius:20px;background:#000}
.hi{position:absolute;left:50%;bottom:8px;width:140px;height:5px;margin-left:-70px;border-radius:3px;background:var(--bar)}
.bt{position:absolute;width:4px;border-radius:2px;background:#2a2a2d}
</style><div class=bt style="left:1px;top:178px;height:34px"></div><div class=bt style="left:1px;top:240px;height:62px"></div><div class=bt style="left:1px;top:318px;height:62px"></div><div class=bt style="right:1px;top:280px;height:100px"></div>
<div class=ph><div class=in><div class=sc id=sc><img id=im src="${src}">
<div class=sb><span class=t>9:41</span><span class=r>
<svg width="18" height="12" viewBox="0 0 18 12" fill="currentColor"><rect x="0" y="8" width="3" height="4" rx=".8"></rect><rect x="5" y="5.5" width="3" height="6.5" rx=".8"></rect><rect x="10" y="3" width="3" height="9" rx=".8"></rect><rect x="15" y="0" width="3" height="12" rx=".8"></rect></svg>
<svg width=17 height=12 viewBox="0 0 17 12" fill=none stroke=currentColor stroke-width=1.9 stroke-linecap=round><path d="M1.2 4.2a10.4 10.4 0 0 1 14.6 0"/><path d="M3.9 6.9a6.6 6.6 0 0 1 9.2 0"/><circle cx=8.5 cy=10 r=1.3 fill=currentColor stroke=none /></svg>
<svg width=27 height=13 viewBox="0 0 27 13" fill=none><rect x=.5 y=.5 width=23 height=12 rx=3.8 stroke=currentColor opacity=.4 /><rect x=2 y=2 width=20 height=9 rx=2.4 fill=currentColor /><path d="M25 4.4v4.2c.9-.3 1.5-1.1 1.5-2.1s-.6-1.8-1.5-2.1z" fill=currentColor opacity=.45 /></svg>
</span></div><div class=di></div><div class=hi></div></div></div></div>`;
(async () => {
  const b = await chromium.launch(); const c = await b.newContext({ viewport: { width: 438, height: 902 }, deviceScaleFactor: 1.5 }); const p = await c.newPage();
  fs.mkdirSync(path.join(__dirname, 'framed'), { recursive: true });
  for (const k of KEYS) {
    const src = 'data:image/png;base64,' + fs.readFileSync(path.join(__dirname, 'raw', k + '.png')).toString('base64');
    await p.setContent(html(src)); const tp = path.join(__dirname, 'raw', 'top', k + '.png'); await p.evaluate((t) => { window.__top = t; }, fs.existsSync(tp) ? 'data:image/png;base64,' + fs.readFileSync(tp).toString('base64') : null); await p.waitForFunction(() => document.getElementById('im').complete);
    await p.evaluate(() => { const im = document.getElementById('im'); const cv = document.createElement('canvas'); cv.width = im.naturalWidth; cv.height = im.naturalHeight; const x = cv.getContext('2d'); x.drawImage(im, 0, 0);
      const px = (yy) => { const d = x.getImageData(Math.round(cv.width / 2), yy, 1, 1).data; return d; }; const lum = (d) => (0.299 * d[0] + 0.587 * d[1] + 0.114 * d[2]);
      const t = x.getImageData(6, 2, 1, 1).data, bt = px(cv.height - 30); const sc = document.getElementById('sc');
      sc.style.setProperty('--top', `rgb(${t[0]},${t[1]},${t[2]})`); if (window.__top) document.querySelector('.sb').style.background = `url(${window.__top}) 0 0/402px 59px`; sc.style.setProperty('--ink', lum(t) < 140 ? '#fff' : '#000'); sc.style.setProperty('--bar', lum(bt) < 140 ? 'rgba(255,255,255,.9)' : 'rgba(0,0,0,.85)'); });
    await p.screenshot({ path: path.join(__dirname, 'framed', k + '.png'), omitBackground: true });
  }
  await b.close(); console.log(KEYS.join(' '));
})();
