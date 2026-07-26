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

/* ═══════════════════════════════════════════════════════════════════
   IMAGE PIPELINE — ported from the app's src/data/queries.ts.
   The app fetches venue photos and artist images LIVE from the same
   Netlify functions this site hosts. The web does exactly the same,
   so both surfaces show the same imagery from the same source.
   Caching mirrors the app's react-query persistence: found images
   cached 30 days in localStorage; a null is never cached as fresh.
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  var DAY = 864e5;

  function cacheGet(key) {
    try {
      var raw = localStorage.getItem(key);
      if (!raw) return undefined;
      var v = JSON.parse(raw);
      if (v && v.exp > Date.now()) return v.val;
    } catch (e) {}
    return undefined;
  }
  function cacheSet(key, val, ttl) {
    try { localStorage.setItem(key, JSON.stringify({ val: val, exp: Date.now() + ttl })); } catch (e) {}
  }

  /* app: bestImage() — prefer 16:9, then widest */
  function bestImage(images) {
    if (!images || !images.length) return undefined;
    var wide = images.filter(function (i) { return i.ratio === '16_9'; });
    var pool = wide.length ? wide : images;
    return pool.sort(function (a, b) { return b.width - a.width; })[0].url;
  }

  /* app: diacritic-folded name matching (RÜFÜS DU SOL -> rufusdusol) */
  function norm(x) {
    return x.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  function setImg(container, src, alt) {
    var img = new Image();
    img.alt = alt || '';
    img.loading = 'lazy';
    img.onload = function () {
      container.querySelectorAll('img,.mono,.ini').forEach(function (n) { n.remove(); });
      container.insertBefore(img, container.firstChild);
      img.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .4s';
      requestAnimationFrame(function () { img.style.opacity = 1; });
    };
    img.src = src;
  }

  /* VENUE PHOTOS — app: useGoogleVenuePhoto -> /.netlify/functions/venue-photo */
  document.querySelectorAll('[data-vphoto]').forEach(function (el) {
    var name = el.getAttribute('data-vname'), city = el.getAttribute('data-vcity');
    var lat = el.getAttribute('data-vlat'), lng = el.getAttribute('data-vlng');
    if (!name || !lat) return;
    var key = 'cw.vphoto.' + norm(name);
    var hit = cacheGet(key);
    if (hit) { setImg(el, hit, name); return; }
    if (hit === null) return; /* coordinate-verified "no photo": honored, but expired nulls refetch */
    var p = new URLSearchParams({ name: name, city: city || '', lat: lat, lng: lng });
    fetch('/.netlify/functions/venue-photo?' + p).then(function (r) {
      if (r.status === 404) { cacheSet(key, null, DAY); return null; }
      if (!r.ok) throw 0;
      return r.json();
    }).then(function (d) {
      if (d && d.src) { cacheSet(key, d.src, 30 * DAY); setImg(el, d.src, name); }
    }).catch(function () {});
  });

  /* ARTIST IMAGES — app: useArtistImage -> tm/events.json, name-contains match */
  document.querySelectorAll('[data-artist]').forEach(function (el) {
    var artist = el.getAttribute('data-artist');
    if (!artist) return;
    var key = 'cw.artist.' + norm(artist);
    var hit = cacheGet(key);
    if (hit) { hydrateTile(el, hit, artist); return; }
    var p = new URLSearchParams({
      keyword: artist, classificationName: 'Music', size: '3',
      sort: 'date,asc',
      startDateTime: new Date().toISOString().replace(/\.\d+Z$/, 'Z')
    });
    fetch('/.netlify/functions/tm/events.json?' + p).then(function (r) {
      if (!r.ok) throw 0; return r.json();
    }).then(function (d) {
      var events = (d && d._embedded && d._embedded.events) || [];
      var target = norm(artist);
      var best = events.find(function (e) { return e.name && norm(e.name).indexOf(target) !== -1; }) || events[0];
      var src = best && bestImage(best.images);
      if (src) { cacheSet(key, src, 30 * DAY); hydrateTile(el, src, artist); }
    }).catch(function () {});
  });

  function hydrateTile(tile, src, alt) {
    var img = new Image();
    img.alt = alt; img.loading = 'lazy';
    img.onload = function () {
      var ini = tile.querySelector('.ini'); if (ini) ini.remove();
      img.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .4s';
      tile.insertBefore(img, tile.firstChild);
      requestAnimationFrame(function () { img.style.opacity = 1; });
    };
    img.src = src;
  }
})();

/* ═══════════════════════════════════════════════════════════════════
   USER STATE SYNC — the same Supabase account, on the web.
   The app writes profiles.{display_name, is_premium, saved_events,
   favorite_venues}; the site's own auth (auth.js / login.html)
   signs into the SAME project. This block reads that session and
   makes the homepage YOURS, exactly like opening the app:
   greeting with your name, your real next show counting down live,
   your member status on the NightCard. Signed-out visitors see the
   default page unchanged. Read-only; fails silent.
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  var URL = 'https://qgvukssbtfkbvahaiejm.supabase.co';
  var ANON = 'sb_publishable_xuc86SqqrndgPMj5ToBuvw_EHDkRwYY';

  /* the supabase-js session lives in localStorage under sb-*-auth-token */
  function session() {
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (/^sb-.*-auth-token$/.test(k)) {
          var v = JSON.parse(localStorage.getItem(k));
          var s = v && (v.currentSession || v);
          if (s && s.access_token && s.user) return s;
        }
      }
    } catch (e) {}
    return null;
  }

  var sess = session();
  var signin = document.getElementById('tbSignin');
  if (!sess) return;
  if (signin) signin.style.display = 'none';

  fetch(URL + '/rest/v1/profiles?id=eq.' + sess.user.id +
        '&select=display_name,is_premium,saved_events,favorite_venues', {
    headers: { apikey: ANON, Authorization: 'Bearer ' + sess.access_token }
  }).then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (rows) {
      var p = rows && rows[0];
      if (!p) return;

      /* 1) Greeting gains the first name — the app's exact fallback chain */
      var g = document.getElementById('greeting');
      if (g) {
        var name = (p.display_name || (sess.user.email || '').split('@')[0] || '').split(' ')[0];
        if (name) g.textContent = g.textContent + ', ' + name.toUpperCase();
      }

      /* 2) The real Next Show, counting down live (the app's spine) */
      var card = document.querySelector('.next-empty');
      var shows = Array.isArray(p.saved_events) ? p.saved_events : [];
      var cutoff = Date.now() - 6 * 36e5;
      var next = shows
        .filter(function (e) { return e && e.date && new Date(e.date).getTime() > cutoff; })
        .sort(function (a, b) { return new Date(a.date) - new Date(b.date); })[0];
      if (card && next) {
        var when = new Date(next.date).getTime();
        card.href = next.venueSlug ? '/venues/' + next.venueSlug : card.href;
        card.innerHTML =
          '<p class="ne-eyebrow">YOUR NEXT SHOW</p>' +
          '<p class="ne-text">' + String(next.name || '').replace(/</g, '&lt;') + '</p>' +
          '<p style="font-size:12px;color:rgba(248,249,249,.65);margin-top:2px">' +
            String(next.venueName || '').replace(/</g, '&lt;') +
            (next.doors ? ' &middot; ' + next.doors : '') + '</p>' +
          '<div class="ne-countrow" id="realCount" style="border-style:solid;border-color:rgba(248,249,249,.11)">' +
            ['DAYS', 'HRS', 'MIN', 'SEC'].map(function (l, i) {
              return (i ? '<div class="ne-colon">:</div>' : '') +
                '<div class="ne-cell"><div class="ne-val" data-u="' + l + '" style="color:var(--cream)">--</div>' +
                '<div class="ne-lab" style="color:var(--gold)">' + l + '</div></div>';
            }).join('') +
          '</div>' +
          '<span class="ne-cta">Open in the app</span>';
        function pad(n) { return (n < 10 ? '0' : '') + n; }
        function tick() {
          var ms = when - Date.now();
          var el = function (u) { return card.querySelector('[data-u="' + u + '"]'); };
          if (ms <= 0) {
            var row = card.querySelector('#realCount');
            if (row) row.innerHTML = '<span style="font-family:var(--display);font-size:18px;color:var(--cream)">' +
              '<span style="display:inline-block;width:8px;height:8px;border-radius:4px;background:var(--gold);margin-right:8px"></span>' +
              "It's showtime</span>";
            return;
          }
          var s = Math.floor(ms / 1e3);
          el('DAYS').textContent = pad(Math.floor(s / 86400));
          el('HRS').textContent = pad(Math.floor(s % 86400 / 3600));
          el('MIN').textContent = pad(Math.floor(s % 3600 / 60));
          el('SEC').textContent = pad(s % 60);
          setTimeout(tick, 1000);
        }
        tick();
      }

      /* 3) Member status on the NightCard, like the app */
      if (p.is_premium) {
        var brand = document.querySelector('.nc-brand');
        var title = document.querySelector('.nc-title');
        var price = document.querySelector('.nc-price');
        var cta = document.querySelector('.nc-cta');
        if (brand) brand.innerHTML = 'Concerto+ &nbsp;<span style="border:1px solid rgba(201,168,76,.5);border-radius:999px;padding:2px 8px;font-size:9px;letter-spacing:1px">MEMBER</span>';
        if (title) title.textContent = "Tonight's Toolkit";
        if (price) price.textContent = 'Bag Check & Plan My Night, unlocked';
        if (cta) cta.firstChild.nodeValue = 'Open the app';
      }

      /* 4) Favorite venues lead the rail, like the app */
      var favs = Array.isArray(p.favorite_venues) ? p.favorite_venues : [];
      if (favs.length) {
        var rail = document.querySelector('.rail');
        if (rail) {
          [].slice.call(rail.querySelectorAll('.vcard')).reverse().forEach(function (c) {
            var slug = (c.getAttribute('href') || '').split('/').pop();
            var name = c.querySelector('.vc-name');
            if (favs.indexOf(slug) !== -1 || (name && favs.indexOf(name.textContent) !== -1)) {
              rail.insertBefore(c, rail.firstChild);
            }
          });
        }
      }
    }).catch(function () {});
})();

/* ═══ "Get the app" banner — the Airbnb top strip, Concerto's version.
   Mobile only, inline at the very top (not fixed), dismissible for
   the session. Sits under Safari's native Smart App Banner. ═══ */
(function () {
  if (window.innerWidth > 820) return;
  try { if (sessionStorage.getItem('getAppBannerDismissed')) return; } catch (e) {}
  var APP_URL = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414';
  var b = document.createElement('div');
  b.id = 'getAppBanner';
  b.style.cssText = 'display:flex;align-items:center;gap:12px;padding:10px 14px;' +
    'background:var(--surface,#fff);border-bottom:1px solid var(--line,rgba(18,30,54,.14));' +
    'font-family:"DM Sans",-apple-system,sans-serif;position:relative;z-index:999';
  b.innerHTML =
    '<button aria-label="Dismiss" style="background:none;border:0;color:var(--ink-faint,#8A91A3);font-size:16px;padding:4px;cursor:pointer;line-height:1">&#10005;</button>' +
    '<img src="/img/app-icon.png" alt="" width="44" height="44" style="border-radius:10px;flex:none"/>' +
    '<span style="flex:1;min-width:0">' +
      '<b style="display:block;font-size:14px;color:var(--ink,#121E36)">Get the app</b>' +
      '<span style="display:block;font-size:11.5px;color:var(--ink-muted,#5A6478);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">The fastest way from the concert to the city</span>' +
    '</span>' +
    '<a href="' + APP_URL + '" style="background:var(--gold,#C9A84C);color:var(--navy,#121E36);font-weight:700;font-size:12px;letter-spacing:.04em;border-radius:999px;padding:9px 16px;text-decoration:none;white-space:nowrap">USE APP</a>';
  b.querySelector('button').addEventListener('click', function () {
    try { sessionStorage.setItem('getAppBannerDismissed', '1'); } catch (e) {}
    b.remove();
  });
  function mount() {
    document.body.insertBefore(b, document.body.firstChild);
    /* the fixed topbar slides below the banner while it's visible */
    var tb = document.querySelector('.topbar');
    function offset() {
      var h = b.parentNode ? b.offsetHeight : 0;
      if (tb) tb.style.top = h + 'px';
      document.documentElement.style.scrollPaddingTop = h + 'px';
    }
    offset();
    window.addEventListener('scroll', function onS() {
      /* banner scrolls away naturally; topbar returns to the top */
      var gone = window.scrollY > b.offsetHeight;
      if (tb) tb.style.top = gone ? '0px' : (b.parentNode ? b.offsetHeight - Math.min(window.scrollY, b.offsetHeight) : 0) + 'px';
    }, { passive: true });
    b.querySelector('button').addEventListener('click', function () { if (tb) tb.style.top = '0px'; });
  }
  if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);
})();

/* ═══════════════════════════════════════════════════════════════════
   GET-THE-APP BANNER — the Airbnb pattern, sitewide.
   Apple's Smart App Banner (the meta tag, already on all 461 pages)
   only shows in Safari. This is the second, always-visible bar every
   app-first company runs underneath it: icon, one line of value, one
   button. Dismissible, and the dismissal sticks for 30 days so it
   never nags. Mobile only -- on desktop the top bar already carries
   "Get the App".
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  if (window.matchMedia('(min-width:821px)').matches) return;
  if (document.querySelector('.appbar')) return;
  var KEY = 'concerto.appbar.dismissed';
  try { if (+(localStorage.getItem(KEY) || 0) > Date.now()) return; } catch (e) {}

  var APP_URL = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414';
  var css = document.createElement('style');
  css.textContent =
    '.appbar{position:sticky;top:0;z-index:1100;display:flex;align-items:center;gap:12px;' +
      'padding:10px 14px;background:#121E36;color:#F8F9F9;font-family:"DM Sans",-apple-system,sans-serif}' +
    '.appbar-x{background:none;border:0;color:rgba(248,249,249,.5);font-size:17px;line-height:1;' +
      'padding:4px 2px;cursor:pointer;flex:none}' +
    '.appbar-icon{width:40px;height:40px;border-radius:9px;flex:none;background:#F8F9F9}' +
    '.appbar-text{flex:1;min-width:0}' +
    '.appbar-t{font-size:14px;font-weight:700;line-height:1.2}' +
    '.appbar-s{font-size:11.5px;color:rgba(248,249,249,.62);line-height:1.3;margin-top:1px;' +
      'white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.appbar-cta{flex:none;background:#C9A84C;color:#121E36;font-size:12.5px;font-weight:700;' +
      'letter-spacing:.04em;border-radius:999px;padding:9px 16px;text-decoration:none}';
  document.head.appendChild(css);

  var bar = document.createElement('aside');
  bar.className = 'appbar';
  bar.setAttribute('aria-label', 'Get the Concerto app');
  bar.innerHTML =
    '<button class="appbar-x" aria-label="Dismiss">\u2715</button>' +
    '<img class="appbar-icon" src="/img/app-icon.png" alt="" width="40" height="40"/>' +
    '<div class="appbar-text">' +
      '<div class="appbar-t">Get the app</div>' +
      '<div class="appbar-s">Bag check, parking, and your night \u2014 planned</div>' +
    '</div>' +
    '<a class="appbar-cta" href="' + APP_URL + '" target="_blank" rel="noopener noreferrer">USE APP</a>';

  bar.querySelector('.appbar-x').addEventListener('click', function () {
    try { localStorage.setItem(KEY, String(Date.now() + 30 * 864e5)); } catch (e) {}
    bar.remove();
  });

  function mount() { document.body.insertBefore(bar, document.body.firstChild); }
  if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);
})();
