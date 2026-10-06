/* Maps: Apple Maps first on Apple devices (iPhone, iPad, Mac), Google Maps everywhere else. */
var CC_APPLE = /iPhone|iPad|iPod|Macintosh/.test((typeof navigator !== 'undefined' && navigator.userAgent) || '');
function ccMapsUrl(query, lat, lng, directions) {
  var q = encodeURIComponent(query || ''), at = (lat != null && lng != null) ? lat + ',' + lng : '';
  if (CC_APPLE) return 'https://maps.apple.com/?' + (directions ? 'daddr=' + (at || q) + (at ? '&q=' + q : '') : 'q=' + q + (at ? '&ll=' + at : ''));
  return 'https://www.google.com/maps/search/?api=1&query=' + q;
}
document.addEventListener('DOMContentLoaded', function () {
  if (!CC_APPLE) return;
  [].forEach.call(document.querySelectorAll('a[data-apple-maps]'), function (a) { a.href = a.getAttribute('data-apple-maps'); });
});
/* Concerto public web V6 behavior.
 *
 * The header and footer are real HTML on every page (scripts/public_chrome.py).
 * This file only wires the menu button, loads photos the same way the iPhone
 * app does, and powers the search and filter inputs.
 *
 * Photo resolution mirrors src/data/queries.ts in concerto-native:
 *   Artist  -> tm/attractions.json (exact name, then contains) -> monogram.
 *              No events fallback: that is how the wrong artist's photo used
 *              to land on a tile.
 *   Venue   -> static cityguide image -> venue-photo (Google Places, coordinate
 *              verified) -> tm/venues.json -> monogram.
 * Photos are only requested for cards near the viewport, a few at a time, so
 * a 346-card catalog does not fire 346 Google calls on load.
 */
(function () {
  'use strict';
  var FN = '/.netlify/functions';
  var DAY = 86400000;

  function safeHttps(u) { try { var p = new URL(String(u || '')); return p.protocol === 'https:' && !p.username && !p.password ? p.href : ''; } catch (e) { return ''; } }
  function norm(s) { return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
  function initial(s) { var t = String(s || '').trim(); return t ? t.charAt(0).toUpperCase() : 'C'; }
  function getJSON(url) {
    return fetch(url, { headers: { Accept: 'application/json' } }).then(function (r) {
      if (!r.ok) { var e = new Error(r.status + ' ' + url); e.status = r.status; throw e; }
      return r.json();
    });
  }
  function bestImage(images) {
    if (!images || !images.length) return null;
    var wide = images.filter(function (i) { return i.ratio === '16_9'; });
    var pool = (wide.length ? wide : images).slice().sort(function (a, b) { return (b.width || 0) - (a.width || 0); });
    return pool[0] && pool[0].url || null;
  }

  /* ---------- small cache: real answers only, never failures ---------- */
  function store(kind) { try { return kind === 'local' ? window.localStorage : window.sessionStorage; } catch (e) { return null; } }
  function cacheGet(key, kind) {
    var s = store(kind); if (!s) return undefined;
    try {
      var raw = s.getItem(key); if (!raw) return undefined;
      var v = JSON.parse(raw);
      if (v && v.exp && v.exp < Date.now()) { s.removeItem(key); return undefined; }
      return v ? v.value : undefined;
    } catch (e) { return undefined; }
  }
  function cacheSet(key, value, ttl, kind) {
    var s = store(kind); if (!s) return;
    try { s.setItem(key, JSON.stringify({ value: value, exp: Date.now() + ttl })); } catch (e) { /* quota: ignore */ }
  }

  /* ---------- concurrency: Ticketmaster allows 5 req/s, Google costs money ---------- */
  var MAX_INFLIGHT = 4, inflight = 0, queue = [];
  function schedule(task) {
    return new Promise(function (resolve, reject) {
      queue.push(function () {
        inflight++;
        Promise.resolve().then(task).then(function (v) { resolve(v); }, function (e) { reject(e); }).then(function () { inflight--; pump(); });
      });
      pump();
    });
  }
  function pump() { while (inflight < MAX_INFLIGHT && queue.length) queue.shift()(); }

  /* ---------- resolvers (same endpoints and order as the app) ---------- */
  function artistImage(artist) {
    var key = 'concerto:artist-image-v3:' + norm(artist);
    var hit = cacheGet(key, 'local');
    if (hit !== undefined) return Promise.resolve(hit);
    var params = new URLSearchParams({ keyword: artist, classificationName: 'Music', size: '10' });
    return schedule(function () { return getJSON(FN + '/tm/attractions.json?' + params); }).then(function (data) {
      var list = data && data._embedded && data._embedded.attractions || [];
      var target = norm(artist);
      var exact = list.find(function (a) { return a.name && norm(a.name) === target; });
      var contains = list.find(function (a) { return a.name && norm(a.name).indexOf(target) !== -1; });
      var match = exact || contains;
      var src = match ? bestImage(match.images) : null;
      if (src) cacheSet(key, src, 30 * DAY, 'local');
      return src;
    });
  }

  function googleVenuePhoto(v) {
    var key = 'concerto:google-venue-photo-v2:' + norm(v.name) + '|' + norm(v.city);
    var hit = cacheGet(key, 'session');
    if (hit !== undefined) return Promise.resolve(hit);
    var params = new URLSearchParams({ name: v.name, city: v.city || '', lat: v.lat || '', lng: v.lng || '' });
    return schedule(function () { return getJSON(FN + '/venue-photo?' + params); }).then(function (d) {
      var val = d && d.src ? { src: d.src, credit: d.credit || '' } : null;
      cacheSet(key, val, 15 * 60 * 1000, 'session');
      return val;
    }, function (e) {
      // 404 = coordinate-verified "no photo": a real answer, keep it for the session.
      if (e && e.status === 404) { cacheSet(key, null, 15 * 60 * 1000, 'session'); return null; }
      throw e;
    });
  }

  function tmVenueImage(name) {
    var key = 'concerto:tm-venue-image-v2:' + norm(name);
    var hit = cacheGet(key, 'local');
    if (hit !== undefined) return Promise.resolve(hit);
    var params = new URLSearchParams({ keyword: name, size: '1' });
    return schedule(function () { return getJSON(FN + '/tm/venues.json?' + params); }).then(function (data) {
      var vs = data && data._embedded && data._embedded.venues || [];
      var src = bestImage(vs[0] && vs[0].images) || null;
      cacheSet(key, src, 30 * DAY, 'local');
      return src;
    });
  }

  /* ---------- painting ---------- */
  function showPhoto(el, src, alt, credit) {
    return new Promise(function (resolve) {
      var img = new Image();
      img.className = 'dynamic-photo';
      img.alt = alt || '';
      img.decoding = 'async';
      img.onload = function () {
        el.querySelectorAll('.dynamic-photo, .fallback-mark, .photo-credit').forEach(function (n) { n.remove(); });
        el.classList.remove('is-loading', 'image-fallback');
        el.classList.add('has-photo');
        el.insertBefore(img, el.firstChild);
        if (credit) { var c = document.createElement('span'); c.className = 'photo-credit'; c.textContent = credit; el.appendChild(c); }
        requestAnimationFrame(function () { img.classList.add('is-ready'); });
        resolve(true);
      };
      img.onerror = function () { resolve(false); };
      img.src = src; // no loading="lazy": a detached lazy image never loads
    });
  }
  function showMonogram(el, label) {
    el.classList.remove('is-loading');
    el.classList.add('image-fallback');
    if (!el.querySelector('.fallback-mark')) {
      var m = document.createElement('span');
      m.className = 'fallback-mark';
      m.setAttribute('aria-hidden', 'true');
      m.textContent = initial(label);
      el.insertBefore(m, el.firstChild);
    }
  }
  function tryChain(el, label, steps) {
    // steps: functions returning Promise<string|{src,credit}|null>. First real photo wins.
    var i = 0;
    function next() {
      if (i >= steps.length) { showMonogram(el, label); return; }
      var step = steps[i++];
      Promise.resolve().then(step).then(function (res) {
        var src = res && (res.src || res), credit = res && res.credit;
        if (!src) return next();
        return showPhoto(el, src, label, credit).then(function (ok) { if (!ok) next(); });
      }).catch(function () { next(); });
    }
    next();
  }

  function loadArtist(el) {
    var artist = el.getAttribute('data-artist');
    if (!artist) return showMonogram(el, 'C');
    el.classList.add('is-loading');
    tryChain(el, artist, [function () { return artistImage(artist); }]);
  }
  function loadVenue(el) {
    var v = { name: el.getAttribute('data-vname') || '', city: el.getAttribute('data-vcity') || '', lat: el.getAttribute('data-vlat') || '', lng: el.getAttribute('data-vlng') || '' };
    var staticSrc = el.getAttribute('data-fallback-src');
    if (!v.name) return showMonogram(el, 'C');
    el.classList.add('is-loading');
    var steps = [];
    if (staticSrc) steps.push(function () { return staticSrc; });
    steps.push(function () { return googleVenuePhoto(v); });
    steps.push(function () { return tmVenueImage(v.name); });
    tryChain(el, v.name, steps);
  }

  /* Only fetch for cards that are near the viewport, like the app's on-screen rows. */
  function watchPhotos() {
    var nodes = [].slice.call(document.querySelectorAll('[data-artist],[data-vphoto]'));
    if (!nodes.length) return;
    function start(el) {
      if (el.dataset.photoStarted) return;
      el.dataset.photoStarted = '1';
      if (el.hasAttribute('data-vphoto')) loadVenue(el); else loadArtist(el);
    }
    if (!('IntersectionObserver' in window)) { nodes.forEach(start); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { io.unobserve(en.target); start(en.target); } });
    }, { rootMargin: '400px 0px' });
    nodes.forEach(function (n) { io.observe(n); });
  }

  /* ---------- header ---------- */
  function wireHeader() {
    var header = document.querySelector('header.site-header');
    if (!header) return;
    var btn = header.querySelector('.menu-btn'), menu = header.querySelector('.mobile-nav');
    if (!btn || !menu) return;
    function setOpen(open) {
      menu.hidden = !open;
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      document.body.classList.toggle('menu-open', open);
    }
    btn.addEventListener('click', function () { setOpen(menu.hidden); });
    document.addEventListener('click', function (e) { if (!menu.hidden && !header.contains(e.target)) setOpen(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) { setOpen(false); btn.focus(); } });
    var mq = window.matchMedia('(min-width: 961px)');
    (mq.addEventListener ? mq.addEventListener('change', onChange) : mq.addListener(onChange));
    function onChange(e) { if (e.matches) setOpen(false); }
    var scrolled = false;
    window.addEventListener('scroll', function () { var s = window.scrollY > 8; if (s !== scrolled) { scrolled = s; header.classList.toggle('is-scrolled', s); } }, { passive: true });
  }

  /* ---------- catalog filter inputs ---------- */
  function wireFilters() {
    document.querySelectorAll('[data-filter-target]').forEach(function (input) {
      var sel = input.getAttribute('data-filter-target');
      var items = [].slice.call(document.querySelectorAll(sel));
      if (!items.length) return;
      var grid = items[0].parentElement, empty = null, timer = null;
      var haystack = items.map(function (it) { return norm(it.textContent); });
      function apply() {
        var q = norm(input.value), shown = 0;
        items.forEach(function (it, i) { var show = !q || haystack[i].indexOf(q) !== -1; it.hidden = !show; if (show) shown++; });
        if (!shown) {
          if (!empty) { empty = document.createElement('div'); empty.className = 'catalog-empty'; grid.appendChild(empty); }
          empty.textContent = 'Nothing matches "' + input.value.trim() + '" yet. Try a broader artist, venue, or city.';
          empty.hidden = false;
        } else if (empty) empty.hidden = true;
      }
      input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(apply, 80); });
      var q0 = new URLSearchParams(location.search).get('q'); if (q0) { input.value = q0; apply(); }
    });
  }

  /* ---------- site search page ---------- */
  function wireSearch() {
    var input = document.querySelector('[data-site-search]'), results = document.querySelector('[data-site-search-results]');
    if (!input || !results) return;
    var index = [];
    Promise.all([getJSON('/search-index.json').catch(function () { return {}; }), getJSON('/setlists.json').catch(function () { return {}; })]).then(function (all) {
      var d = all[0] || {}, raw = all[1] || {};
      if (Array.isArray(d)) index = d;
      else index = (d.venues || []).map(function (v) { return { title: v.name, subtitle: [v.type, v.city].filter(Boolean).join(' · '), type: 'Venue', url: '/venue/' + v.slug }; })
        .concat((d.tours || []).map(function (t) { return { title: t.artist || t.name, subtitle: t.name || '', type: 'Tour', url: '/tour/' + t.slug }; }));
      var setlists = Array.isArray(raw) ? raw : Object.keys(raw).map(function (slug) { var x = Object.assign({}, raw[slug]); x.slug = slug; return x; });
      setlists.forEach(function (s) {
        if (!Array.isArray(s.songs) || !s.songs.length) return;
        var slug = s.slug || s.tourSlug || s.id; if (!slug) return;
        index.push({ title: s.artist || s.name || 'Setlist', subtitle: (s.tour || s.tourName || s.name || '') + ' · ' + s.songs.length + ' songs', type: 'Setlist', url: '/setlist/' + slug });
      });
      index.forEach(function (x) { x._n = norm([x.title, x.subtitle, x.type, x.city].filter(Boolean).join(' ')); });
      render();
    });
    function esc(s) { return String(s || '').replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function render() {
      var q = norm(input.value);
      results.innerHTML = '';
      if (!q) { results.innerHTML = '<div class="search-empty">Try an artist, tour, venue, city, or setlist.</div>'; return; }
      var hits = index.filter(function (x) { return x._n && x._n.indexOf(q) !== -1; }).slice(0, 30);
      if (!hits.length) { results.innerHTML = '<div class="search-empty">No match yet. Try a broader artist, venue, or city.</div>'; return; }
      results.innerHTML = hits.map(function (x) {
        return '<a class="search-result" href="' + esc(x.url || '#') + '"><span class="search-result-type">' + esc(x.type || 'Concerto') + '</span><strong>' + esc(x.title) + '</strong><span>' + esc(x.subtitle || x.city || '') + '</span></a>';
      }).join('');
    }
    var q0 = new URLSearchParams(location.search).get('q'); if (q0) input.value = q0;
    input.addEventListener('input', render);
    render();
  }


  /* ---------- Live: shows near the visitor, same Ticketmaster query as the app ---------- */
  function fmtDay(d) {
    var t = new Date(d + 'T12:00:00'); var now = new Date(); now.setHours(12, 0, 0, 0);
    var diff = Math.round((t - now) / 86400000);
    if (diff === 0) return 'Tonight'; if (diff === 1) return 'Tomorrow';
    return t.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  }
  function eventCard(ev) {
    var v = ev._embedded && ev._embedded.venues && ev._embedded.venues[0] || {};
    var img = bestImage(ev.images); var day = ev.dates && ev.dates.start && ev.dates.start.localDate || '';
    var time = ev.dates && ev.dates.start && ev.dates.start.localTime ? new Date('1970-01-01T' + ev.dates.start.localTime).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : '';
    // The card is Concerto's: tapping it opens the show in the app (or the App Store).
    // The ticket provider is a secondary link, never the click that leaves the site.
    var store = document.querySelector('.header-cta') ? document.querySelector('.header-cta').getAttribute('href') : 'https://apps.apple.com/us/app/concerto-show-go/id6744903414';
    var a = document.createElement('a'); a.className = 'live-card'; a.href = store; a.rel = 'noopener';
    a.setAttribute('data-app-link', 'concerto://show/' + encodeURIComponent(ev.id || ''));
    a.innerHTML = (img ? '<img alt="" loading="lazy" decoding="async">' : '<span class="live-mono">' + initial(ev.name) + '</span>') +
      '<div class="live-copy"><span class="live-day"></span><h3></h3><p></p><span class="live-actions"><span class="live-primary">Open in Concerto</span></span></div>';
    if (img) a.querySelector('img').src = img;
    a.querySelector('.live-day').textContent = day ? fmtDay(day) : '';
    a.querySelector('h3').textContent = ev.name || '';
    // Ticketmaster's start time is the SHOW time: always labeled, never shown bare, since a bare
    // "8:00 PM" reads as doors. Doors appear only when the ticketing record publishes them.
    var clock = function (lt) { return new Date('1970-01-01T' + lt).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }); };
    var doorsAt = ev.doorsTimes && ev.doorsTimes.localTime ? clock(ev.doorsTimes.localTime) : '';
    var when = ev.dates && ev.dates.start && ev.dates.start.timeTBA ? 'Time to be announced'
      : [doorsAt ? 'Doors ' + doorsAt : null, time ? 'Show ' + time : null].filter(Boolean).join(' · ');
    a.querySelector('p').textContent = [v.name, when].filter(Boolean).join(' · ');
    if (ev.url && /^https:\/\//.test(ev.url)) {
      var t = document.createElement('a'); t.className = 'live-tickets'; t.href = ev.url; t.target = '_blank'; t.rel = 'noopener nofollow'; t.textContent = 'Tickets';
      t.addEventListener('click', function (e) { e.stopPropagation(); });
      a.querySelector('.live-actions').appendChild(t);
    }
    return a;
  }
  function loadNear(opts) {
    var rail = document.querySelector('[data-live-rail]'); if (!rail) return;
    var now = new Date(); var end = new Date(now.getTime() + 7 * DAY);
    var params = new URLSearchParams({ size: '12', sort: 'date,asc', classificationName: 'Music', startDateTime: now.toISOString().split('.')[0] + 'Z', endDateTime: end.toISOString().split('.')[0] + 'Z' });
    if (opts.country) params.set('countryCode', opts.country);
    if (opts.city) params.set('city', opts.city); else if (opts.lat) { params.set('latlong', opts.lat + ',' + opts.lng); params.set('radius', '75'); params.set('unit', 'miles'); }
    getJSON(FN + '/tm/events.json?' + params).then(function (d) {
      var list = d && d._embedded && d._embedded.events || [];
      var seen = {}; list = list.filter(function (ev) { var k = (ev.name || '') + (ev.dates && ev.dates.start && ev.dates.start.localDate); if (seen[k]) return false; seen[k] = 1; return true; });
      rail.innerHTML = '';
      if (!list.length) { rail.innerHTML = '<div class="live-empty">No music shows near here in the next seven days. <a class="text-link" href="/near-me">See upcoming shows</a> or try another city.</div>'; return; }
      list.slice(0, 10).forEach(function (ev) { rail.appendChild(eventCard(ev)); });
    }).catch(function () { rail.innerHTML = '<div class="live-empty">Shows near you load in a moment. <a class="text-link" href="/near-me">Open Near Me in the app</a>.</div>'; });
  }
  function wireLive() {
    var root = document.querySelector('[data-live-near]'); if (!root) return;
    var cityEl = root.querySelector('[data-live-city]'), sub = root.querySelector('[data-live-sub]'), form = root.querySelector('[data-live-form]');
    getJSON(FN + '/geo').then(function (g) {
      if (g && g.ok) { cityEl.textContent = g.city || 'you'; loadNear({ lat: g.lat, lng: g.lng, country: g.country }); }
      else { cityEl.textContent = 'Dallas'; loadNear({ city: 'Dallas' }); }
    }).catch(function () { cityEl.textContent = 'Dallas'; loadNear({ city: 'Dallas' }); });
    form.addEventListener('submit', function (e) {
      e.preventDefault(); var c = form.querySelector('input').value.trim(); if (!c) return;
      cityEl.textContent = c; sub.textContent = 'Music shows in ' + c + ', by night.';
      root.querySelector('[data-live-rail]').innerHTML = '<div class="live-skeleton"></div><div class="live-skeleton"></div><div class="live-skeleton"></div><div class="live-skeleton"></div>';
      loadNear({ city: c });
    });
  }
  /* No orphaned last word in headlines: tie the last two words together (fallback for browsers without text-wrap:balance) */
  function wireWidows() {
    if (CSS && CSS.supports && CSS.supports('text-wrap', 'balance')) return;
    document.querySelectorAll('h1, h2, h3, .lead, figcaption p').forEach(function (el) {
      if (el.children.length) return;
      var t = el.textContent.trim(); var i = t.lastIndexOf(' ');
      if (i < 0 || t.length < 24) return;
      el.textContent = t.slice(0, i) + '\u00A0' + t.slice(i + 1);
    });
  }
  /* Open in Concerto: try the app scheme, fall back to the App Store (iOS only; elsewhere the href wins) */
  function wireAppLinks() {
    var ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
    document.querySelectorAll('[data-app-link]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        if (!ios) return;
        e.preventDefault();
        var store = a.getAttribute('href'), app = a.getAttribute('data-app-link'), t0 = Date.now(), left = false;
        var onHide = function () { left = true; };
        document.addEventListener('visibilitychange', onHide, { once: true });
        window.location.href = app;
        setTimeout(function () { document.removeEventListener('visibilitychange', onHide); if (!left && !document.hidden && Date.now() - t0 < 2500) window.location.href = store; }, 1400);
      });
    });
  }
  /* Report wrong info: one tap on any venue section, setlist, or time. Fans are the verification network. */
  function wireReports() {
    var venue = (location.pathname.match(/^\/venue\/([a-z0-9-]+)/) || [])[1];
    var tour = (location.pathname.match(/^\/(?:tour|setlist)\/([a-z0-9-]+)/) || [])[1];
    if (!venue && !tour) return;
    var targets = venue ? document.querySelectorAll('.info-card[data-section]') : document.querySelectorAll('.song-list, .detail-grid');
    targets.forEach(function (card) {
      var field = card.getAttribute('data-section') || (card.classList.contains('song-list') ? 'setlist' : 'showTime');
      var a = document.createElement('button'); a.type = 'button'; a.className = 'report-link'; a.textContent = 'Report wrong info';
      a.addEventListener('click', function () {
        if (a.disabled) return;
        a.textContent = 'Sending…'; a.disabled = true;
        fetch(FN + '/report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ venue: venue || '', tour: tour || '', field: field, message: '', surface: 'web' }) })
          .then(function (r) { if (!r.ok) throw new Error(String(r.status)); a.textContent = 'Thank you. We will check it.'; a.setAttribute('aria-live', 'polite'); })
          .catch(function () { a.textContent = 'Could not send. Tap to try again.'; a.disabled = false; });
      });
      card.appendChild(a);
    });
  }
  /* Countdowns on rendered UI pieces */
  function wireCountdowns() {
    document.querySelectorAll('[data-countdown]').forEach(function (el) {
      var t = new Date(el.getAttribute('data-countdown')); if (isNaN(t)) return;
      var days = Math.floor((t - new Date()) / 86400000);
      if (days < 0) { var wrap = el.closest('.ui-count'); if (wrap) { wrap.innerHTML = '<b>Your night</b><span>example show</span>'; } else if (el.parentElement) { el.parentElement.textContent = 'Show day, planned'; } return; }
      el.textContent = String(days);
    });
  }
  /* Every live Perk at a venue, grouped by kind, in a fair daily rotation
     (same rule as the app) so no paying partner is permanently last. Builds its
     own section after the hero: venue pages have no .detail-section. */
  function rotateDaily(list, seed) {
    if (list.length < 2) return list;
    var h = 2166136261, str = new Date().toISOString().slice(0, 10) + '|' + seed;
    for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    var off = (h >>> 0) % list.length;
    return list.slice(off).concat(list.slice(0, off));
  }
  /* Concerto Partners on a venue page: the one thing a restaurant or hotel buys.
     Same card as the app: photo, name, description, the Perk if they have one,
     Reserve and Directions. Listed partners plus anyone with a live Perk here,
     one card each, rotating daily. */
  function partnerCards(perks, partners, kind) {
    var out = {}, order = [];
    (partners || []).forEach(function (o) {
      if (o.kind !== kind) return;
      out[o.id] = { id: o.id, name: o.name, kind: kind, blurb: o.blurb, address: o.address, url: safeHttps(o.url), lat: o.lat, lng: o.lng };
      order.push(o.id);
    });
    (perks || []).forEach(function (p) {
      if ((p.kind || 'restaurant') !== kind || p.tour_slug) return;
      var key = p.org_id && out[p.org_id] ? p.org_id : 'perk:' + (p.org_id || String(p.partner_name).toLowerCase());
      if (!out[key]) { out[key] = { id: key, name: p.partner_name, kind: kind, address: p.address, lat: p.lat, lng: p.lng }; order.push(key); }
      if (!out[key].perk) out[key].perk = { offer: p.offer, details: p.details, url: safeHttps(p.url) };
    });
    return order.map(function (k) { return out[k]; });
  }
  function renderVenuePerks(perks, slug, venueName, partners) {
    var hero = document.querySelector('.c-hero'); if (!hero || document.querySelector('.partner-venue')) return;
    var sec = document.createElement('section'); sec.className = 'c-section c-cream partner-venue';
    var wrap = document.createElement('div'); wrap.className = 'c-wrap'; sec.appendChild(wrap);
    var any = false;
    [{ kind: 'restaurant', eyebrow: 'Concerto Partners', title: 'Before the show.' },
     { kind: 'hotel', eyebrow: 'Concerto Partners', title: 'Where to stay.' }].forEach(function (g) {
      var list = rotateDaily(partnerCards(perks, partners, g.kind), slug + ':' + g.kind);
      if (!list.length) return; any = true;
      var eb = document.createElement('p'); eb.className = 'c-eyebrow'; eb.textContent = g.eyebrow;
      var h2 = document.createElement('h2'); h2.className = 'c-h2 c-h2-sm'; h2.textContent = g.title;
      var grid = document.createElement('div'); grid.className = 'partner-grid';
      var sub = document.createElement('p'); sub.className = 'partner-sub'; sub.textContent = 'Near ' + venueName + '.';
      if (list.length === 1) grid.className += ' is-single';
      wrap.appendChild(eb); wrap.appendChild(h2); wrap.appendChild(sub); wrap.appendChild(grid);
      list.forEach(function (c, i) { grid.appendChild(partnerCardEl(c, slug, i)); });
    });
    if (any) hero.parentNode.insertBefore(sec, hero.nextSibling);
  }
  function partnerCardEl(c, slug, i) {
    var card = document.createElement('article'); card.className = 'partner-card';
    card.innerHTML = '<div class="partner-photo"><span class="fallback-mark"></span><span class="partner-label">Concerto Partner</span></div><div class="partner-body"><h3></h3><p class="partner-blurb"></p></div>';
    card.querySelector('.fallback-mark').textContent = c.name.charAt(0);
    card.querySelector('h3').textContent = c.name;
    var bl = card.querySelector('.partner-blurb'); if (c.blurb) bl.textContent = c.blurb; else bl.remove();
    var body = card.querySelector('.partner-body');
    if (c.perk) {
      var pk = document.createElement('div'); pk.className = 'partner-perk';
      pk.innerHTML = '<span>Concerto Perk</span><strong></strong><p></p>';
      pk.querySelector('strong').textContent = c.perk.offer;
      if (c.perk.details) pk.querySelector('p').textContent = c.perk.details; else pk.querySelector('p').remove();
      // Perks are redeemed with a live code in the app, so the website points there.
      var use = document.createElement('a'); use.className = 'partner-perk-app'; use.href = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414';
      use.textContent = 'Use this Perk in the Concerto app'; use.target = '_blank'; use.rel = 'noopener'; pk.appendChild(use);
      body.appendChild(pk);
    }
    var act = document.createElement('div'); act.className = 'partner-actions';
    var reserve = (c.perk && c.perk.url) || c.url;
    var track = function (action) { if (typeof window.gtag === 'function') { try { window.gtag('event', 'partner_tap', { venue: slug, partner: c.name, partner_id: c.id, action: action, surface: 'web_venue_' + c.kind }); } catch (_) {} } };
    if (reserve) { var r = document.createElement('a'); r.className = 'partner-btn'; r.href = reserve; r.target = '_blank'; r.rel = 'noopener nofollow sponsored'; r.textContent = c.kind === 'hotel' ? 'Book' : 'Reserve'; r.addEventListener('click', function () { track('reserve'); }); act.appendChild(r); }
    var d = document.createElement('a'); d.className = 'partner-btn partner-btn-quiet'; d.target = '_blank'; d.rel = 'noopener';
    d.href = ccMapsUrl(c.name + ' ' + (c.address || ''), c.lat, c.lng, true);
    d.textContent = 'Directions'; d.addEventListener('click', function () { track('directions'); }); act.appendChild(d);
    body.appendChild(act);
    if (c.lat != null && c.lng != null) {
      var ph = card.querySelector('.partner-photo');
      var city = String(c.address || '').split(',').slice(-2, -1)[0] || '';
      googleVenuePhoto({ name: c.name, city: city.trim(), lat: c.lat, lng: c.lng }).then(function (v) { if (v && v.src) showPhoto(ph, v.src, c.name, v.credit); }).catch(function () {});
    }
    if (typeof window.gtag === 'function') { try { window.gtag('event', 'partner_impression', { venue: slug, partner: c.name, partner_id: c.id, has_perk: c.perk ? 'yes' : 'no', surface: 'web_venue_' + c.kind, position: String(i + 1) }); } catch (_) {} }
    return card;
  }
  /* Partners without a live Perk: labeled, no offer line, so they never read as a benefit. */
  function partnerGrid(list, slug, surface) {
    var grid = document.createElement('div'); grid.className = 'perk-grid';
    list.forEach(function (o, i) {
      var box = document.createElement('article'); box.className = 'ui ui-section perk-web perk-partner';
      box.innerHTML = '<div class="ui-section-head"><span class="ui-kicker"></span><span class="perk-badge">Concerto Partner</span></div><h3></h3><p class="perk-details"></p>';
      box.querySelector('.ui-kicker').textContent = o.kind === 'hotel' ? 'Stay' : 'Before the show';
      box.querySelector('h3').textContent = o.name;
      box.querySelector('.perk-details').textContent = [o.blurb, o.address].filter(Boolean).join(' · ');
      var links = document.createElement('div'); links.className = 'perk-links';
      var u = safeHttps(o.url);
      if (u) { var a = document.createElement('a'); a.className = 'ui-link'; a.href = u; a.target = '_blank'; a.rel = 'noopener nofollow sponsored'; a.textContent = (o.kind === 'hotel' ? 'Visit / book' : 'Visit / reserve') + ' →'; links.appendChild(a); }
      if (o.address) { var m = document.createElement('a'); m.className = 'ui-link'; m.href = ccMapsUrl(o.name + ' ' + o.address); m.target = '_blank'; m.rel = 'noopener'; m.textContent = 'Directions'; links.appendChild(m); }
      if (links.children.length) box.appendChild(links);
      grid.appendChild(box);
      if (typeof window.gtag === 'function') { try { window.gtag('event', 'partner_impression', { venue: slug || '', partner: o.name, partner_id: o.id || '', surface: surface, position: String(i + 1) }); } catch (_) {} }
    });
    return grid;
  }
  /* What the venue and its partners published through the Partner Console: same endpoint the app reads */
  function wirePartnerContent() {
    var host = document.querySelector('[data-venue-tonight]'); if (!host) return;
    var slug = (location.pathname.match(/^\/venue\/([a-z0-9-]+)/) || [])[1]; if (!slug) return;
    getJSON(FN + '/partner-content?venue=' + encodeURIComponent(slug)).then(function (pc) {
      if (!pc) return;
      if (pc.claimed) { var c = document.createElement('span'); c.className = 'meta-pill'; c.textContent = '✓ Verified by the venue'; host.insertBefore(c, host.firstChild); }
      Object.keys(pc.overrides || {}).forEach(function (key) {
        var card = document.querySelector('.info-card[data-section="' + key + '"]'); var o = pc.overrides[key]; if (!card || !o) return;
        var p = card.querySelector('p'); if (p && (o.summary || o.note)) p.textContent = o.summary || o.note;
        var v = card.querySelector('.verified'); if (!v) { v = document.createElement('span'); v.className = 'verified'; card.insertBefore(v, card.querySelector('.link-row')); }
        v.textContent = 'Verified by the venue ' + (o.verified || '');
        var safeLink = safeHttps(o.officialLink); if (safeLink) { var a = card.querySelector('.link-row a'); if (a) a.href = safeLink; }
      });
      var st = (pc.stageTimes || [])[0];
      if (st && (st.headliner || st.doors)) {
        var fmt = function (t) { var h = +t.split(':')[0], m = t.split(':')[1] || '00'; return (h % 12 || 12) + ':' + m + (h >= 12 ? ' PM' : ' AM'); };
        var sp = document.createElement('span'); sp.className = 'meta-pill';
        sp.textContent = [st.doors ? 'Doors ' + fmt(st.doors) : null, st.headliner ? 'Headliner ' + fmt(st.headliner) : null].filter(Boolean).join(' · ') + ' · set by the venue';
        host.appendChild(sp);
      }
      if ((pc.perks && pc.perks.length) || (pc.partners && pc.partners.length)) renderVenuePerks(pc.perks || [], slug, host.getAttribute('data-name') || 'this venue', pc.partners || []);
    }).catch(function () {});
  }
  /* Tonight at this venue: upcoming shows + forecast on venue pages, same functions the app calls */
  function wireVenueTonight() {
    var host = document.querySelector('[data-venue-tonight]'); if (!host) return;
    var lat = host.getAttribute('data-lat'), lng = host.getAttribute('data-lng'), name = host.getAttribute('data-name');
    var country = host.getAttribute('data-country');
    var params = new URLSearchParams({ keyword: name, size: '5', sort: 'date,asc', startDateTime: new Date().toISOString().split('.')[0] + 'Z' });
    if (country) params.set('countryCode', country);
    if (lat && lng) { params.set('latlong', lat + ',' + lng); params.set('radius', '2'); params.set('unit', 'miles'); }
    getJSON(FN + '/tm/events.json?' + params).then(function (d) {
      var list = d && d._embedded && d._embedded.events || [];
      // Only an event whose venue name matches this page's venue counts. A plausible
      // event two blocks away is worse than showing nothing.
      var want = norm(name);
      list = list.filter(function (ev) { var v = ev._embedded && ev._embedded.venues && ev._embedded.venues[0]; var got = norm(v && v.name); return got && (got === want || got.indexOf(want) === 0 || want.indexOf(got) === 0); });
      if (!list.length) return;
      var first = list[0], day = first.dates && first.dates.start && first.dates.start.localDate;
      var pill = document.createElement('span'); pill.className = 'meta-pill';
      pill.innerHTML = '<b></b>&nbsp;· ' + (day ? fmtDay(day) : 'Upcoming');
      pill.querySelector('b').textContent = first.name; host.appendChild(pill);
      if (day && lat && lng) getJSON(FN + '/weather?' + new URLSearchParams({ lat: lat, lng: lng, date: day })).then(function (w) {
        if (!w || !w.available) return;
        var wp = document.createElement('span'); wp.className = 'meta-pill';
        wp.textContent = 'Show day ' + w.highF + '°/' + w.lowF + '°' + (w.precipPercent >= 30 ? ' · ' + w.precipPercent + '% rain' : '');
        host.appendChild(wp);
      }).catch(function () {});
    }).catch(function () {});
  }

  /* ---------- contact form: prefill topic from ?topic= ---------- */
  function wireTopic() {
    var sel = document.querySelector('select[name="topic"]'); if (!sel) return;
    var t = (new URLSearchParams(location.search).get('topic') || '').toLowerCase(); if (!t) return;
    var map = { investor: 'Investor', media: 'Media / Press', press: 'Media / Press', creator: 'Creator collaboration', company: 'Company / General' };
    var want = map[t]; if (!want) return;
    [].slice.call(sel.options).forEach(function (o) { if (o.text === want) sel.value = o.value || o.text; });
  }

  function wireLivePerks() {
    var host = document.querySelector('[data-live-perks]'); if (!host) return;
    host.setAttribute('aria-live', 'polite');
    function load() {
      host.textContent = 'Checking available Perks…';
      fetch(FN + '/partner-content?all=1').then(function (r) { if (!r.ok) throw new Error(); return r.json(); }).then(function (data) {
        if (data.error) throw new Error();
        host.textContent = '';
        var today = new Date().toISOString().slice(0, 10);
        var offers = (data.perks || []).filter(function (p) { return p.offer && p.details && (!p.starts_on || p.starts_on <= today) && (!p.ends_on || p.ends_on >= today); });
        var withPerk = {};
        offers.forEach(function (p) { if (p.org_id) withPerk[p.org_id] = true; });
        var listed = (data.partners || []).filter(function (o) { return !withPerk[o.id]; });
        if (!offers.length) host.textContent = 'No Perks are available right now. New offers will appear here with their dates and redemption terms.';
        if (listed.length) {
          var after = document.createElement('section'); after.className = 'live-partners';
          var hh = document.createElement('h2'); hh.className = 'c-h2 c-h2-sm'; hh.textContent = 'Concerto Partners';
          var pp = document.createElement('p'); pp.textContent = 'Restaurants and hotels near the venues, labeled so you always know the relationship.';
          after.appendChild(hh); after.appendChild(pp); after.appendChild(partnerGrid(rotateDaily(listed, 'perks-page'), '', 'web_perks_partner'));
          host.parentNode.insertBefore(after, host.nextSibling);
        }
        if (!offers.length) return;
        offers.forEach(function (p) {
          var card = document.createElement('article'); card.className = 'live-perk';
          function line(tag, text) { var el = document.createElement(tag); el.textContent = text; card.appendChild(el); }
          line('span', 'Concerto Partner · ' + (p.kind || 'Partner'));
          line('h3', p.partner_name); line('h4', p.offer); line('p', p.details);
          if (p.address) line('p', p.address);
          if (p.starts_on || p.ends_on) line('p', [p.starts_on ? 'From ' + p.starts_on : '', p.ends_on ? 'Through ' + p.ends_on : ''].filter(Boolean).join(' · '));
          var url = safeHttps(p.url);
          if (url) { var a = document.createElement('a'); a.href = url; a.target = '_blank'; a.rel = 'noopener nofollow'; a.className = 'ui-link'; a.textContent = 'View offer →'; card.appendChild(a); }
          host.appendChild(card);
        });
      }).catch(function () {
        host.textContent = 'We couldn’t load Perks. Please try again.';
        var retry = document.createElement('button'); retry.className = 'btn-secondary'; retry.textContent = 'Try again'; retry.addEventListener('click', load); host.appendChild(retry);
      });
    }
    load();
  }

  function wireNightTabs() {
    document.querySelectorAll('.night-tabs').forEach(function (list) {
      var tabs = Array.from(list.querySelectorAll('[role="tab"]'));
      function select(tab, focus) {
        tabs.forEach(function (item) {
          var active = item === tab;
          item.setAttribute('aria-selected', String(active));
          item.tabIndex = active ? 0 : -1;
          var panel = document.getElementById(item.getAttribute('aria-controls'));
          if (panel) panel.hidden = !active;
        });
        if (focus) tab.focus();
      }
      tabs.forEach(function (tab, index) {
        tab.addEventListener('click', function () { select(tab, false); });
        tab.addEventListener('keydown', function (event) {
          var next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
          if (next !== null) { event.preventDefault(); select(tabs[next], true); }
        });
      });
    });
  }

  function init() {
    wireNightTabs();
    wireLivePerks();
    wireTopic();
    wireLive();
    wireCountdowns();
    wireReports();
    wireAppLinks();
    wireVenueTonight();
    wirePartnerContent();
    document.body.classList.add('public-site');
    wireHeader();
    wireFilters();
    wireSearch();
    watchPhotos();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();

/* V8: reveal on scroll, and the venue guide's current-section marker. */
(function () {
  'use strict';
  var d = document, reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var els = [].slice.call(d.querySelectorAll('[data-reveal]'));
  if (!els.length) return;
  if (reduce || !('IntersectionObserver' in window)) { els.forEach(function (el) { el.classList.add('is-in'); }); }
  else {
    var io = new IntersectionObserver(function (es) { es.forEach(function (x) { if (x.isIntersecting) { x.target.classList.add('is-in'); io.unobserve(x.target); } }); }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });
    els.forEach(function (el) { io.observe(el); });
  }
})();
(function () {
  'use strict';
  var links = [].slice.call(document.querySelectorAll('.c-toc a'));
  if (!links.length || !('IntersectionObserver' in window)) return;
  var byId = {}; links.forEach(function (a) { byId[a.getAttribute('href').slice(1)] = a; });
  var io = new IntersectionObserver(function (es) { es.forEach(function (x) { if (x.isIntersecting && byId[x.target.id]) { links.forEach(function (a) { a.classList.remove('is-current'); }); byId[x.target.id].classList.add('is-current'); } }); }, { rootMargin: '-30% 0px -60% 0px' });
  Object.keys(byId).forEach(function (id) { var el = document.getElementById(id); if (el) io.observe(el); });
})();
(function () {
  'use strict';
  /* Directory filter: hide group headings whose entries are all filtered out. */
  document.querySelectorAll('[data-filter-target]').forEach(function (input) {
    input.addEventListener('input', function () {
      setTimeout(function () { document.querySelectorAll('.c-group').forEach(function (g) { var any = [].some.call(g.querySelectorAll('.c-entry'), function (li) { return !li.hidden; }); g.hidden = !any; }); }, 120);
    });
  });
})();
/* "Missing a venue or tour?" requests go to the report inbox as field "request". */
(function () {
  document.querySelectorAll('form[data-request]').forEach(function (f) {
    f.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var input = f.querySelector('input'); var note = f.parentNode.querySelector('.c-request-note');
      var text = (input.value || '').trim(); if (!text) return;
      var btn = f.querySelector('button'); btn.disabled = true;
      fetch('/.netlify/functions/report', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field: 'request', surface: 'web', message: (f.getAttribute('data-request') === 'tour' ? 'Tour request: ' : 'Venue request: ') + text.slice(0, 200) }) })
        .then(function (r) { return r.json(); })
        .then(function (j) { if (j && j.ok) { f.reset(); if (note) note.textContent = 'Thank you. We read every request.'; } else throw 0; })
        .catch(function () { if (note) note.textContent = 'That didn\u2019t send. Please try again in a moment.'; })
        .finally(function () { btn.disabled = false; });
    });
  });
})();
/* Jingle Ball: one city at a time. Opens on the next show (or the city in the link), keeps a link per city. */
(function () {
  var hub = document.querySelector('.c-jb'); if (!hub) return;
  var tabs = [].slice.call(hub.querySelectorAll('.c-jb-chip')), cards = [].slice.call(hub.querySelectorAll('.c-jb-card'));
  if (!tabs.length) return;
  hub.classList.add('is-tabbed');
  function show(id, push) {
    cards.forEach(function (c) { c.classList.toggle('is-active', c.id === id); c.hidden = c.id !== id; });
    tabs.forEach(function (t) { var on = t.getAttribute('data-city') === id; t.setAttribute('aria-selected', on ? 'true' : 'false'); t.tabIndex = on ? 0 : -1; });
    if (push) { try { history.replaceState(null, '', '#' + id); } catch (e) {} }
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { show(t.getAttribute('data-city'), true); });
    t.addEventListener('keydown', function (ev) {
      if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return;
      var n = tabs[(i + (ev.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]; n.focus(); n.click();
    });
  });
  var fromHash = (location.hash || '').slice(1);
  var start = cards.some(function (c) { return c.id === fromHash; }) ? fromHash : cards[0].id;
  show(start, false);
  window.addEventListener('hashchange', function () { var id = location.hash.slice(1); if (cards.some(function(c) { return c.id === id; })) show(id, false); });
  if (fromHash === start && fromHash) setTimeout(function () { hub.scrollIntoView({ block: 'start' }); }, 50);
})();
/* Jingle Ball countdown: counts up on load, ticks to the showtime, follows the chosen city,
   moves to the next city after each show, and says "Tonight" on show day. */
(function () {
  var box = document.querySelector('.c-jb-count[data-cities]'); if (!box) return;
  var list; try { list = JSON.parse(box.getAttribute('data-cities')); } catch (e) { return; }
  var q = function (s) { return box.querySelector(s); };
  var still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var pinned = null, shown = null, first = list[0] && list[0].a;
  function target() {
    var now = Date.now();
    if (pinned) { var p = list.filter(function (x) { return x.a === pinned; })[0]; if (p && Date.parse(p.t) + 4 * 3600e3 > now) return { x: p, mine: true }; }
    for (var i = 0; i < list.length; i++) if (Date.parse(list[i].t) + 4 * 3600e3 > now) return { x: list[i], mine: false };
    return null;
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function paint(animate) {
    var t = target(); if (!t) { box.innerHTML = '<strong>That\u2019s a wrap on Jingle Ball 2026.</strong>'; return; }
    var ms = Date.parse(t.x.t) - Date.now(), live = ms <= 0;
    var start = new Date(t.x.t), today = new Date(); var d0 = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    var d1 = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    var days = Math.max(0, Math.round((d1 - d0) / 86400000));
    var rem = Math.max(0, ms), h = Math.floor(rem / 3600e3) % 24, m = Math.floor(rem / 60e3) % 60, s = Math.floor(rem / 1e3) % 60;
    var big = q('[data-days]'), unit = q('[data-unit]');
    if (days === 0) { big.textContent = live ? 'Now' : 'Tonight'; unit.textContent = ''; }
    else if (animate && !still) {
      var n = 0, step = Math.max(1, Math.ceil(days / 24)); var iv = setInterval(function () { n = Math.min(days, n + step); big.textContent = n; if (n >= days) clearInterval(iv); }, 28);
      unit.textContent = days === 1 ? 'day' : 'days';
    } else { big.textContent = days; unit.textContent = days === 1 ? 'day' : 'days'; }
    q('[data-h]').textContent = pad(live ? 0 : Math.floor(rem / 3600e3) % 24 + (days ? 0 : 0));
    q('[data-h]').textContent = pad(h); q('[data-m]').textContent = pad(m); q('[data-s]').textContent = pad(s);
    if (shown !== t.x.a + t.mine) {
      q('[data-city]').textContent = t.x.city.replace(/ /g, '\u00a0');
      q('[data-line]').textContent = (t.mine ? 'your night' : (t.x.a === first ? 'opens the tour' : 'is next')) + ' \u00b7 ' + t.x.date + ' \u00b7 ' + t.x.venue;
      q('[data-go]').setAttribute('href', '#' + t.x.a);
      if (shown !== null) { box.classList.remove('is-bump'); void box.offsetWidth; box.classList.add('is-bump'); }
      shown = t.x.a + t.mine;
    }
  }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.c-jb-chip[data-city]'); if (!b) return;
    pinned = b.getAttribute('data-city'); paint(false);
  });
  window.addEventListener('hashchange', function () { var h = location.hash.slice(1); if (list.some(function (x) { return x.a === h; })) { pinned = h; paint(false); } });
  var h0 = location.hash.slice(1); if (list.some(function (x) { return x.a === h0; })) pinned = h0;
  paint(true); setInterval(function () { paint(false); }, 1000);
})();
/* Self-serve Concerto Partner signup on /partners/restaurants: venue, find the business,
   one line for fans, live card preview, then Stripe Checkout. Paid = live automatically. */
(function () {
  var f = document.getElementById('ss-form'); if (!f) return;
  var el = function (n) { return f.elements[n]; };
  var msg = f.querySelector('.ss-msg'), results = f.querySelector('.ss-results'), dl = document.getElementById('ss-venues');
  var preview = f.querySelector('.ss-preview'), card = f.querySelector('.ss-preview-card'), count = f.querySelector('.ss-count');
  var venues = [], picked = null;
  function esc(t) { return String(t || '').replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function label(v) { return v.name + ' \u00b7 ' + [v.city, v.state || v.country].filter(Boolean).join(', '); }
  fetch('/data/venues.json').then(function (r) { return r.json(); }).then(function (v) {
    venues = v || []; dl.innerHTML = venues.map(function (x) { return '<option value="' + esc(label(x)) + '"></option>'; }).join('');
  }).catch(function () {});
  function venue() {
    var t = (el('venue').value || '').trim().toLowerCase();
    return venues.filter(function (x) { return label(x).toLowerCase() === t || x.name.toLowerCase() === t; })[0] || null;
  }
  function say(t, bad) { msg.textContent = t || ''; msg.style.color = bad ? '#A42237' : ''; }
  function draw() {
    var name = (el('name').value || '').trim(), blurb = (el('blurb').value || '').trim();
    count.textContent = blurb.length + ' / 110';
    if (!picked && !name) { preview.hidden = true; return; }
    preview.hidden = false;
    var hotel = el('kind').value === 'hotel';
    card.innerHTML = '<article class="partner-card"><div class="partner-photo"><span class="fallback-mark">' + esc((name || '?').charAt(0)) +
      '</span><span class="partner-label">Concerto Partner</span></div><div class="partner-body"><h3>' + esc(name || 'Your name') + '</h3>' +
      (blurb ? '<p class="partner-blurb">' + esc(blurb) + '</p>' : '') +
      ((el('perkOffer') && el('perkOffer').value.trim()) ? '<div class="partner-perk"><span>Concerto Perk</span><strong>' + esc(el('perkOffer').value.trim()) + '</strong>' +
        (el('perkDetails').value.trim() ? '<p>' + esc(el('perkDetails').value.trim()) + '</p>' : '') + '</div>' : '') +
      '<div class="partner-actions"><span class="partner-btn">' + (hotel ? 'Book' : 'Reserve') + '</span><span class="partner-btn partner-btn-quiet">Directions</span></div></div></article>';
  }
  ['name', 'blurb', 'kind', 'perkOffer', 'perkDetails'].forEach(function (n) { if (!el(n)) return; el(n).addEventListener('input', draw); el(n).addEventListener('change', draw); });
  // The redeem field appears only once a Perk is typed.
  var how = f.querySelector('.ss-perk-how');
  if (el('perkOffer') && how) el('perkOffer').addEventListener('input', function () { how.hidden = !el('perkOffer').value.trim(); });
  function search() {
    var v = venue(), q = (el('q').value || '').trim();
    if (!v) { say('Choose your venue from the list first.', true); el('venue').focus(); return; }
    if (q.length < 2) { say('Type your business name, then search.', true); el('q').focus(); return; }
    say(''); results.innerHTML = '<p class="form-note">Searching near ' + esc(v.name) + '\u2026</p>'; picked = null;
    fetch('/.netlify/functions/partner-place-search?venue=' + encodeURIComponent(v.id) + '&kind=' + el('kind').value + '&q=' + encodeURIComponent(q))
      .then(function (r) { return r.json(); }).then(function (j) {
        var list = (j && j.results) || [];
        if (!list.length) { results.innerHTML = '<p class="form-note">' + esc((j && j.error) || 'No matches within 5 miles of ' + v.name + '. Try your exact business name.') + '</p>'; return; }
        results.innerHTML = list.map(function (p, i) {
          return '<button type="button" class="ss-hit" data-i="' + i + '"' + (p.fits ? '' : ' disabled') + '><b>' + esc(p.name) + '</b><span>' + esc(p.address) + ' \u00b7 ' + p.miles + ' mi' + (p.fits ? '' : ' \u00b7 not listed as a ' + (el('kind').value === 'hotel' ? 'hotel' : 'restaurant')) + '</span></button>';
        }).join('');
        [].forEach.call(results.querySelectorAll('.ss-hit'), function (b) {
          b.addEventListener('click', function () {
            picked = list[+b.getAttribute('data-i')];
            [].forEach.call(results.querySelectorAll('.ss-hit'), function (x) { x.classList.toggle('is-picked', x === b); });
            if (!el('name').value) el('name').value = picked.name;
            draw(); say('');
          });
        });
      }).catch(function () { results.innerHTML = '<p class="form-note">Search failed. Try again.</p>'; });
  }
  f.querySelector('.ss-find').addEventListener('click', search);
  el('q').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); search(); } });
  f.addEventListener('submit', function (e) {
    e.preventDefault();
    var v = venue();
    if (!v) { say('Choose your venue from the list.', true); return; }
    if (!picked) { say('Search for your business and select it.', true); return; }
    if (el('perkOffer') && el('perkOffer').value.trim() && !el('perkDetails').value.trim()) { say('Add how fans redeem your Perk.', true); el('perkDetails').focus(); return; }
    if (el('staffCode') && !/^\d{4}$/.test((el('staffCode').value || '').trim())) { say('Choose a 4-digit staff code.', true); el('staffCode').focus(); return; }
    if (!el('agree').checked) { say('Please agree to the terms.', true); return; }
    var plan = (f.querySelector('input[name=plan]:checked') || {}).value || 'monthly';
    var btn = f.querySelector('.ss-pay'); btn.disabled = true; say('Getting your checkout ready\u2026');
    fetch('/.netlify/functions/partner-signup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      kind: el('kind').value, venue: v.id, placeId: picked.id, name: el('name').value, url: el('url').value,
      blurb: el('blurb').value, plan: plan, agree: true, company: el('company').value,
      perkOffer: el('perkOffer') ? el('perkOffer').value : '', perkDetails: el('perkDetails') ? el('perkDetails').value : '',
      staffCode: el('staffCode') ? el('staffCode').value.trim() : '' }) })
      .then(function (r) { return r.json(); }).then(function (j) {
        if (j && j.checkout) { location.href = j.checkout; return; }
        btn.disabled = false; say((j && j.error) || 'Something went wrong. Try again.', true);
      }).catch(function () { btn.disabled = false; say('Something went wrong. Try again.', true); });
  });
})();
