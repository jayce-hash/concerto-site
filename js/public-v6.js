/* Maps: Apple Maps first on Apple devices (iPhone, iPad, Mac), Google Maps everywhere else. */
var CC_APPLE = /iPhone|iPad|iPod|Macintosh/.test((typeof navigator !== 'undefined' && navigator.userAgent) || '');
/* Demo partners (private): ?demo=<key> on any page turns them on for this visit; ?demo=off ends it. */
function ccDemoKey() {
  try {
    var q = new URLSearchParams(location.search).get('demo');
    if (q === 'off') { sessionStorage.removeItem('concerto.demo'); return ''; }
    if (q && /^[A-Za-z0-9_-]{4,64}$/.test(q)) sessionStorage.setItem('concerto.demo', q);
    return sessionStorage.getItem('concerto.demo') || '';
  } catch (_) { return ''; }
}
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
    if (v.place_id) params.set('place_id', v.place_id);
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
      // The menu covers the page from just under the header.
      if (open) { var r = header.getBoundingClientRect(); document.documentElement.style.setProperty('--mn-top', Math.max(0, Math.round(r.bottom)) + 'px'); }
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
      // A question ("can I bring a bag to MSG") also lists the venue or artist it names.
      var hits = index.filter(function (x) { if (!x._n) return false; if (x._n.indexOf(q) !== -1) return true; var t = norm(x.title); return q.length > 12 && t.length >= 5 && q.indexOf(t) !== -1; }).slice(0, 30);
      if (!hits.length) { results.innerHTML = '<div class="search-empty">' + (q.length > 12 ? 'Press Enter or Ask to get an answer from Concerto.' : 'No match yet. Try a broader artist, venue, or city.') + '</div>'; return; }
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
    // The app opens saved shows only, so a show the fan has not saved opens Near Me; once the
    // venue is matched to a guide (ccLinkVenueGuides) it opens that venue's screen instead.
    a.setAttribute('data-app-link', 'concerto://near-me');
    a.setAttribute('data-venue', v.name || '');
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
      list.slice(0, 12).forEach(function (ev) { rail.appendChild(eventCard(ev)); });
      if (window.ccLinkVenueGuides) window.ccLinkVenueGuides(rail);
    }).catch(function () { rail.innerHTML = '<div class="live-empty">Shows near you load in a moment. <a class="text-link" href="/near-me">Open Near Me in the app</a>.</div>'; });
  }
  function wireLive() {
    var root = document.querySelector('[data-live-near]'); if (!root) return;
    var cityEl = root.querySelector('[data-live-city]'), sub = root.querySelector('[data-live-sub]'), form = root.querySelector('[data-live-form]');
    getJSON(FN + '/geo').then(function (g) {
      if (g && g.ok) { cityEl.textContent = g.city || 'you'; loadNear({ lat: g.lat, lng: g.lng, country: g.country }); }
      else { cityEl.textContent = 'New York'; loadNear({ city: 'New York' }); }
    }).catch(function () { cityEl.textContent = 'New York'; loadNear({ city: 'New York' }); });
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
    var targets = venue ? document.querySelectorAll('.info-card[data-section], .cx-card[data-section]') : document.querySelectorAll('.song-list, .cx-songs, .detail-grid');
    targets.forEach(function (card) {
      var field = card.getAttribute('data-section') || (card.classList.contains('song-list') || card.classList.contains('cx-songs') ? 'setlist' : 'showTime');
      var a = document.createElement('button'); a.type = 'button'; a.className = 'report-link'; a.textContent = 'Report wrong info';
      a.addEventListener('click', function () {
        if (a.disabled) return;
        a.textContent = 'Sending…'; a.disabled = true;
        fetch(FN + '/report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ venue: venue || '', tour: tour || '', field: field, message: '', surface: 'web' }) })
          .then(function (r) { if (!r.ok) throw new Error(String(r.status)); a.textContent = 'Thank you. We will check it.'; a.setAttribute('aria-live', 'polite'); })
          .catch(function () { a.textContent = 'Could not send. Tap to try again.'; a.disabled = false; });
      });
      if (card.classList.contains('cx-songs')) { card.parentNode.insertBefore(a, card.nextSibling); return; }
      (card.querySelector('.cx-card-b') || card).appendChild(a);
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
  function byId(list) { return list.slice().sort(function (a, b) { return a.id < b.id ? -1 : a.id > b.id ? 1 : 0; }); }
  function partnerCards(perks, partners, kind) {
    var out = {}, order = [];
    (partners || []).forEach(function (o) {
      if (o.kind !== kind) return;
      out[o.id] = { id: o.id, name: o.name, kind: kind, blurb: o.blurb, address: o.address, url: safeHttps(o.url), lat: o.lat, lng: o.lng, place_id: o.place_id };
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
  /* Concerto Partners on a venue page: one row, the same shape as the app's Nearby row.
     Restaurants and hotels are two tabs of the same row, so 1 partner or 12 take the same
     space. Swipe on phones, arrows on desktop. Order rotates daily, same as the app. */
  function renderVenuePerks(perks, slug, venueName, partners) {
    var hero = document.querySelector('.cx-hero') || document.querySelector('.c-hero'); if (!hero || document.querySelector('.c-near')) return;
    var host = document.querySelector('[data-venue-tonight]');
    var vlat = host && parseFloat(host.getAttribute('data-lat')), vlng = host && parseFloat(host.getAttribute('data-lng'));
    var groups = [{ kind: 'restaurant', tab: 'Restaurants', h: 'Eat' }, { kind: 'hotel', tab: 'Hotels', h: 'Stay' }].map(function (g) {
      g.list = rotateDaily(byId(partnerCards(perks, partners, g.kind)), slug + ':' + g.kind + 's'); return g;
    }).filter(function (g) { return g.list.length; });
    if (!groups.length) return;
    var sec = document.createElement('section'); sec.className = 'c-section c-white c-near'; sec.id = 'partners';
    sec.setAttribute('aria-label', 'Concerto Partners near ' + venueName);
    var wrap = document.createElement('div'); wrap.className = 'c-wrap'; sec.appendChild(wrap);
    var head = document.createElement('div'); head.className = 'c-near-head'; wrap.appendChild(head);
    var title = document.createElement('div');
    title.innerHTML = '<p class="c-eyebrow">Concerto Partners</p><h2 class="c-h2 c-h2-sm"></h2><p class="c-near-sub"></p>';
    title.querySelector('h2').textContent = document.querySelector('.cx') ? 'Concerto Partners' : 'Near ' + venueName;
    title.querySelector('.c-near-sub').textContent = 'Restaurants and hotels near ' + venueName + ' that partner with Concerto.';
    head.appendChild(title);
    var tools = document.createElement('div'); tools.className = 'c-near-tools'; head.appendChild(tools);
    var tabs = null;
    if (groups.length > 1) {
      tabs = document.createElement('div'); tabs.className = 'c-near-tabs'; tabs.setAttribute('role', 'tablist'); tools.appendChild(tabs);
    }
    var prev = document.createElement('button'), next = document.createElement('button');
    prev.className = next.className = 'c-near-arrow'; prev.type = next.type = 'button';
    prev.setAttribute('aria-label', 'Previous'); next.setAttribute('aria-label', 'Next');
    prev.innerHTML = '&#8249;'; next.innerHTML = '&#8250;';
    tools.appendChild(prev); tools.appendChild(next);
    var row = document.createElement('div'); row.className = 'c-near-row'; row.setAttribute('role', 'list'); wrap.appendChild(row);
    var seen = {};
    function arrows() { var max = row.scrollWidth - row.clientWidth - 2; prev.disabled = row.scrollLeft <= 2; next.disabled = row.scrollLeft >= max; tools.classList.toggle('no-scroll', max <= 0); }
    function show(g) {
      row.innerHTML = ''; row.scrollLeft = 0;
      g.list.forEach(function (c, i) {
        row.appendChild(nearCard(c, slug, vlat, vlng));
        if (!seen[c.id] && typeof window.gtag === 'function') { seen[c.id] = 1; try { window.gtag('event', 'partner_impression', { venue: slug, partner: c.name, partner_id: c.id, has_perk: c.perk ? 'yes' : 'no', surface: 'web_venue_' + c.kind, position: String(i + 1) }); } catch (_) {} }
      });
      if (tabs) [].forEach.call(tabs.children, function (b) { var on = b.getAttribute('data-kind') === g.kind; b.setAttribute('aria-selected', on ? 'true' : 'false'); b.classList.toggle('on', on); });
      setTimeout(arrows, 0);
    }
    if (tabs) groups.forEach(function (g) {
      var b = document.createElement('button'); b.type = 'button'; b.setAttribute('role', 'tab'); b.setAttribute('data-kind', g.kind);
      b.textContent = g.tab + ' '; var n = document.createElement('span'); n.textContent = g.list.length; b.appendChild(n);
      b.addEventListener('click', function () { show(g); }); tabs.appendChild(b);
    });
    var step = function (dir) { var card = row.firstElementChild; row.scrollBy({ left: dir * ((card ? card.getBoundingClientRect().width : 260) + 16) * 2, behavior: 'smooth' }); };
    prev.addEventListener('click', function () { step(-1); }); next.addEventListener('click', function () { step(1); });
    row.addEventListener('scroll', function () { window.requestAnimationFrame(arrows); }, { passive: true });
    window.addEventListener('resize', arrows);
    hero.parentNode.insertBefore(sec, hero.nextSibling);
    show(groups[0]);
  }
  function nearMiles(c, vlat, vlng) {
    if (!isFinite(vlat) || !isFinite(vlng) || c.lat == null || c.lng == null) return '';
    var r = Math.PI / 180, x = Math.pow(Math.sin((c.lat - vlat) * r / 2), 2) + Math.cos(vlat * r) * Math.cos(c.lat * r) * Math.pow(Math.sin((c.lng - vlng) * r / 2), 2);
    var mi = 2 * 3958.8 * Math.asin(Math.sqrt(x));
    return mi < 0.1 ? 'Steps away' : (Math.round(mi * 10) / 10) + ' mi';
  }
  function nearCard(c, slug, vlat, vlng) {
    var card = document.createElement('article'); card.className = 'c-near-card'; card.setAttribute('role', 'listitem');
    card.innerHTML = '<div class="c-near-photo"><span class="c-near-mark"></span></div><div class="c-near-body"><h3></h3><p class="c-near-meta"></p><p class="c-near-blurb"></p><div class="c-near-links"></div></div>';
    card.querySelector('.c-near-mark').textContent = c.name.charAt(0);
    card.querySelector('h3').textContent = c.name;
    card.querySelector('.c-near-meta').textContent = [nearMiles(c, vlat, vlng), 'Concerto Partner'].filter(Boolean).join(' · ');
    var bl = card.querySelector('.c-near-blurb'); if (c.blurb) bl.textContent = c.blurb; else bl.remove();
    var track = function (action) { if (typeof window.gtag === 'function') { try { window.gtag('event', 'partner_tap', { venue: slug, partner: c.name, partner_id: c.id, action: action, surface: 'web_venue_' + c.kind }); } catch (_) {} } };
    var links = card.querySelector('.c-near-links'), go = (c.perk && c.perk.url) || c.url;
    if (go) { var a = document.createElement('a'); a.className = 'c-near-go'; a.href = go; a.target = '_blank'; a.rel = 'noopener nofollow sponsored'; a.textContent = c.kind === 'hotel' ? 'Book' : 'Reserve'; a.addEventListener('click', function () { track('reserve'); }); links.appendChild(a); }
    var d = document.createElement('a'); d.className = 'c-near-dir'; d.target = '_blank'; d.rel = 'noopener'; d.href = ccMapsUrl(c.name + ' ' + (c.address || ''), c.lat, c.lng, true); d.textContent = 'Directions';
    d.addEventListener('click', function () { track('directions'); }); links.appendChild(d);
    if (c.perk) {
      // Same as the app: a gold star, and the offer itself is for signed-in Concerto members.
      var ph = card.querySelector('.c-near-photo');
      var star = document.createElement('button'); star.type = 'button'; star.className = 'c-near-star'; star.setAttribute('aria-label', 'Concerto Perk at ' + c.name); star.innerHTML = '&#9733;';
      var tip = document.createElement('div'); tip.className = 'c-near-tip'; tip.hidden = true;
      tip.innerHTML = '<b>Concerto Perk</b><p>This place has an offer for Concerto members.</p><a href="https://apps.apple.com/us/app/concerto-show-go/id6744903414?pt=127753814&ct=website-perk&mt=8" target="_blank" rel="noopener">See it in the app</a>';
      star.addEventListener('click', function (e) { e.stopPropagation(); tip.hidden = !tip.hidden; if (!tip.hidden) track('perk'); });
      ph.appendChild(star); ph.appendChild(tip);
    }
    if (c.lat != null && c.lng != null) {
      var city = String(c.address || '').split(',').slice(-2, -1)[0] || '';
      googleVenuePhoto({ name: c.name, city: city.trim(), lat: c.lat, lng: c.lng, place_id: c.place_id }).then(function (v) { if (v && v.src) showPhoto(card.querySelector('.c-near-photo'), v.src, c.name, v.credit); }).catch(function () {});
    }
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
    var demo = ccDemoKey();
    getJSON(FN + '/partner-content?venue=' + encodeURIComponent(slug) + (demo ? '&demo=' + encodeURIComponent(demo) : '')).then(function (pc) {
      if (!pc) return;
      if (pc.claimed) { var c = document.createElement('span'); c.className = 'meta-pill'; c.textContent = '✓ Verified by the venue'; host.insertBefore(c, host.firstChild); }
      Object.keys(pc.overrides || {}).forEach(function (key) {
        var card = document.querySelector('[data-section="' + key + '"]'); var o = pc.overrides[key]; if (!card || !o) return;
        var p = card.querySelector('.cx-card-b > p') || card.querySelector('p'); if (p && (o.summary || o.note)) p.textContent = o.summary || o.note;
        var v = card.querySelector('.cx-ver') || card.querySelector('.verified'); if (!v) { v = document.createElement('span'); v.className = 'verified'; card.insertBefore(v, card.querySelector('.link-row')); }
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
      if (document.querySelector('[data-nearby]')) {
        // Venue pages: partners go first in their own Nearby row (see Around the venue).
        publishPartners({ restaurant: rotateDaily(byId(partnerCards(pc.perks || [], pc.partners || [], 'restaurant')), slug + ':restaurants'),
                          hotel: rotateDaily(byId(partnerCards(pc.perks || [], pc.partners || [], 'hotel')), slug + ':hotels') });
        return;
      }
      if ((pc.perks && pc.perks.length) || (pc.partners && pc.partners.length)) renderVenuePerks(pc.perks || [], slug, host.getAttribute('data-name') || 'this venue', pc.partners || []);
    }).catch(function () { publishPartners({ restaurant: [], hotel: [] }); });
  }
  function publishPartners(v) {
    window.ccVenuePartners = v;
    try { document.dispatchEvent(new CustomEvent('cc:partners')); } catch (_) {}
  }
  window.ccNearCard = nearCard;
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
    // The same Nearby row the app draws: your card first, a gold star when there is an offer,
    // and the popup fans see when they tap it.
    var offer = el('perkOffer') ? el('perkOffer').value.trim() : '', details = el('perkDetails') ? el('perkDetails').value.trim() : '';
    card.innerHTML = '<div class="nb-mock"><p class="nb-title">' + (hotel ? 'Nearby Hotels' : 'Nearby Restaurants') + '</p><div class="nb-row">' +
      '<div class="nb-card nb-you"><div class="nb-photo"><span class="nb-mark">' + esc((name || '?').charAt(0)) + '</span>' + (offer ? '<span class="nb-star" aria-label="Concerto Perk">&#9733;</span>' : '') + '</div><b>' + esc(name || 'Your name') + '</b><span>Your price · distance</span></div>' +
      '<div class="nb-card nb-other"><div class="nb-photo"><span class="nb-mark">B</span></div><b>Another place</b><span>Nearby</span></div></div>' +
      (offer ? '<p class="nb-cap">Tap the star:</p><div class="nb-alert"><b>' + esc(offer) + '</b><p>' + esc(name || 'Your name') + '</p>' + (details ? '<p>' + esc(details) + '</p>' : '<p></p>') +
        '<div class="nb-alert-actions"><span>Close</span><span>' + (hotel ? 'Book' : 'Reserve') + '</span></div></div>' : '') + '</div>';
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
    if (el('perkOffer') && el('perkOffer').value.trim() && !el('perkDetails').value.trim()) { say('Add how fans use your offer.', true); el('perkDetails').focus(); return; }
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

/* Download taps: one GA4 event per tap on any App Store link or "Open in Concerto" button,
   with the page type and the link's campaign token (ct=website-venue and so on). Listens in
   the capture phase so it runs before the app-link handler redirects the page. */
(function () {
  function pageType(p) {
    var m = p.match(/^\/(venue|tour|setlist|partners)\b/); if (m) return m[1];
    return p === '/' ? 'home' : p.replace(/^\//, '').replace(/\.html$/, '') || 'home';
  }
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href*="apps.apple.com"], a[data-app-link]') : null;
    if (!a || typeof window.gtag !== 'function') return;
    var href = a.getAttribute('href') || '', ct = (href.match(/[?&]ct=([^&]+)/) || [])[1] || '';
    try {
      window.gtag('event', 'app_store_tap', {
        campaign: ct, page_type: pageType(location.pathname), page_path: location.pathname,
        link_text: (a.textContent || a.getAttribute('aria-label') || '').trim().slice(0, 60),
        transport_type: 'beacon'
      });
    } catch (_) {}
  }, true);
})();

/* V9: answers before questions. Upcoming shows on venue pages, tour dates on tour pages,
   and venue guides linked from every show list. Same Ticketmaster feed the app uses. */
(function () {
  'use strict';
  var FN = '/.netlify/functions';
  var ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
  var STORE = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414?pt=127753814&mt=8&ct=';
  function getJSON(u) { return fetch(u, { headers: { Accept: 'application/json' } }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }); }
  function norm(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/^the\s+/, '').replace(/[^a-z0-9]/g, ''); }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function clock(lt) { try { return new Date('1970-01-01T' + lt).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }); } catch (e) { return ''; } }
  function dayParts(d) { var t = new Date(d + 'T12:00:00'); return { dow: t.toLocaleDateString(undefined, { weekday: 'short' }), mon: t.toLocaleDateString(undefined, { month: 'short' }), day: String(t.getDate()), year: t.getFullYear() }; }
  function bindAppLink(a) {
    a.addEventListener('click', function (e) {
      if (typeof window.gtag === 'function') { try { window.gtag('event', 'app_store_tap', { campaign: (a.getAttribute('href').match(/[?&]ct=([^&]+)/) || [])[1] || '', page_type: location.pathname.split('/')[1] || 'home', page_path: location.pathname, link_text: (a.textContent || '').trim().slice(0, 60), transport_type: 'beacon' }); } catch (_) {} }
      if (!ios) return;
      e.preventDefault(); e.stopPropagation();
      var store = a.getAttribute('href'), app = a.getAttribute('data-app-link'), t0 = Date.now(), left = false;
      var onHide = function () { left = true; };
      document.addEventListener('visibilitychange', onHide, { once: true });
      window.location.href = app;
      setTimeout(function () { document.removeEventListener('visibilitychange', onHide); if (!left && !document.hidden && Date.now() - t0 < 2500) window.location.href = store; }, 1400);
    });
    return a;
  }
  window.ccBindAppLink = bindAppLink;
  function appLink(label, deep, ct, cls) { var a = el('a', cls || 'c-up-save', label); a.href = STORE + ct; a.rel = 'noopener'; a.setAttribute('data-app-link', deep); return bindAppLink(a); }
  function ticketLink(url) { if (!url || !/^https:\/\//.test(url)) return null; var t = el('a', 'c-up-tix', 'Tickets'); t.href = url; t.target = '_blank'; t.rel = 'noopener nofollow'; return t; }
  // Venue name -> guide slug, from the same search index the site search uses.
  var vidx = null;
  function venueIndex() {
    if (!vidx) vidx = getJSON('/search-index.json').then(function (d) { var m = {}; (d.venues || []).forEach(function (v) { m[norm(v.name)] = v.slug; }); return m; }).catch(function () { return {}; });
    return vidx;
  }
  function slugFor(m, name) { var k = norm(name); if (m[k]) return m[k]; for (var n in m) { if (n.length > 6 && (k.indexOf(n) === 0 || n.indexOf(k) === 0)) return m[n]; } return null; }
  function realEvent(ev) { var c = ev.dates && ev.dates.status && ev.dates.status.code; return c !== 'cancelled' && c !== 'postponed'; }
  function supportActs(ev, headliner) {
    var at = (ev._embedded && ev._embedded.attractions) || []; var h = norm(headliner);
    return at.map(function (a) { return a.name; }).filter(function (n) { return n && norm(n) !== h; }).slice(0, 3);
  }
  function timeLine(ev) {
    var s = ev.dates && ev.dates.start || {};
    if (s.timeTBA || s.noSpecificTime) return 'Time to be announced';
    var doors = ev.doorsTimes && ev.doorsTimes.localTime ? 'Doors ' + clock(ev.doorsTimes.localTime) : '';
    var show = s.localTime ? 'Show ' + clock(s.localTime) : '';
    return [doors, show].filter(Boolean).join(' · ');
  }
  function row(ev, opts) {
    var s = ev.dates && ev.dates.start || {}; var p = s.localDate ? dayParts(s.localDate) : null;
    var li = el('li', 'c-up-row');
    var date = el('div', 'c-up-date');
    if (p) { date.appendChild(el('span', 'c-up-dow', p.dow)); date.appendChild(el('span', 'c-up-day', p.day)); date.appendChild(el('span', 'c-up-mon', p.mon)); }
    li.appendChild(date);
    var body = el('div', 'c-up-body');
    body.appendChild(el('h3', 'c-up-name', opts.title(ev)));
    var meta = opts.meta(ev).filter(Boolean);
    if (meta.length) body.appendChild(el('p', 'c-up-meta', meta.join(' · ')));
    var acts = el('div', 'c-up-actions');
    opts.actions(ev).forEach(function (a) { if (a) acts.appendChild(a); });
    body.appendChild(acts);
    li.appendChild(body);
    return li;
  }

  /* Venue page: the next shows here, with doors, show time, and opening acts */
  function venueUpcoming() {
    var host = document.querySelector('[data-venue-upcoming]'), anchor = document.querySelector('[data-venue-tonight]');
    if (!host || !anchor) return;
    var slug = (location.pathname.match(/^\/venue\/([a-z0-9-]+)/) || [])[1];
    var name = anchor.getAttribute('data-name'), lat = anchor.getAttribute('data-lat'), lng = anchor.getAttribute('data-lng'), country = anchor.getAttribute('data-country');
    var p = new URLSearchParams({ keyword: name, size: '20', sort: 'date,asc', classificationName: 'Music', startDateTime: new Date().toISOString().split('.')[0] + 'Z' });
    if (country) p.set('countryCode', country);
    if (lat && lng) { p.set('latlong', lat + ',' + lng); p.set('radius', '2'); p.set('unit', 'miles'); }
    getJSON(FN + '/tm/events.json?' + p).then(function (d) {
      var want = norm(name);
      var list = (d && d._embedded && d._embedded.events || []).filter(realEvent).filter(function (ev) {
        var v = ev._embedded && ev._embedded.venues && ev._embedded.venues[0]; var got = norm(v && v.name);
        return got && (got === want || got.indexOf(want) === 0 || want.indexOf(got) === 0);
      });
      var seen = {}; list = list.filter(function (ev) { var k = ev.name + (ev.dates && ev.dates.start && ev.dates.start.localDate); if (seen[k]) return false; seen[k] = 1; return true; }).slice(0, 6);
      if (!list.length) return;
      var ol = host.querySelector('.c-up-list');
      list.forEach(function (ev) {
        var headliner = (ev._embedded && ev._embedded.attractions && ev._embedded.attractions[0] && ev._embedded.attractions[0].name) || ev.name;
        ol.appendChild(row(ev, {
          title: function () { return ev.name; },
          meta: function () { var acts = supportActs(ev, headliner); return [timeLine(ev), acts.length ? 'With ' + acts.join(', ') : '']; },
          actions: function () { return [appLink('Save in Concerto', 'concerto://venue/' + slug, 'website-venue-upcoming'), ticketLink(ev.url)]; }
        }));
      });
      host.hidden = false;
    }).catch(function () {});
  }

  /* Tour page: where and when it plays, with opening acts and the venue guide for each stop */
  function tourDates() {
    var host = document.querySelector('[data-tour-dates]'); if (!host) return;
    var artist = host.getAttribute('data-tour-artist'), slug = host.getAttribute('data-tour');
    // Shows that aren't concerts are listed under their own name and outside the Music category.
    var keyword = host.getAttribute('data-tour-keyword') || artist, prefix = host.getAttribute('data-tour-match') === 'prefix';
    var now = new Date(), end = new Date(now.getTime() + 400 * 86400000);
    var p = new URLSearchParams({ keyword: keyword, classificationName: 'Music', size: '100', sort: 'date,asc', startDateTime: now.toISOString().split('.')[0] + 'Z', endDateTime: end.toISOString().split('.')[0] + 'Z' });
    if (host.hasAttribute('data-tour-any')) p.delete('classificationName');
    Promise.all([getJSON(FN + '/tm/events.json?' + p), venueIndex()]).then(function (r) {
      var d = r[0], m = r[1], want = norm(prefix ? keyword : artist);
      // Only dates where this artist is actually billed: tribute acts and lookalike names stay out.
      var list = (d && d._embedded && d._embedded.events || []).filter(realEvent).filter(function (ev) {
        var at = (ev._embedded && ev._embedded.attractions) || [];
        return at.some(function (a) { var n = norm(a.name); return prefix ? n.indexOf(want) === 0 : n === want; });
      });
      var seen = {}; list = list.filter(function (ev) { var v = ev._embedded.venues && ev._embedded.venues[0] || {}; var k = (v.name || '') + (ev.dates && ev.dates.start && ev.dates.start.localDate); if (seen[k]) return false; seen[k] = 1; return true; });
      if (!list.length) return;
      var ol = host.querySelector('.c-up-list');
      list.forEach(function (ev, i) {
        var v = ev._embedded.venues && ev._embedded.venues[0] || {};
        var city = [v.city && v.city.name, v.state && v.state.stateCode || (v.country && v.country.countryCode !== 'US' ? v.country.name : '')].filter(Boolean).join(', ');
        var vslug = slugFor(m, v.name);
        var li = row(ev, {
          title: function () { return city || v.name || ''; },
          meta: function () { var acts = supportActs(ev, artist); return [v.name, timeLine(ev), acts.length ? 'With ' + acts.join(', ') : '']; },
          actions: function () {
            var g = null; if (vslug) { g = el('a', 'c-up-guide', 'Venue guide'); g.href = '/venue/' + vslug; }
            return [g, appLink('Save in Concerto', 'concerto://tour/' + slug, 'website-tour-dates'), ticketLink(ev.url)];
          }
        });
        if (i >= 8) li.hidden = true;
        ol.appendChild(li);
      });
      host.querySelector('[data-count]').textContent = list.length === 1 ? '1 date' : list.length + ' dates';
      if (list.length > 8) {
        var more = el('button', 'c-up-more', 'Show all ' + list.length + ' dates'); more.type = 'button';
        more.addEventListener('click', function () { [].forEach.call(ol.children, function (x) { x.hidden = false; }); more.remove(); });
        host.querySelector('.c-wrap').appendChild(more);
      }
      host.hidden = false;
    }).catch(function () {});
  }

  /* Near Me cards: open the right place in the app, and link the venue guide on the site */
  window.ccLinkVenueGuides = function (rail) {
    venueIndex().then(function (m) {
      [].forEach.call(rail.querySelectorAll('.live-card'), function (card) {
        var vname = card.getAttribute('data-venue'); var vs = vname && slugFor(m, vname);
        if (vs) {
          card.setAttribute('data-app-link', 'concerto://venue/' + vs);
          var g = el('a', 'live-tickets', 'Venue guide'); g.href = '/venue/' + vs;
          g.addEventListener('click', function (e) { e.stopPropagation(); });
          var acts = card.querySelector('.live-actions'); if (acts) acts.appendChild(g);
        }
        if (!card.getAttribute('data-bound')) { card.setAttribute('data-bound', '1'); bindAppLink(card); }
      });
    });
  };

  function init() { venueUpcoming(); tourDates(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();

/* V10: Ask Concerto. The search bar answers questions from Concerto's own data
   (netlify/functions/ask.js). Typing still searches instantly; Enter or Ask sends the
   question. Only counts are sent to analytics, never the question. */
(function () {
  'use strict';
  var form = document.querySelector('[data-ask-form]'), out = document.querySelector('[data-ask-answer]');
  if (!form || !out) return;
  var input = form.querySelector('input'), ring = form.querySelector('.c-ask-ring'), btn = form.querySelector('button');
  function esc(s) { return String(s || '').replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function safe(u) { u = String(u || ''); return /^\/[a-z0-9\-\/#_]*$/i.test(u) || /^https:\/\//.test(u) ? u : ''; }
  function render(r) {
    var kicker = (r.partners || []).length ? (r.mode === 'ai' ? 'Concerto AI' : 'Concerto') : r.mode === 'ai' ? 'Concerto AI · from Concerto’s guide' : r.mode === 'guide' ? 'From Concerto’s guide' : 'Concerto';
    var src = (r.sources || []).map(function (s) {
      var u = safe(s.url), o = safe(s.official);
      return '<li>' + (u ? '<a href="' + esc(u) + '">' + esc(s.label) + '</a>' : esc(s.label)) + (s.checked ? '<span>Checked ' + esc(s.checked) + '</span>' : '') +
        (o ? '<a class="c-answer-off" href="' + esc(o) + '" target="_blank" rel="noopener">Official source</a>' : '') + '</li>';
    }).join('');
    var venue = r.entity && r.entity.venue ? r.entity.venue.slug : '';
    var pts = (r.partners || []).map(function (p, i) {
      var u = safe(p.url), d = typeof p.miles === 'number' ? (p.miles < 0.1 ? 'Steps away' : p.miles + ' mi away') : '';
      return '<li class="c-ap"><p class="c-ap-tag">Concerto Partner</p><p class="c-ap-name">' + esc(p.name) + '</p>' +
        ((d || p.address) ? '<p class="c-ap-meta">' + esc([d, p.address].filter(Boolean).join(' · ')) + '</p>' : '') +
        (p.perk ? '<p class="c-ap-perk"><span aria-hidden="true">★</span> ' + (p.perk.offer ? esc(p.perk.offer) : 'Concerto Perk in the app') + '</p>' : '') +
        (u ? '<a class="c-ap-go" data-ap="' + i + '" href="' + esc(u) + '" target="_blank" rel="noopener">' + (p.kind === 'hotel' ? 'Book' : 'Reserve') + '</a>' : '') + '</li>';
    }).join('');
    out.innerHTML = '<p class="c-answer-kicker">' + kicker + '</p><p class="c-answer-text">' + esc(r.text) + '</p>' +
      (pts ? '<ul class="c-answer-partners">' + pts + '</ul>' : '') +
      (src ? '<ul class="c-answer-src">' + src + '</ul>' : '') + (r.note ? '<p class="c-answer-note">' + esc(r.note) + '</p>' : '') +
      (r.mode === 'ai' ? '<p class="c-answer-note">Rules can change for a specific show. Check your ticket and the official page before you go.</p>' : '');
    out.hidden = false;
    (r.partners || []).forEach(function (p) { ga('partner_impression', { venue: venue, partner: p.name, partner_id: p.id, has_perk: p.perk ? 'yes' : 'no', surface: 'web_ask' }); });
    Array.prototype.forEach.call(out.querySelectorAll('[data-ap]'), function (a) {
      a.addEventListener('click', function () { var p = r.partners[+a.getAttribute('data-ap')]; ga('partner_tap', { venue: venue, partner: p.name, partner_id: p.id, action: 'reserve', surface: 'web_ask' }); });
    });
  }
  function ga(name, params) { if (typeof window.gtag === 'function') { try { window.gtag('event', name, params); } catch (_) {} } }
  var busy = false;
  function ask(q) {
    q = String(q || '').trim(); if (q.length < 3 || busy) return;
    busy = true; ring.classList.add('is-thinking'); btn.disabled = true; btn.textContent = 'Thinking';
    out.hidden = false; out.innerHTML = '<p class="c-answer-kicker">Concerto</p><p class="c-answer-text c-answer-wait">Looking through Concerto’s guides…</p>';
    fetch('/.netlify/functions/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: q, demo: ccDemoKey() || undefined }) })
      .then(function (r) { if (r.status === 429) return { mode: 'none', text: 'Too many questions at once. Try again in a minute.', sources: [] }; return r.json(); })
      .then(function (r) {
        render(r);
        if (typeof window.gtag === 'function') { try { window.gtag('event', 'ask', { mode: r.mode || 'none', venue: r.entity && r.entity.venue ? 1 : 0, tour: r.entity && r.entity.tour ? 1 : 0, limited: r.limited || '' }); } catch (_) {} }
      })
      .catch(function () { render({ mode: 'none', text: 'Concerto couldn’t answer right now. Try again in a moment, or search below.', sources: [] }); })
      .then(function () { busy = false; ring.classList.remove('is-thinking'); btn.disabled = false; btn.textContent = 'Ask'; });
  }
  form.addEventListener('submit', function (e) { e.preventDefault(); ask(input.value); });
  var p = new URLSearchParams(location.search);
  if (p.get('q') && p.get('ask') === '1') { input.value = p.get('q'); ask(p.get('q')); }
})();

/* Partner checkout returns to /partners/thank-you?paid=1. The page's default text is for inquiries. */
(function () {
  'use strict';
  if (!/^\/partners[-\/]thank-you/.test(location.pathname)) return;
  var q = new URLSearchParams(location.search); if (q.get('paid') !== '1') return;
  var set = function (k, html) { var el = document.querySelector('[data-ty="' + k + '"]'); if (el) el.innerHTML = html; };
  set('eb', 'You’re a Concerto Partner');
  set('h', 'Payment received.<br>You’re going live.');
  set('lead', 'Your listing is live within five minutes. Stripe emails your receipt, and the link in it lets you cancel anytime. To change your listing or your Perk, email <a href="mailto:partners@concertocity.com">partners@concertocity.com</a>.');
  var venue = (q.get('venue') || '').toLowerCase();
  var act = document.querySelector('.c-hero .c-actions');
  if (act && /^[a-z0-9-]{2,120}$/.test(venue)) {
    var a = document.createElement('a'); a.className = 'c-btn c-btn-navy'; a.href = '/venue/' + venue; a.textContent = 'See your venue page';
    act.insertBefore(a, act.firstChild);
  }
  document.title = 'Payment received | Concerto Partners';
})();

/* A small label while demo partners are on, so a demo is never mistaken for the live site. */
(function () {
  if (!ccDemoKey()) return;
  var b = document.createElement('a'); b.href = '?demo=off'; b.className = 'cc-demo-badge'; b.textContent = 'Demo partners on · turn off';
  (document.body || document.documentElement).appendChild(b);
})();

/* Around the venue: the app's Nearby rows on venue pages, from Concerto's own nearby data
   (/data/nearby/<venue>.json, a static file, so no lookups and no cost per view). No photos,
   except Concerto Partners: they lead their row with their photo, like in the app. */
(function () {
  'use strict';
  var host = document.querySelector('[data-nearby]'); if (!host) return;
  var slug = host.getAttribute('data-nearby');
  // The app's icons (Ionicons): restaurant, bed, sparkles.
  var IC = { restaurants: "<path d=\"M357.57 223.94a79.48 79.48 0 0056.58-23.44l77-76.95c6.09-6.09 6.65-16 .85-22.39a16 16 0 00-23.17-.56l-68.63 68.58a12.29 12.29 0 01-17.37 0c-4.79-4.78-4.53-12.86.25-17.64l68.33-68.33a16 16 0 00-.56-23.16A15.62 15.62 0 00440.27 56a16.71 16.71 0 00-11.81 4.9l-68.27 68.26a12.29 12.29 0 01-17.37 0c-4.78-4.78-4.53-12.86.25-17.64l68.33-68.31a16 16 0 00-.56-23.16A15.62 15.62 0 00400.26 16a16.73 16.73 0 00-11.81 4.9L311.5 97.85a79.49 79.49 0 00-23.44 56.59v8.23a16 16 0 01-4.69 11.33l-35.61 35.62a4 4 0 01-5.66 0L68.82 36.33a16 16 0 00-22.58-.06C31.09 51.28 23 72.47 23 97.54c-.1 41.4 21.66 89 56.79 124.08l85.45 85.45A64.79 64.79 0 00211 326a64 64 0 0016.21-2.08 16.24 16.24 0 014.07-.53 15.93 15.93 0 0110.83 4.25l11.39 10.52a16.12 16.12 0 014.6 11.23v5.54a47.73 47.73 0 0013.77 33.65l90.05 91.57.09.1a53.29 53.29 0 0075.36-75.37L302.39 269.9a4 4 0 010-5.66L338 228.63a16 16 0 0111.32-4.69z\"/><path d=\"M211 358a97.32 97.32 0 01-68.36-28.25l-13.86-13.86a8 8 0 00-11.3 0l-85 84.56c-15.15 15.15-20.56 37.45-13.06 59.29a30.63 30.63 0 001.49 3.6C31 484 50.58 496 72 496a55.68 55.68 0 0039.64-16.44L225 365.66a4.69 4.69 0 001.32-3.72v-.26a4.63 4.63 0 00-5.15-4.27A97.09 97.09 0 01211 358z\"/>", hotels: "<path d=\"M432 230.7a79.44 79.44 0 00-32-6.7H112a79.51 79.51 0 00-32 6.69A80.09 80.09 0 0032 304v112a16 16 0 0032 0v-8a8.1 8.1 0 018-8h368a8.1 8.1 0 018 8v8a16 16 0 0032 0V304a80.09 80.09 0 00-48-73.3zM376 80H136a56 56 0 00-56 56v72a4 4 0 005.11 3.84A95.5 95.5 0 01112 208h4.23a4 4 0 004-3.55A32 32 0 01152 176h56a32 32 0 0131.8 28.45 4 4 0 004 3.55h24.46a4 4 0 004-3.55A32 32 0 01304 176h56a32 32 0 0131.8 28.45 4 4 0 004 3.55h4.2a95.51 95.51 0 0126.89 3.85A4 4 0 00432 208v-72a56 56 0 00-56-56z\"/>", more: "<path d=\"M208 512a24.84 24.84 0 01-23.34-16l-39.84-103.6a16.06 16.06 0 00-9.19-9.19L32 343.34a25 25 0 010-46.68l103.6-39.84a16.06 16.06 0 009.19-9.19L184.66 144a25 25 0 0146.68 0l39.84 103.6a16.06 16.06 0 009.19 9.19l103 39.63a25.49 25.49 0 0116.63 24.1 24.82 24.82 0 01-16 22.82l-103.6 39.84a16.06 16.06 0 00-9.19 9.19L231.34 496A24.84 24.84 0 01208 512zm66.85-254.84zM88 176a14.67 14.67 0 01-13.69-9.4l-16.86-43.84a7.28 7.28 0 00-4.21-4.21L9.4 101.69a14.67 14.67 0 010-27.38l43.84-16.86a7.31 7.31 0 004.21-4.21L74.16 9.79A15 15 0 0186.23.11a14.67 14.67 0 0115.46 9.29l16.86 43.84a7.31 7.31 0 004.21 4.21l43.84 16.86a14.67 14.67 0 010 27.38l-43.84 16.86a7.28 7.28 0 00-4.21 4.21l-16.86 43.84A14.67 14.67 0 0188 176zM400 256a16 16 0 01-14.93-10.26l-22.84-59.37a8 8 0 00-4.6-4.6l-59.37-22.84a16 16 0 010-29.86l59.37-22.84a8 8 0 004.6-4.6l22.67-58.95a16.45 16.45 0 0113.17-10.57 16 16 0 0116.86 10.15l22.84 59.37a8 8 0 004.6 4.6l59.37 22.84a16 16 0 010 29.86l-59.37 22.84a8 8 0 00-4.6 4.6l-22.84 59.37A16 16 0 01400 256z\"/>" };
  var ROWS = [['restaurants', 'Nearby Restaurants'], ['hotels', 'Nearby Hotels'], ['more', 'Nearby Things to Do']];
  var SKIP = ['convenience_store', 'gas_station', 'grocery_store', 'pharmacy', 'drugstore', 'atm', 'bank', 'car_repair', 'parking', 'storage'];
  var RENTAL = /apartment|studio|bedroom|\bapt\b|\d\s?-?(bd|bdr|br)\b|penthouse|condo|airbnb|luxurious|vacation/i;
  var LABEL = { sports_bar: 'Sports bar', bar_and_grill: 'Bar and grill', steak_house: 'Steakhouse', steakhouse: 'Steakhouse', pizza_restaurant: 'Pizza',
    mexican_restaurant: 'Mexican', italian_restaurant: 'Italian', japanese_restaurant: 'Japanese', sushi_restaurant: 'Sushi', ramen_restaurant: 'Ramen',
    chinese_restaurant: 'Chinese', thai_restaurant: 'Thai', indian_restaurant: 'Indian', american_restaurant: 'American', seafood_restaurant: 'Seafood',
    hamburger_restaurant: 'Burgers', barbecue_restaurant: 'Barbecue', breakfast_restaurant: 'Breakfast', brunch_restaurant: 'Brunch', cafe: 'Cafe',
    coffee_shop: 'Coffee', bar: 'Bar', night_club: 'Club', pub: 'Pub', wine_bar: 'Wine bar', cocktail_bar: 'Cocktails', bakery: 'Bakery',
    hotel: 'Hotel', lodging: 'Hotel', museum: 'Museum', park: 'Park', art_gallery: 'Gallery', tourist_attraction: 'Attraction', bowling_alley: 'Bowling',
    movie_theater: 'Movies', comedy_club: 'Comedy', performing_arts_theater: 'Theater', shopping_mall: 'Shopping', aquarium: 'Aquarium', zoo: 'Zoo',
    restaurant: 'Restaurant', food: 'Food' };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function kindOf(types) { for (var i = 0; i < (types || []).length; i++) if (LABEL[types[i]]) return LABEL[types[i]]; return ''; }
  function svg(k) { return '<svg width="20" height="20" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true">' + IC[k] + '</svg>'; }
  // Concerto Partners for this venue, published by the partner script; never wait more than 3s.
  var partnersReady = new Promise(function (resolve) {
    if (window.ccVenuePartners) return resolve(window.ccVenuePartners);
    var done = function () { resolve(window.ccVenuePartners || { restaurant: [], hotel: [] }); };
    document.addEventListener('cc:partners', done, { once: true });
    setTimeout(done, 3000);
  });
  var nearbyData = fetch('/data/nearby/' + encodeURIComponent(slug) + '.json').then(function (r) { if (!r.ok) throw 0; return r.json(); }).catch(function () { return null; });
  var vh = document.querySelector('[data-venue-tonight]');
  var vlat = vh && parseFloat(vh.getAttribute('data-lat')), vlng = vh && parseFloat(vh.getAttribute('data-lng'));
  Promise.all([nearbyData, partnersReady]).then(function (res) {
    var d = res[0] || { tabs: {} }, P = res[1] || {};
    var rows = host.querySelector('.cx-rows'), any = false;
    (function () {
      var lead = { restaurants: P.restaurant || [], hotels: P.hotel || [], more: [] };
      var taken = {};
      lead.restaurants.concat(lead.hotels).forEach(function (c) { taken[c.name.trim().toLowerCase()] = 1; });
      ROWS.forEach(function (rw) {
        var tab = (d.tabs && d.tabs[rw[0]]) || { items: [] };
        var seen = {};
        var list = (tab.items || []).filter(function (i) {
          var n = (i.name || '').trim().toLowerCase();
          if (!n || seen[n] || taken[n] || i.lat == null) return false; seen[n] = 1;
          if ((i.types || []).some(function (t) { return SKIP.indexOf(t) >= 0; })) return false;
          if (rw[0] === 'hotels' && RENTAL.test(i.name)) return false;
          return i.distance_mi == null || i.distance_mi <= 3;
        }).slice(0, 14);
        var partners = lead[rw[0]] || [];
        if (!list.length && !partners.length) return; any = true;
        var wrap = document.createElement('div');
        wrap.innerHTML = '<div class="cx-row-head"><h3>' + esc(rw[1]) + '</h3><div class="cx-row-arrows"><button type="button" aria-label="Previous">&#8249;</button><button type="button" aria-label="Next">&#8250;</button></div></div><div class="cx-scroll" role="list"></div>';
        var sc = wrap.querySelector('.cx-scroll');
        // Partners first: the same card as the app, with their photo, and the gold star when they have a Perk.
        partners.forEach(function (c, i) {
          if (typeof window.ccNearCard !== 'function') return;
          var card = window.ccNearCard(c, slug, vlat, vlng); card.classList.add('cx-partner'); sc.appendChild(card);
          if (typeof window.gtag === 'function') { try { window.gtag('event', 'partner_impression', { venue: slug, partner: c.name, partner_id: c.id, has_perk: c.perk ? 'yes' : 'no', surface: 'web_venue_' + c.kind, position: String(i + 1) }); } catch (_) {} }
        });
        list.forEach(function (i) {
          var a = document.createElement('a'); a.className = 'cx-place'; a.setAttribute('role', 'listitem'); a.target = '_blank'; a.rel = 'noopener';
          a.href = ccMapsUrl(i.name + ' ' + (i.address || ''), i.lat, i.lng, true);
          var meta = [i.price ? new Array(Math.min(i.price, 4) + 1).join('$') : '', kindOf(i.types), i.distance_mi != null ? (i.distance_mi < 0.1 ? 'Steps away' : i.distance_mi.toFixed(i.distance_mi < 10 ? 1 : 0) + ' mi') : ''].filter(Boolean).join(' · ');
          a.innerHTML = '<span class="cx-ic">' + svg(rw[0]) + '</span><b>' + esc(i.name) + '</b><small>' + esc(meta) + '</small><span class="cx-go">Directions</span>';
          sc.appendChild(a);
        });
        var btns = wrap.querySelectorAll('.cx-row-arrows button');
        var upd = function () { var max = sc.scrollWidth - sc.clientWidth - 2; btns[0].disabled = sc.scrollLeft <= 2; btns[1].disabled = sc.scrollLeft >= max; wrap.querySelector('.cx-row-arrows').style.visibility = max > 0 ? '' : 'hidden'; };
        btns[0].addEventListener('click', function () { sc.scrollBy({ left: -sc.clientWidth * 0.8, behavior: 'smooth' }); });
        btns[1].addEventListener('click', function () { sc.scrollBy({ left: sc.clientWidth * 0.8, behavior: 'smooth' }); });
        sc.addEventListener('scroll', function () { window.requestAnimationFrame(upd); }, { passive: true });
        rows.appendChild(wrap); setTimeout(upd, 0); window.addEventListener('resize', upd);
      });
      if (any) host.hidden = false;
    })();
  }).catch(function () {});
})();
