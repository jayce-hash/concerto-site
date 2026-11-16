const { open, BASE, clean, scrollMain, tap } = require('./lib');
const only = process.argv[2];
const D = { id: 'ChIJ-blessed', kind: 'eat', name: 'Blessed Kitchen', when: 'before', time: 17 * 60, distance_mi: 0.37, address: 'Inglewood, CA' };
const filled = { travel: 'rideshare', bag: 'small', seat: { section: 'C26', row: '17', seat: '7' }, ticket: 'wallet', setupDone: true, stops: [D], updatedAt: new Date().toISOString() };
const planned = { ...filled, stops: [{ ...D, why: 'The closest sit-down dinner to the doors, a 7-minute walk.' }], plan: { mode: 'me', exit: 'beat', home: 'home', at: new Date().toISOString() }, tips: ['Rideshare drops off at the Mobility Hub, on the first level of the East Garage.'] };
const map = (p) => p.evaluate((src) => {
  const ton = [...document.querySelectorAll('div')].filter((e) => e.innerText && e.innerText.trim() === 'Tonight').pop(); if (!ton) return;
  const m = document.createElement('div'); m.style.cssText = `aspect-ratio:527/286;margin:-8px 16px 28px;border-radius:24px;background:url(${src}) center/cover;box-shadow:0 8px 24px rgba(18,30,54,.12)`;
  ton.parentNode.insertBefore(m, ton);
}, BASE + '/__art/map.jpg');
const shots = [
  ['home', {}, '/', 0], ['tour', {}, '/tour/olivia-rodrigo-the-unraveled-tour', 0], ['tours', {}, '/tours', 0], ['venues', {}, '/venues', 0],
  ['venue', {}, '/venue/intuit-dome', 0], ['nearme', {}, '/near-me', 0, map],
  ['pyn-start', {}, '/show/or14', 0], ['pyn-question', {}, '/show/or14', 470], ['pyn-night', { night: filled }, '/show/or14', 420],
  ['plus-home', { plus: true }, '/show/or14', 0], ['plus-planner', { night: planned, plus: true }, '/show/or14', 215],
  ['plus-exit', { night: filled, plus: true }, '/exit?show=or14', 0], ['plus-locked', {}, '/plus?feature=plan&show=or14', 0],
  ['plus-bag', { plus: true, cap: true }, '/bagcheck?show=or14', 0, (p) => p.evaluate(() => { const e = [...document.querySelectorAll('div')].filter((d) => d.innerText && d.innerText.trim() === 'Sign in on the Account tab to use Bag Check.').sort((a, b) => b.getBoundingClientRect().width - a.getBoundingClientRect().width)[0]; let n = e; while (n && n.parentElement && n.parentElement.getBoundingClientRect().height < 60) n = n.parentElement; if (n) n.style.display = 'none'; })],
];
(async () => {
  for (const [key, o, url, y, extra] of shots) {
    if (only && !only.split(',').includes(key)) continue;
    const { b, ctx, p, errs } = await open(o);
    if (o.cap) await ctx.addInitScript(() => { globalThis.__cap = true; });
    await p.goto(BASE + url); await p.waitForTimeout(3800); await clean(p);
    if (extra) await extra(p);
    if (y) { await scrollMain(p, y); }
    await p.waitForTimeout(900);
    await p.screenshot({ path: `raw/${key}.png` });
    // A screen that opens on artwork: on a phone the artwork runs up behind the status bar. Keep a
    // clean copy of its top edge (buttons hidden) so the frame can continue it.
    if (key === 'pyn-start' || key === 'plus-home') {
      await p.evaluate(() => { for (const e of document.querySelectorAll('[role=button],a,button')) { const r = e.getBoundingClientRect(); if (r.bottom < 70 && r.width < 80) e.style.visibility = 'hidden'; } });
      await p.waitForTimeout(200); await p.screenshot({ path: `raw/top/${key}.png`, clip: { x: 0, y: 0, width: 402, height: 59 } });
    }
    console.log(key, JSON.stringify(errs)); await b.close();
  }
})();
