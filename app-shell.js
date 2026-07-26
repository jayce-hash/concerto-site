// ─────────────────────────────────────────
// CONCERTO APP SHELL
// Drop-in native-app chrome (frosted appbar with hamburger menu + bottom tab bar)
// for any page that does not already ship its own app bar.
// Include once per page, after auth.js:  <script src="app-shell.js"></script>
//
// Activates ONLY when:
//   • running inside the native (Capacitor) app, OR
//   • the session was started from the app home (mobile.html marks it, app-only), OR
//   • the URL has ?app=1  (per-page preview , never persisted, never leaks)
// On normal desktop/mobile web it does nothing. ?app=0 clears a preview/session flag.
//
// Header: logo left, hamburger right. Tapping the hamburger opens a slide-out menu
// with every section (matches the hand-built mobile-*.html pages).
// Bottom tab bar: Home · Venues · Tours · Near Me · Account, active tab auto-detected.
//
// If the page ALREADY has an app bar (.app-appbar), this script does nothing , the
// page's own hamburger wins, so there is never a double bar.
// ─────────────────────────────────────────
(function () {
  var LOGO_H = 48; // keep in sync with mobile.html .appbar-logo height
  var APP_KEY = 'concerto-app-session';

  // ── Activation (app-only; preview never persists) ──
  var params = new URLSearchParams(location.search);
  if (params.get('app') === '0') { try { sessionStorage.removeItem(APP_KEY); } catch (e) {} }
  var preview = params.get('app') === '1';
  var inNativeApp = !!window.Capacitor;
  if (inNativeApp) { try { sessionStorage.setItem(APP_KEY, '1'); } catch (e) {} }
  var sessionApp = false;
  try { sessionApp = sessionStorage.getItem(APP_KEY) === '1'; } catch (e) {}

  if (!inNativeApp && !sessionApp && !preview) return; // normal web , leave the page alone
  var usingPreview = !inNativeApp && !sessionApp && preview;

  var CSS = [
    'body.app-shell-on{',
      '--nav-h:0px !important;',
      'padding-top:calc(env(safe-area-inset-top) + ' + (LOGO_H + 22) + 'px) !important;',
      'padding-bottom:calc(env(safe-area-inset-bottom) + 64px) !important;',
    '}',
    'body.app-shell-on .site-nav,',
    'body.app-shell-on .nav-mobile-menu{display:none !important;}',

    '.app-appbar{',
      'position:fixed;top:0;left:0;right:0;z-index:1000;box-sizing:border-box;',
      'display:flex;align-items:center;justify-content:space-between;',
      'padding:calc(env(safe-area-inset-top) + 10px) 20px 12px;',
      'background:rgba(248,249,249,0.78);',
      'backdrop-filter:saturate(160%) blur(14px);',
      '-webkit-backdrop-filter:saturate(160%) blur(14px);',
      'border-bottom:1px solid transparent;',
      'transition:border-color .2s, background .2s;',
    '}',
    '.app-appbar.scrolled{border-bottom-color:rgba(18,30,54,0.08);background:rgba(248,249,249,0.92);}',
    '.app-appbar-logo{height:' + LOGO_H + 'px;width:auto;display:block;}',

    // hamburger button
    '.app-appbar-menu{background:none;border:none;color:#121E36;padding:6px;cursor:pointer;display:flex;align-items:center;}',

    // slide-out menu (matches mobile-*.html appmenu-css)
    '.app-menu-overlay{position:fixed;inset:0;z-index:1001;background:rgba(12,20,36,.45);opacity:0;pointer-events:none;transition:opacity .25s;}',
    '.app-menu-overlay.open{opacity:1;pointer-events:auto;}',
    '.app-menu{position:fixed;top:0;right:0;height:100%;width:80%;max-width:320px;background:#F8F9F9;box-shadow:-16px 0 50px rgba(18,30,54,.2);transform:translateX(100%);transition:transform .3s cubic-bezier(.16,1,.3,1);display:flex;flex-direction:column;padding:4.6rem 1.6rem 2rem;overflow-y:auto;box-sizing:border-box;}',
    '.app-menu-overlay.open .app-menu{transform:translateX(0);}',
    ".app-menu a{font-family:'Playfair Display',Georgia,serif;font-size:1.35rem;font-weight:600;color:#121E36;text-decoration:none;padding:.8rem 0;border-bottom:1px solid rgba(18,30,54,.08);}",
    '.app-menu a:last-child{border-bottom:none;}',
    '.app-menu-close{position:absolute;top:1rem;right:1.3rem;background:none;border:none;font-size:1.7rem;color:#121E36;cursor:pointer;line-height:1;}',

    '.app-tabbar{',
      'position:fixed;left:0;right:0;bottom:0;z-index:1000;',
      'display:grid;grid-template-columns:repeat(5,1fr);',
      'padding:6px 4px calc(env(safe-area-inset-bottom) + 4px);',
      'background:rgba(248,249,249,0.88);',
      'backdrop-filter:saturate(160%) blur(18px);',
      '-webkit-backdrop-filter:saturate(160%) blur(18px);',
      'border-top:1px solid rgba(18,30,54,0.08);',
    '}',
    '.app-tab{',
      'display:flex;flex-direction:column;align-items:center;justify-content:center;',
      'gap:3px;padding:8px 4px 6px;text-decoration:none;color:rgba(18,30,54,0.28);',
      'transition:color .15s, transform .15s cubic-bezier(0.16,1,0.3,1);',
    '}',
    '.app-tab svg{width:22px;height:22px;stroke-width:1.75;}',
    '.app-tab-label{font-size:0.62rem;font-weight:600;letter-spacing:0.02em;}',
    '.app-tab.active{color:#121E36;}',
    '.app-tab:active{transform:scale(0.94);}'
  ].join('');

  var TABS = [
    ['home',   '/mobile.html',        'Home',   '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h14V10"/>'],
    ['venues', '/mobile-venues.html', 'Venues', '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>'],
    ['tours',  '/mobile-tours.html',  'Tours',  '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>'],
    ['events', '/mobile-events.html', 'Near Me', '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>'],
    ['account', '/mobile-account.html', 'Account', '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-7 8-7s8 3 8 7"/>']
  ];

  // Slide-out menu links (mirrors the hand-built mobile-*.html menu).
  var MENU = [
    ['Venues',      '/venues.html'],
    ['Tours',       '/tours.html'],
    ['Near Me',     '/events.html'],
    ['Top Picks',   '/mobile-top-picks.html'],
    ['Bag Policies', '/bags.html'],
    ['Rideshare',   '/rideshare.html'],
    ['Parking',     '/parking.html'],
    ['Concessions', '/concessions.html'],
    ['Premium',     '/premium.html'],
    ['About',       '/about.html']
  ];

  function activeKey() {
    var p = location.pathname.toLowerCase();
    if (p.indexOf('/venues') > -1 || p.indexOf('venues.html') > -1) return 'venues';
    if (p.indexOf('/tours') > -1 || p.indexOf('tours.html') > -1) return 'tours';
    if (p.indexOf('events.html') > -1) return 'events';
    if (p.indexOf('account.html') > -1) return 'account';
    if (p.indexOf('mobile.html') > -1 || p === '/' || p.indexOf('index.html') > -1) return 'home';
    return '';
  }

  function build() {
    // If the page already ships its own app bar, or we've already run, do nothing.
    if (document.querySelector('.app-appbar') || document.getElementById('appShellStyle')) return;

    document.body.classList.add('app-shell-on');

    var style = document.createElement('style');
    style.id = 'appShellStyle';
    style.textContent = CSS;
    document.head.appendChild(style);

    var q = usingPreview ? '?app=1' : '';

    // ── Top app bar: logo + hamburger ──
    var bar = document.createElement('header');
    bar.className = 'app-appbar';
    bar.id = 'appShellBar';
    bar.innerHTML =
      '<a href="/mobile.html" aria-label="Concerto Home"><img src="/logo.png" alt="Concerto" class="app-appbar-logo"></a>' +
      '<button id="appShellMenuBtn" class="app-appbar-menu" aria-label="Open menu" aria-expanded="false">' +
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>' +
      '</button>';
    document.body.insertBefore(bar, document.body.firstChild);

    // ── Slide-out menu ──
    var overlay = document.createElement('div');
    overlay.className = 'app-menu-overlay';
    overlay.id = 'appShellMenuOverlay';
    overlay.setAttribute('aria-hidden', 'true');
    var links = MENU.map(function (m) { return '<a href="' + m[1] + q + '">' + m[0] + '</a>'; }).join('');
    overlay.innerHTML =
      '<nav class="app-menu" aria-label="Menu">' +
        '<button class="app-menu-close" id="appShellMenuClose" aria-label="Close menu">&times;</button>' +
        links +
      '</nav>';
    document.body.appendChild(overlay);

    // ── Bottom tab bar ──
    var key = activeKey();
    var tabsHtml = TABS.map(function (t) {
      var cls = 'app-tab' + (t[0] === key ? ' active' : '');
      var cur = t[0] === key ? ' aria-current="page"' : '';
      return '<a href="' + t[1] + q + '" class="' + cls + '" data-tab="' + t[0] + '"' + cur + '>'
        + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        + t[3] + '</svg><span class="app-tab-label">' + t[2] + '</span></a>';
    }).join('');

    var nav = document.createElement('nav');
    nav.className = 'app-tabbar';
    nav.setAttribute('aria-label', 'Main');
    nav.innerHTML = tabsHtml;
    document.body.appendChild(nav);

    // ── Appbar scroll state ──
    var onScroll = function () { bar.classList.toggle('scrolled', window.scrollY > 4); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    // ── Hamburger open/close ──
    (function () {
      var b = document.getElementById('appShellMenuBtn');
      var o = overlay;
      var c = document.getElementById('appShellMenuClose');
      if (!b || !o) return;
      function op() { o.classList.add('open'); b.setAttribute('aria-expanded', 'true'); document.body.style.overflow = 'hidden'; }
      function cl() { o.classList.remove('open'); b.setAttribute('aria-expanded', 'false'); document.body.style.overflow = ''; }
      b.addEventListener('click', op);
      if (c) c.addEventListener('click', cl);
      o.addEventListener('click', function (e) { if (e.target === o) cl(); });
    })();
  }

  if (document.body) build();
  else document.addEventListener('DOMContentLoaded', build);
})();


// ═══════════════════════════════════════════════════════════════════
// V2 CHROME (2026-07): the app's bottom tab bar on every legacy page.
// The 446 venue/tour/hub pages keep their HTML untouched (SEO intact)
// but gain the same navigation a visitor learned on the V2 homepage,
// so moving between the new pages and the old ones feels like one
// product. Styles are injected here so zero legacy files change.
// Guarded: pages that already carry the V2 shell (the new home,
// venues, tours, events) render their own tab bar and are skipped.
// ═══════════════════════════════════════════════════════════════════
(function () {
  if (document.querySelector('script[src*="concerto-shell"]')) return; // V2 pages own their chrome
  if (document.querySelector('.tabbar')) return;
  var APP_URL = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414';

  var css = document.createElement('style');
  css.textContent =
    '.tabbar{position:fixed;left:0;right:0;bottom:0;z-index:1000;display:none;' +
    'height:calc(62px + env(safe-area-inset-bottom));padding-bottom:env(safe-area-inset-bottom);' +
    'background:rgba(255,255,255,.94);backdrop-filter:blur(14px);border-top:1px solid rgba(18,30,54,.14)}' +
    
    '.tabbar a{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;' +
    'font-family:"DM Sans",-apple-system,sans-serif;font-size:10px;font-weight:700;color:#8A91A3;text-decoration:none}' +
    '.tabbar a.active{color:#C9A84C}.tabbar a svg{width:21px;height:21px}' +
    '@media(max-width:820px){.tabbar{display:flex}body{padding-bottom:calc(62px + env(safe-area-inset-bottom))}}';
  document.head.appendChild(css);

  var ic = {
    home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>',
    venues: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 21h18M5 21V8l7-5 7 5v13"/><path d="M9 21v-6h6v6"/></svg>',
    tours: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3.5"/></svg>',
    near: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m3 11 18-8-8 18-2.5-7.5L3 11z"/></svg>',
    get: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v12m0 0 4-4m-4 4-4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>'
  };
  var path = location.pathname;
  function act(p) {
    return (p === '/' && (path === '/' || path === '/index.html')) ||
           (p !== '/' && path.indexOf(p) === 0) ? ' class="active"' : '';
  }
  var bar = document.createElement('nav');
  bar.className = 'tabbar';
  bar.setAttribute('aria-label', 'Concerto');
  bar.innerHTML =
    '<a href="/"' + act('/') + '>' + ic.home + 'Home</a>' +
    '<a href="/venues"' + act('/venues') + '>' + ic.venues + 'Venues</a>' +
    '<a href="/tours"' + act('/tours') + '>' + ic.tours + 'Tours</a>' +
    '<a href="/events"' + act('/near-me') + '>' + ic.near + 'Near Me</a>' +
    '<a href="' + APP_URL + '" style="color:#C9A84C">' + ic.get + 'Get App</a>';
  function mount() { document.body.appendChild(bar); }
  if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);
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
  function mount() { document.body.insertBefore(b, document.body.firstChild); }
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
  if (document.querySelector('script[src*="concerto-shell"]')) return;
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
