/* ============================================================
   Concerto — Unified Venue Info component
   ONE component replacing four microsites (bag, parking, concessions, rideshare).
   • Identity + coordinates come from the registry (/data/venues.json) — single source.
   • Each feature reads its own /data file, resolved by canonical slug (with a
     normalization safety net for legacy underscore/hyphen mismatches).
   • Rideshare buttons build Uber/Lyft deep links from registry coords (no BuildFire).
   • Rideshare note falls back to parking.rideshare when the rideshare file lacks one.

   USAGE (on any venues/<slug>.html):
     <link rel="stylesheet" href="/venue-info/venue-info.css">
     <div class="cvi" data-slug="madison-square-garden"
          data-features="bag,parking,concessions,rideshare"></div>
     <script src="/venue-info/venue-info.js"></script>
   Optional: set window.CONCERTO_DATA_BASE = '/data' (default) before the script.
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
  // Resolve a slug against an object whose keys may differ in separators.
  function pick(obj, slug) {
    if (!obj) return null;
    if (obj[slug]) return obj[slug];
    const n = norm(slug);
    for (const k in obj) if (norm(k) === n) return obj[k];
    return null;
  }

  // ---- Feature renderers (return HTML string, or '' if no data) ----
  const RENDER = {
    bag(v) {
      if (!v) return '';
      let h = '';
      if (v.summary) h += card('Summary', `<p class="cvi-body">${esc(v.summary)}</p>`);
      if (Array.isArray(v.allowed) && v.allowed.length)
        h += card('Allowed', list(v.allowed), 'allow');
      if (Array.isArray(v.notAllowed) && v.notAllowed.length)
        h += card('Not Allowed', list(v.notAllowed), 'deny');
      if (v.note) h += card('Extra Notes', `<p class="cvi-body">${esc(v.note)}</p>`);
      if (v.fullLink) h += `<a class="cvi-btn" href="${esc(v.fullLink)}" target="_blank" rel="noopener noreferrer">View Official Bag Policy &rarr;</a>`;
      return section('Bag Policy', 'Know Before You Go', h);
    },
    parking(v) {
      if (!v) return '';
      let h = '';
      h += card('Parking Overview', `<p class="cvi-body">${esc(v.note || 'Parking details not available yet.')}</p>`);
      if (Array.isArray(v.lots) && v.lots.length) h += card('Key Lots', list(v.lots));
      if (v.officialParkingUrl) h += `<a class="cvi-btn" href="${esc(v.officialParkingUrl)}" target="_blank" rel="noopener noreferrer">View Official Parking Guide &rarr;</a>`;
      return section('Parking', 'Getting There', h);
    },
    concessions(v) {
      if (!v) return '';
      let h = '';
      h += card('Concessions Overview', `<p class="cvi-body">${esc(v.note || 'Concessions details not available yet.')}</p>`);
      if (Array.isArray(v.stands) && v.stands.length) h += card('Notable Stands', list(v.stands));
      if (v.officialConcessionsUrl) h += `<a class="cvi-btn" href="${esc(v.officialConcessionsUrl)}" target="_blank" rel="noopener noreferrer">View Official Concessions Guide &rarr;</a>`;
      return section('Concessions', 'Inside the Venue', h);
    },
    // rideshare needs registry coords + parking fallback, handled in render()
  };

  function card(label, inner, cls) {
    return `<div class="cvi-card"><div class="cvi-card-label ${cls||''}">${esc(label)}</div>${inner}</div>`;
  }
  function list(arr) { return `<ul class="cvi-list">${arr.map(i => `<li>${esc(i)}</li>`).join('')}</ul>`; }
  function section(title, eyebrow, body) {
    if (!body) return '';
    return `<div class="cvi-section"><div class="cvi-section-head">
      <span class="cvi-section-title">${esc(title)}</span>
      <span class="cvi-section-eyebrow">${esc(eyebrow)}</span></div>${body}</div>`;
  }

  function rideshareSection(rideV, parkV, venue) {
    // note: rideshare file → fallback to parking.rideshare
    let note = (rideV && rideV.note) || (parkV && parkV.rideshare) || '';
    if (/^no specific rideshare/i.test(note)) note = '';
    let h = '';
    if (note) h += card('Rideshare Information', `<p class="cvi-body">${esc(note)}</p>`);
    if (venue && venue.lat != null && venue.lng != null) {
      const lat = encodeURIComponent(venue.lat), lng = encodeURIComponent(venue.lng), nm = encodeURIComponent(venue.name || 'Venue');
      const uTo = `https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[latitude]=${lat}&dropoff[longitude]=${lng}&dropoff[nickname]=${nm}`;
      const uFrom = `https://m.uber.com/ul/?action=setPickup&pickup[latitude]=${lat}&pickup[longitude]=${lng}&pickup[nickname]=${nm}`;
      const lTo = `https://ride.lyft.com/?destination[latitude]=${lat}&destination[longitude]=${lng}`;
      const lFrom = `https://ride.lyft.com/?pickup[latitude]=${lat}&pickup[longitude]=${lng}`;
      h += card('Use Rideshare Apps',
        `<div class="cvi-ride-grid">
          <a class="cvi-btn" target="_blank" rel="noopener noreferrer" href="${uTo}">Uber to Venue</a>
          <a class="cvi-btn" target="_blank" rel="noopener noreferrer" href="${uFrom}">Uber from Venue</a>
          <a class="cvi-btn" target="_blank" rel="noopener noreferrer" href="${lTo}">Lyft to Venue</a>
          <a class="cvi-btn" target="_blank" rel="noopener noreferrer" href="${lFrom}">Lyft from Venue</a>
        </div>`);
    }
    return section('Rideshare', 'Getting There & Back', h);
  }

  async function render(el) {
    const slug = el.getAttribute('data-slug');
    const feats = (el.getAttribute('data-features') || 'bag,parking,concessions,rideshare')
      .split(',').map(s => s.trim()).filter(Boolean);
    if (!slug) return;

    const reg = await loadJSON('venues.json') || [];
    const venue = reg.find(v => v.id === slug) || reg.find(v => norm(v.id) === norm(slug)) || null;

    const files = { bag: 'bag_policies.json', parking: 'parking.json', concessions: 'concessions.json', rideshare: 'rideshare.json' };
    const need = new Set(feats);
    if (need.has('rideshare')) need.add('parking'); // for fallback
    const data = {};
    await Promise.all([...need].map(async f => { data[f] = pick(await loadJSON(files[f]), slug); }));

    let html = '';
    for (const f of feats) {
      if (f === 'rideshare') html += rideshareSection(data.rideshare, data.parking, venue);
      else if (RENDER[f]) html += RENDER[f](data[f]);
    }
    el.innerHTML = html || `<p class="cvi-empty">Venue info for “${esc(slug)}” isn’t available yet.</p>`;
  }

  function init() { document.querySelectorAll('.cvi[data-slug]').forEach(render); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.ConcertoVenueInfo = { render: el => render(el), init };
})();
