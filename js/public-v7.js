/* Concerto V7: the interactions that make the site a product, not a brochure.
   Reveal on scroll, phase dial, count-up, live "tonight near you", venue lookup.
   Everything degrades: no JS, the page still reads. Reduce Motion: no movement. */
(function () {
  'use strict';
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var FN = '/.netlify/functions';
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  /* Reveal */
  var reveals = $$('.reveal');
  if (reduce || !('IntersectionObserver' in window)) reveals.forEach(function (el) { el.classList.add('in'); });
  else { var io = new IntersectionObserver(function (es) { es.forEach(function (x) { if (x.isIntersecting) { x.target.classList.add('in'); io.unobserve(x.target); } }); }, { rootMargin: '0px 0px -10% 0px', threshold: 0.12 }); reveals.forEach(function (el) { io.observe(el); }); }

  /* Phase dial: the sticky label follows the step in view */
  var num = $('[data-phase-num]'), name = $('[data-phase-name]');
  if (num && 'IntersectionObserver' in window) {
    var po = new IntersectionObserver(function (es) { es.forEach(function (x) { if (x.isIntersecting) { num.textContent = x.target.getAttribute('data-phase-index'); name.textContent = x.target.getAttribute('data-phase-label'); } }); }, { rootMargin: '-40% 0px -50% 0px' });
    $$('.v7-phase').forEach(function (el) { po.observe(el); });
  }

  /* Count-up */
  $$('[data-count]').forEach(function (el) {
    var target = parseInt(el.getAttribute('data-count'), 10); if (!isFinite(target)) return;
    if (reduce || !('IntersectionObserver' in window)) { el.textContent = target; return; }
    el.textContent = '0';
    var co = new IntersectionObserver(function (es) { es.forEach(function (x) { if (!x.isIntersecting) return; co.disconnect(); var t0 = null; function step(t) { if (!t0) t0 = t; var k = Math.min(1, (t - t0) / 900); k = 1 - Math.pow(1 - k, 3); el.textContent = Math.round(target * k); if (k < 1) requestAnimationFrame(step); } requestAnimationFrame(step); }); }, { threshold: 0.5 });
    co.observe(el);
  });

  /* Countdown: days until, in whole calendar days; never below "Show day" */
  $$('[data-countdown]').forEach(function (el) {
    var t = new Date(el.getAttribute('data-countdown')); if (isNaN(t)) return;
    var days = Math.floor((t - new Date()) / 86400000);
    if (days < 0) { var w = el.closest('.v7-ticket-count'); if (w) w.innerHTML = '<b>Tonight</b><span>your night is ready</span>'; return; }
    el.textContent = String(days);
  });

  /* Tonight near you: real event, real venue, real time; the example stays if nothing is on */
  var ticket = $('[data-live-ticket]');
  if (ticket && window.fetch) {
    fetch(FN + '/geo').then(function (r) { return r.json(); }).then(function (g) {
      if (!g || !g.lat) return;
      var now = new Date(), end = new Date(now.getTime() + 7 * 86400000);
      var p = new URLSearchParams({ size: '5', sort: 'date,asc', classificationName: 'Music', latlong: g.lat + ',' + g.lng, radius: '60', unit: 'miles', startDateTime: now.toISOString().split('.')[0] + 'Z', endDateTime: end.toISOString().split('.')[0] + 'Z' });
      if (g.country) p.set('countryCode', g.country);
      return fetch(FN + '/tm?' + p.toString()).then(function (r) { return r.json(); }).then(function (d) {
        var ev = (d && d._embedded && d._embedded.events || []).filter(function (x) { return x.dates && x.dates.start && !x.dates.start.timeTBA; })[0]; if (!ev) return;
        var v = ev._embedded && ev._embedded.venues && ev._embedded.venues[0] || {};
        var start = ev.dates.start.dateTime ? new Date(ev.dates.start.dateTime) : new Date(ev.dates.start.localDate + 'T19:30:00');
        var isToday = start.toDateString() === now.toDateString();
        $('[data-ticket-kicker]', ticket).textContent = isToday ? 'Tonight near you' : 'This week near you';
        $('[data-ticket-artist]', ticket).textContent = ev.name.split(/: | - | – /)[0];
        $('[data-ticket-venue]', ticket).textContent = [v.name, v.city && v.city.name, v.state && v.state.stateCode].filter(Boolean).join(' · ').replace(' · ', ' · ');
        $('[data-ticket-when]', ticket).textContent = start.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }) + (ev.dates.start.localTime ? ' · Show ' + start.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : '');
        var c = $('.v7-ticket-count', ticket); var days = Math.floor((start - now) / 86400000);
        c.innerHTML = days <= 0 ? '<b>Tonight</b><span>doors before you know it</span>' : '<b>' + days + '</b><span>' + (days === 1 ? 'day' : 'days') + ' to show day</span>';
        var link = $('[data-ticket-link]', ticket); if (link && ev.url) { link.href = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414?pt=127753814&ct=website-ticket&mt=8'; link.textContent = 'Save this night in Concerto →'; }
        ticket.classList.add('is-live');
      });
    }).catch(function () {});
  }

  /* Venue lookup: the product, on the page */
  var input = $('[data-venue-search]'), result = $('[data-venue-result]'), hint = $('[data-venue-hint]');
  if (input && result) {
    var data = null, loading = null;
    function load() { if (!loading) loading = fetch('/data/venue_lookup.json').then(function (r) { return r.json(); }).then(function (d) { data = d; return d; }); return loading; }
    function norm(s) { return String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]/g, ''); }
    function card(title, s) {
      if (!s) return '<figure class="night-card night-card-paper"><div class="nc-head"><h3>' + esc(title) + '</h3><span class="nc-verified nc-unverified">Not yet verified</span></div><p class="nc-body">Concerto has not confirmed this yet. It will say so in the app too.</p></figure>';
      var lists = (s.allowed.length || s.prohibited.length) ? '<div class="nc-lists">' + (s.allowed.length ? '<div><span class="nc-label">Allowed</span><ul>' + s.allowed.map(function (a) { return '<li>' + esc(a) + '</li>'; }).join('') + '</ul></div>' : '') + (s.prohibited.length ? '<div><span class="nc-label">Not allowed</span><ul class="no">' + s.prohibited.map(function (a) { return '<li>' + esc(a) + '</li>'; }).join('') + '</ul></div>' : '') + '</div>' : '';
      return '<figure class="night-card night-card-paper"><div class="nc-head"><h3>' + esc(title) + '</h3>' + (s.verified ? '<span class="nc-verified">Verified ' + esc(s.verified) + '</span>' : '') + '</div><p class="nc-body">' + esc(s.summary) + '</p>' + lists + (s.link && /^https:/.test(s.link) ? '<a class="nc-link" href="' + esc(s.link) + '" target="_blank" rel="noopener">Official source ↗</a>' : '') + '</figure>';
    }
    function render(v) {
      $('.v7-try-cards', result).innerHTML = card('Bag Policy', v.bag) + card('Parking', v.parking) + card('Rideshare', v.ride);
      var a = $('[data-venue-page]', result); if (a) { a.href = '/venue/' + v.slug; a.textContent = 'Full guide for ' + v.name + ' →'; }
      hint.textContent = v.city ? v.city + (v.state ? ', ' + v.state : '') : '';
    }
    input.addEventListener('focus', function () { load(); });
    input.addEventListener('input', function () {
      var q = norm(input.value); if (q.length < 2) { hint.textContent = 'Start typing'; return; }
      load().then(function (d) {
        var hit = d.find(function (v) { return norm(v.name).indexOf(q) === 0; }) || d.find(function (v) { return norm(v.name).indexOf(q) >= 0; }) || d.find(function (v) { return norm(v.city).indexOf(q) === 0; });
        if (hit) render(hit); else hint.textContent = 'Not covered yet. Ask for it in the app.';
      });
    });
  }
})();
