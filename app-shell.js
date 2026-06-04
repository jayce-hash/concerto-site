// ─────────────────────────────────────────
// CONCERTO APP SHELL
// Drop-in native-app chrome (frosted appbar + bottom tab bar) for any page.
// Include once per page, after auth.js:  <script src="app-shell.js"></script>
//
// Activates ONLY when:
//   • running inside the native (Capacitor) app, OR
//   • the URL has ?app=1  (persists for browser preview; ?app=0 turns it off)
// On normal desktop/mobile web it does nothing, so the existing site is untouched.
//
// When active it: hides the marketing nav, shows a frosted top appbar (logo),
// and a fixed bottom tab bar (Home · Venues · Tours · Near Me · Account) with
// the active tab auto-detected from the URL. Single source of truth — one line
// per page, no per-page config, no duplicate "-mobile" files.
// ─────────────────────────────────────────
(function () {
  // ── Activation ───────────────────────────
  var params = new URLSearchParams(location.search);
  if (params.get('app') === '1') localStorage.setItem('concerto-app-mode', '1');
  if (params.get('app') === '0') localStorage.removeItem('concerto-app-mode');

  var inNativeApp = !!(window.Capacitor &&
    (typeof window.Capacitor.isNativePlatform === 'function'
      ? window.Capacitor.isNativePlatform() : true));
  var forced = localStorage.getItem('concerto-app-mode') === '1';
  if (!inNativeApp && !forced) return; // normal web — leave the page alone

  var CSS = [
    'body.app-shell-on{',
      '--nav-h:0px !important;',
      'padding-top:calc(env(safe-area-inset-top) + 56px) !important;',
      'padding-bottom:calc(env(safe-area-inset-bottom) + 64px) !important;',
    '}',
    'body.app-shell-on .site-nav,',
    'body.app-shell-on .nav-mobile-menu{display:none !important;}',

    '.app-appbar{',
      'position:fixed;top:0;left:0;right:0;z-index:1000;box-sizing:border-box;',
      'display:flex;align-items:center;justify-content:center;',
      'padding:calc(env(safe-area-inset-top) + 10px) 20px 12px;',
      'background:rgba(248,249,249,0.82);',
      'backdrop-filter:saturate(160%) blur(16px);',
      '-webkit-backdrop-filter:saturate(160%) blur(16px);',
      'border-bottom:1px solid transparent;',
      'transition:border-color .2s, background .2s;',
    '}',
    '.app-appbar.scrolled{border-bottom-color:rgba(18,30,54,0.08);background:rgba(248,249,249,0.93);}',
    '.app-appbar img{height:34px;width:auto;display:block;}',

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

  // SVGs lifted from mobile.html so the tab bar matches exactly.
  var TABS = [
    ['home',    'mobile.html',  'Home',    '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h14V10"/>'],
    ['venues',  'venues.html',  'Venues',  '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>'],
    ['tours',   'tours.html',   'Tours',   '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>'],
    ['events',  'events.html',  'Near Me', '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>'],
    ['account', 'account.html', 'Account', '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-7 8-7s8 3 8 7"/>']
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
    // Skip pages that already ship their own native shell (e.g. mobile.html).
    if (document.querySelector('.tabbar') || document.getElementById('appShellStyle')) return;

    document.body.classList.add('app-shell-on');

    var style = document.createElement('style');
    style.id = 'appShellStyle';
    style.textContent = CSS;
    document.head.appendChild(style);

    var bar = document.createElement('header');
    bar.className = 'app-appbar';
    bar.id = 'appShellBar';
    bar.innerHTML = '<a href="mobile.html" aria-label="Concerto Home"><img src="logo.png" alt="Concerto"></a>';
    document.body.insertBefore(bar, document.body.firstChild);

    var key = activeKey();
    var tabsHtml = TABS.map(function (t) {
      var cls = 'app-tab' + (t[0] === key ? ' active' : '');
      var cur = t[0] === key ? ' aria-current="page"' : '';
      return '<a href="' + t[1] + '" class="' + cls + '" data-tab="' + t[0] + '"' + cur + '>'
        + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        + t[3] + '</svg><span class="app-tab-label">' + t[2] + '</span></a>';
    }).join('');

    var nav = document.createElement('nav');
    nav.className = 'app-tabbar';
    nav.setAttribute('aria-label', 'Main');
    nav.innerHTML = tabsHtml;
    document.body.appendChild(nav);

    var onScroll = function () { bar.classList.toggle('scrolled', window.scrollY > 4); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  if (document.body) build();
  else document.addEventListener('DOMContentLoaded', build);
})();
