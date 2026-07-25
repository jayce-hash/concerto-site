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
// APP-FIRST LAYER (2026-07): the site's job is now driving downloads.
// Two additions, both SEO-safe by construction:
//
// 1. NAV SIMPLIFICATION happens here in JS, not in HTML. Crawlers
//    parsing the raw HTML still see the complete historical link set
//    on every one of the ~460 pages (all internal-linking equity
//    preserved); humans with JS get five focused links + a gold
//    "Get the App" pill. This split is deliberate: the SEO nav and
//    the human nav are different products.
//
// 2. APP PILL on venue/tour detail pages: the pages that earn organic
//    search traffic are exactly where a fan is one tap from a better
//    answer in the app. One quiet, dismissible pill; session-scoped
//    dismissal so it never nags.
// ═══════════════════════════════════════════════════════════════════
(function () {
  var APP_URL = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414';

  function simplifyNav() {
    var center = document.querySelector('.nav-center');
    if (!center) return;
    center.innerHTML =
      '<a href="/venues">Venues</a>' +
      '<a href="/tours">Tours</a>' +
      '<a href="/events">Near Me</a>' +
      '<a href="/concertoplus">Concerto+</a>' +
      '<a href="/about">About</a>';
    var right = document.querySelector('.nav-right') || document.querySelector('.nav-cta');
    if (right && !right.querySelector('.nav-app-cta')) {
      var cta = document.createElement('a');
      cta.className = 'nav-app-cta';
      cta.href = APP_URL;
      cta.textContent = 'Get the App';
      cta.style.cssText = 'font-family:var(--body);font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;background:var(--gold,#C9A84C);color:var(--navy,#121E36);padding:0.55rem 1.1rem;border-radius:999px;margin-left:0.9rem;white-space:nowrap;';
      right.insertBefore(cta, right.firstChild);
    }
  }

  function appPill() {
    var path = location.pathname;
    var isDetail = /^\/(venues|tours)\/[^\/]+/.test(path);
    if (!isDetail) return;
    if (sessionStorage.getItem('appPillDismissed')) return;
    var isVenue = path.indexOf('/venues/') === 0;
    var pill = document.createElement('div');
    pill.setAttribute('role', 'complementary');
    pill.style.cssText = 'position:fixed;bottom:1.1rem;left:50%;transform:translateX(-50%);z-index:900;background:var(--navy,#121E36);color:#F8F9F9;border-radius:999px;box-shadow:0 8px 30px rgba(18,30,54,0.35);padding:0.6rem 0.7rem 0.6rem 1.1rem;display:flex;align-items:center;gap:0.8rem;font-family:var(--body,sans-serif);font-size:0.82rem;max-width:92vw;';
    pill.innerHTML =
      '<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' +
        (isVenue ? 'Bag check + night planner for this venue' : 'Countdown + setlists for this tour') +
      '</span>' +
      '<a href="' + APP_URL + '" style="background:#C9A84C;color:#121E36;font-weight:700;border-radius:999px;padding:0.45rem 0.95rem;white-space:nowrap;">Open in App</a>' +
      '<button aria-label="Dismiss" style="background:none;border:none;color:rgba(248,249,249,0.55);font-size:1rem;padding:0.2rem 0.4rem;cursor:pointer;">✕</button>';
    pill.querySelector('button').addEventListener('click', function () {
      sessionStorage.setItem('appPillDismissed', '1');
      pill.remove();
    });
    document.body.appendChild(pill);
  }

  function run() { simplifyNav(); appPill(); }
  if (document.body) run();
  else document.addEventListener('DOMContentLoaded', run);
})();
