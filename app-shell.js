// ─────────────────────────────────────────
// CONCERTO APP SHELL
// Drop-in native-app chrome (frosted appbar + bottom tab bar) for any page.
// Include once per page, after auth.js:  <script src="app-shell.js"></script>
//
// Activates ONLY when:
//   • running inside the native (Capacitor) app, OR
//   • the session was started from the app home (mobile.html marks it, app-only), OR
//   • the URL has ?app=1  (per-page preview — never persisted, never leaks)
// On normal desktop/mobile web it does nothing. ?app=0 clears a preview/session flag.
//
// Header matches mobile.html: logo left, Sign In / My Account pill right.
// Bottom tab bar: Home · Venues · Tours · Near Me · Account, active tab auto-detected.
// ─────────────────────────────────────────
(function () {
  var SB_URL = 'https://qgvukssbtfkbvahaiejm.supabase.co';
  var SB_KEY = 'sb_publishable_xuc86SqqrndgPMj5ToBuvw_EHDkRwYY';
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

  if (!inNativeApp && !sessionApp && !preview) return; // normal web — leave the page alone
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
    '.app-appbar-signin{',
      'font-size:0.62rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;',
      'color:rgba(18,30,54,0.52);padding:8px 14px;text-decoration:none;',
      'border:1px solid rgba(18,30,54,0.14);border-radius:99px;white-space:nowrap;',
    '}',

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
    if (document.querySelector('.tabbar') || document.getElementById('appShellStyle')) return;

    document.body.classList.add('app-shell-on');

    var style = document.createElement('style');
    style.id = 'appShellStyle';
    style.textContent = CSS;
    document.head.appendChild(style);

    var bar = document.createElement('header');
    bar.className = 'app-appbar';
    bar.id = 'appShellBar';
    bar.innerHTML =
      '<a href="mobile.html" aria-label="Concerto Home"><img src="logo.png" alt="Concerto" class="app-appbar-logo"></a>' +
      '<a id="appShellSignin" href="login.html" class="app-appbar-signin">Sign In</a>';
    document.body.insertBefore(bar, document.body.firstChild);

    var key = activeKey();
    var q = usingPreview ? '?app=1' : '';
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

    var onScroll = function () { bar.classList.toggle('scrolled', window.scrollY > 4); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    // Swap "Sign In" → "My Account" when a session exists (matches mobile.html).
    try {
      var k = 'sb-' + SB_URL.split('//')[1].split('.')[0] + '-auth-token';
      var token = (JSON.parse(localStorage.getItem(k) || '{}') || {}).access_token || '';
      if (token) {
        fetch(SB_URL + '/auth/v1/user', { headers: { apikey: SB_KEY, Authorization: 'Bearer ' + token } })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (user) {
            if (user && user.id) {
              var el = document.getElementById('appShellSignin');
              if (el) { el.textContent = 'My Account'; el.href = 'account.html' + q; }
            }
          })
          .catch(function () {});
      }
    } catch (e) {}
  }

  if (document.body) build();
  else document.addEventListener('DOMContentLoaded', build);
})();
