/* ============================================================
   Concerto — Unified Venue Info component
   One component renders bag / parking / concessions / rideshare as
   native-style cards inline on a venue page. Identity + coordinates
   come from /data/venues.json; each feature reads its own /data file.
   Usage:
     <link rel="stylesheet" href="/venue-info/venue-info.css">
     <div class="cvi" data-slug="madison-square-garden"
          data-features="bag,parking,concessions,rideshare"></div>
     <script src="/venue-info/venue-info.js"></script>
   ============================================================ */
(function () {
  const DATA_BASE = (window.CONCERTO_DATA_BASE || '/data').replace(/\/$/, '');
  const norm = s => String(s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const esc = s => String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

  const cache = {};
  async function loadJSON(name) {
    if (cache[name] !== undefined) return cache[name];
    try { const r = await fetch(`${DATA_BASE}/${name}`); cache[name] = r.ok ? await r.json() : null; }
    catch (e) { cache[name] = null; }
    return cache[name];
  }
  function pick(obj, slug) {
    if (!obj) return null;
    if (obj[slug]) return obj[slug];
    const n = norm(slug);
    for (const k in obj) if (norm(k) === n) return obj[k];
    return null;
  }

  // ---- building blocks ----
  const FEAT_ID = { 'Bag Policy':'bag', 'Parking':'parking', 'Concessions':'concessions', 'Rideshare':'rideshare' };
  const feature = (eyebrow, title, body) => !body ? '' :
    `<section class="cvi-feature" id="${FEAT_ID[title] || ''}"><div class="cvi-feature-head">
      <span class="cvi-eyebrow">${esc(eyebrow)}</span>
      <h2 class="cvi-title">${esc(title)}</h2></div>${body}</section>`;
  const block = (label, inner, cls='') =>
    `<div class="cvi-block"><span class="cvi-block-label ${cls}">${esc(label)}</span>${inner}</div>`;
  const list = arr => `<ul class="cvi-list">${arr.map(i => `<li>${esc(i)}</li>`).join('')}</ul>`;
  const cta  = (href, text) =>
    `<a class="cvi-cta" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(text)} &rarr;</a>`;

  const RENDER = {
    bag(v) {
      if (!v) return '';
      let b = '';
      if (v.summary) b += `<p class="cvi-desc">${esc(v.summary)}</p>`;
      const sub = [];
      if (Array.isArray(v.allowed) && v.allowed.length)
        sub.push(`<div class="cvi-subcard"><span class="cvi-block-label allow">Allowed</span>${list(v.allowed)}</div>`);
      if (Array.isArray(v.notAllowed) && v.notAllowed.length)
        sub.push(`<div class="cvi-subcard"><span class="cvi-block-label deny">Not Allowed</span>${list(v.notAllowed)}</div>`);
      if (sub.length) b += `<div class="cvi-subgrid">${sub.join('')}</div>`;
      if (v.note) b += block('Extra Notes', `<p class="cvi-desc">${esc(v.note)}</p>`);
      if (v.fullLink) b += cta(v.fullLink, 'View Full Policy');
      return feature('Know Before You Go', 'Bag Policy', b);
    },
    parking(v) {
      if (!v) return '';
      let b = `<p class="cvi-desc">${esc(v.note || 'Parking details for this venue are not available yet.')}</p>`;
      if (Array.isArray(v.lots) && v.lots.length) b += block('Key Lots', list(v.lots));
      if (v.officialParkingUrl) b += cta(v.officialParkingUrl, 'View Official Parking Guide');
      return feature('Getting There', 'Parking', b);
    },
    concessions(v) {
      if (!v) return '';
      let b = `<p class="cvi-desc">${esc(v.note || 'Concessions details for this venue are not available yet.')}</p>`;
      if (Array.isArray(v.stands) && v.stands.length) b += block('Notable Stands', list(v.stands));
      if (v.officialConcessionsUrl) b += cta(v.officialConcessionsUrl, 'View Official Concessions Guide');
      return feature('Inside the Venue', 'Concessions', b);
    },
  };

  function rideshare(rideV, parkV, venue) {
    let note = (rideV && rideV.note) || (parkV && parkV.rideshare) || '';
    if (/^no specific rideshare/i.test(note)) note = '';
    let b = '';
    if (note) b += `<p class="cvi-desc">${esc(note)}</p>`;
    if (venue && venue.lat != null && venue.lng != null) {
      const lat = encodeURIComponent(venue.lat), lng = encodeURIComponent(venue.lng),
            nm = encodeURIComponent(venue.name || 'Venue');
      const u = (q) => `https://m.uber.com/ul/?action=setPickup&${q}`;
      const links = [
        ['Uber to Venue',   u(`pickup=my_location&dropoff[latitude]=${lat}&dropoff[longitude]=${lng}&dropoff[nickname]=${nm}`)],
        ['Uber from Venue', u(`pickup[latitude]=${lat}&pickup[longitude]=${lng}&pickup[nickname]=${nm}`)],
        ['Lyft to Venue',   `https://ride.lyft.com/?destination[latitude]=${lat}&destination[longitude]=${lng}`],
        ['Lyft from Venue', `https://ride.lyft.com/?pickup[latitude]=${lat}&pickup[longitude]=${lng}`],
      ];
      const btns = links.map(([t,h]) => `<a class="cvi-btn" href="${h}" target="_blank" rel="noopener noreferrer">${t}</a>`).join('');
      b += block('Click to Open Rideshare Apps', `<div class="cvi-ride-grid">${btns}</div>`);
    }
    return feature('Uber & Lyft', 'Rideshare', b);
  }

  async function render(el) {
    const slug = el.getAttribute('data-slug');
    const feats = (el.getAttribute('data-features') || 'bag,parking,concessions,rideshare')
      .split(',').map(s => s.trim()).filter(Boolean);
    if (!slug) return;
    const reg = await loadJSON('venues.json') || [];
    const venue = reg.find(v => v.id === slug) || reg.find(v => norm(v.id) === norm(slug)) || null;
    const files = { bag:'bag_policies.json', parking:'parking.json', concessions:'concessions.json', rideshare:'rideshare.json' };
    const need = new Set(feats); if (need.has('rideshare')) need.add('parking');
    const data = {};
    await Promise.all([...need].map(async f => { data[f] = pick(await loadJSON(files[f]), slug); }));
    let html = '';
    for (const f of feats) {
      if (f === 'rideshare') html += rideshare(data.rideshare, data.parking, venue);
      else if (RENDER[f]) html += RENDER[f](data[f]);
    }
    el.innerHTML = html || `<p class="cvi-empty">Venue info for &ldquo;${esc(slug)}&rdquo; isn't available yet.</p>`;
  }

  function init(){ document.querySelectorAll('.cvi[data-slug]').forEach(render); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
  window.ConcertoVenueInfo = { render, init };
})();
