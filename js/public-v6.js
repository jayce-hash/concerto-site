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
  var APP = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414';
  var FN = '/.netlify/functions';
  var DAY = 86400000;

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

  /* ---------- contact form: prefill topic from ?topic= ---------- */
  function wireTopic() {
    var sel = document.querySelector('select[name="topic"]'); if (!sel) return;
    var t = (new URLSearchParams(location.search).get('topic') || '').toLowerCase(); if (!t) return;
    var map = { investor: 'Investor', media: 'Media / Press', press: 'Media / Press', creator: 'Creator collaboration', company: 'Company / General' };
    var want = map[t]; if (!want) return;
    [].slice.call(sel.options).forEach(function (o) { if (o.text === want) sel.value = o.value || o.text; });
  }

  function init() {
    wireTopic();
    document.body.classList.add('public-site');
    wireHeader();
    wireFilters();
    wireSearch();
    watchPhotos();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
