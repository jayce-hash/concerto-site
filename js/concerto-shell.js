/* Concerto web shell: the app's chrome, on the web.
   Top bar scroll state, the bottom tab bar (mobile), the live
   countdown, and reveal-on-scroll. No libraries. */
(function () {
  var APP_URL = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414';

  /* greeting, exactly like the app's Home masthead */
  var g = document.getElementById('greeting');
  if (g) {
    var h = new Date().getHours();
    g.textContent = h < 12 ? 'GOOD MORNING' : h < 17 ? 'GOOD AFTERNOON' : 'GOOD EVENING';
  }

  /* live countdown: real target, persisted per visitor */
  var KEY = 'concertoHeroTarget'; var t;
  try { t = parseInt(localStorage.getItem(KEY) || '0', 10); } catch (e) { t = 0; }
  var now = Date.now();
  if (!t || t - now < 36e5 || t - now > 12 * 864e5) {
    t = now + 5 * 864e5 + 8 * 36e5 + 42 * 6e4;
    try { localStorage.setItem(KEY, String(t)); } catch (e) {}
  }
  var cells = {};
  ['d', 'h', 'm', 's'].forEach(function (u) {
    cells[u] = document.querySelector('#liveCount [data-u="' + u + '"]');
  });
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function tick() {
    var ms = Math.max(0, t - Date.now()), s = Math.floor(ms / 1e3);
    if (cells.d) {
      cells.d.textContent = pad(Math.floor(s / 86400));
      cells.h.textContent = pad(Math.floor(s % 86400 / 3600));
      cells.m.textContent = pad(Math.floor(s % 3600 / 60));
      cells.s.textContent = pad(s % 60);
    }
  }
  tick(); setInterval(tick, 1000);

  /* top bar hairline */
  var tb = document.querySelector('.topbar');
  if (tb) {
    var on = function () { tb.classList.toggle('scrolled', window.scrollY > 8); };
    window.addEventListener('scroll', on, { passive: true }); on();
  }

  /* bottom tab bar: the app's nav, on mobile web */
  if (!document.querySelector('.tabbar')) {
    var ic = {
      home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>',
      venues: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 21h18M5 21V8l7-5 7 5v13"/><path d="M9 21v-6h6v6"/></svg>',
      tours: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3.5"/></svg>',
      near: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m3 11 18-8-8 18-2.5-7.5L3 11z"/></svg>',
      get: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v12m0 0 4-4m-4 4-4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>'
    };
    var path = location.pathname;
    function act(p) { return (p === '/' && (path === '/' || path === '/index.html')) || (p !== '/' && path.indexOf(p) === 0) ? ' class="active"' : ''; }
    var bar = document.createElement('nav');
    bar.className = 'tabbar';
    bar.setAttribute('aria-label', 'Concerto');
    bar.innerHTML =
      '<a href="/"' + act('/') + '>' + ic.home + 'Home</a>' +
      '<a href="/venues"' + act('/venues') + '>' + ic.venues + 'Venues</a>' +
      '<a href="/tours"' + act('/tours') + '>' + ic.tours + 'Tours</a>' +
      '<a href="/events"' + act('/events') + '>' + ic.near + 'Near Me</a>' +
      '<a href="' + APP_URL + '" style="color:var(--gold)">' + ic.get + 'Get App</a>';
    document.body.appendChild(bar);
  }

  /* reveals */
  var io = ('IntersectionObserver' in window) ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { threshold: .12 }) : null;
  document.querySelectorAll('.rv').forEach(function (el) { io ? io.observe(el) : el.classList.add('in'); });
})();
