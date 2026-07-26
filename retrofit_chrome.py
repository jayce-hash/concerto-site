#!/usr/bin/env python3
"""
Retrofit the V2 chrome onto the legacy content pages.

These pages (About, FAQ, Premium, Privacy, Terms) already have the
editorial design we want -- correct fonts, spacing and rhythm. Only
their NAV and FOOTER are from the old site. This swaps just those two
regions for markup matching the app-on-web chrome, and leaves every
word of the page body untouched.

Run from the site root:  python3 retrofit_chrome.py
Idempotent: re-running is safe.
"""
import re, pathlib, shutil

PAGES = ['about.html', 'faq.html', 'premium.html', 'privacy.html', 'terms.html']
APP_URL = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414'

NAV = '''<nav class="v2nav" role="navigation" aria-label="Main navigation">
    <a class="v2nav-brand" href="/" aria-label="Concerto home">
      <img src="/img/lockup.png" alt="Concerto — From the Concert to the City" width="168" height="36" />
    </a>
    <div class="v2nav-links">
      <a href="/">Home</a>
      <a href="/venues">Venues</a>
      <a href="/tours">Tours</a>
      <a href="/near-me">Near Me</a>
    </div>
    <div class="v2nav-right">
      <a class="v2nav-icon" href="/search" aria-label="Search">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      </a>
      <a class="v2nav-icon" href="/account" aria-label="Account">
        <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="9" r="3.2"/><circle cx="12" cy="12" r="9"/><path d="M5.5 19a7 7 0 0 1 13 0"/></svg>
      </a>
      <a class="v2nav-cta" href="''' + APP_URL + '''" target="_blank" rel="noopener noreferrer">Get the App</a>
    </div>
  </nav>'''

FOOTER = '''<footer class="v2foot" role="contentinfo">
    <div class="v2foot-inner">
      <span class="v2foot-copy">&copy; 2026 Concerto &middot; From the Concert to the City&reg;</span>
      <nav class="v2foot-links" aria-label="Footer">
        <a href="/about">About</a><span>&middot;</span>
        <a href="/premium">Premium</a><span>&middot;</span>
        <a href="/faq">FAQ</a><span>&middot;</span>
        <a href="/privacy">Privacy</a><span>&middot;</span>
        <a href="/terms">Terms</a><span>&middot;</span>
        <a href="/account">Account</a>
      </nav>
      <a class="v2foot-cta" href="''' + APP_URL + '''" target="_blank" rel="noopener noreferrer">Get the App</a>
    </div>
  </footer>'''

CHROME_VERSION = 'v2.1'

CSS = '''/* concerto-chrome v2.1 */
  /* ── Uniform editorial system ───────────────────────────────────
     About, FAQ, Premium, Privacy and Terms had drifted apart: About
     and FAQ used a 4.8rem title and 1.05rem prose, Privacy and Terms
     a 4rem title and 1rem prose, and Premium its own marketing scale.
     Layout may differ by page purpose -- a pricing page is not a
     legal page -- but type, scale and colour must not. This locks
     every one of them to the same system, and forces light mode:
     a guest arriving from search is not a user with a saved
     preference. */
  :root{
    --v2-display:'Playfair Display',Georgia,serif;
    --v2-body:'DM Sans',-apple-system,BlinkMacSystemFont,sans-serif;
    --v2-text:#121E36; --v2-dim:#5A6478; --v2-faint:#8A91A3;
    --v2-surface:#FFFFFF;
  }
  html,body{ background:var(--v2-bg) !important; color:var(--v2-text) !important;
             color-scheme: light !important; }

  .editorial-container,.hero,.pricing-section,.features-grid{ }

  .eyebrow{
    font-family:var(--v2-body) !important; font-size:.62rem !important;
    font-weight:700 !important; letter-spacing:.28em !important;
    text-transform:uppercase !important; color:var(--v2-gold) !important;
    margin-bottom:1.4rem !important;
  }
  .page-title,.hero-title{
    font-family:var(--v2-display) !important;
    font-size:clamp(2.4rem,5vw,4rem) !important;
    font-weight:700 !important; letter-spacing:-.03em !important;
    line-height:1.05 !important; color:var(--v2-text) !important;
  }
  .page-sub,.hero-desc,.pricing-copy{
    font-family:var(--v2-body) !important; font-size:1.05rem !important;
    font-weight:300 !important; line-height:1.8 !important;
    color:var(--v2-dim) !important;
  }
  .prose p,.prose li{
    font-family:var(--v2-body) !important; font-size:1rem !important;
    font-weight:300 !important; line-height:1.85 !important;
    color:var(--v2-dim) !important;
  }
  .prose h2,.pricing-section h2,.features-grid h2{
    font-family:var(--v2-display) !important; font-size:1.5rem !important;
    font-weight:700 !important; letter-spacing:-.015em !important;
    color:var(--v2-text) !important;
  }
  .prose h3,.feat-label,.feat-card h3{
    font-family:var(--v2-display) !important; color:var(--v2-text) !important;
  }
  .feat-label,.hero-price,.price-pill{
    font-family:var(--v2-body) !important;
  }
  .prose strong{ color:var(--v2-text) !important; font-weight:600 !important; }
  .prose a,.editorial-container a:not(.btn){ color:var(--v2-gold) !important; }

  /* One CTA colour sitewide, matching the app-on-web chrome. */
  .btn-gold,.feat-cta,.btn.btn-gold{
    background:var(--v2-gold) !important; color:var(--v2-navy) !important;
    border-color:var(--v2-gold) !important;
    font-family:var(--v2-body) !important; font-weight:700 !important;
  }
  .btn-dark,.btn.btn-dark{
    background:var(--v2-navy) !important; color:#F8F9F9 !important;
    font-family:var(--v2-body) !important; font-weight:700 !important;
  }
  .feat-card,.pricing-card{
    background:var(--v2-surface) !important;
    border-color:var(--v2-line) !important;
  }

  /* ── V2 chrome (matches the app-on-web nav + footer) ────────── */
  :root { --v2-navy:#121E36; --v2-gold:#C9A84C; --v2-bg:#F8F9F9;
          --v2-ink:#121E36; --v2-muted:#5A6478; --v2-line:rgba(18,30,54,.14); }
  .v2nav{position:sticky;top:0;z-index:1000;display:flex;align-items:center;
    justify-content:space-between;gap:1.2rem;padding:12px 20px;
    background:var(--v2-bg);}
  .v2nav.is-scrolled{border-bottom:1px solid var(--v2-line);}
  .v2nav-brand img{display:block;width:168px;height:36px;object-fit:contain;}
  .v2nav-links{position:absolute;left:50%;transform:translateX(-50%);
    display:flex;align-items:center;gap:1.6rem;}
  .v2nav-links a{font-family:var(--body,'DM Sans',sans-serif);font-size:11.5px;
    font-weight:600;letter-spacing:.09em;text-transform:uppercase;
    color:var(--v2-muted);text-decoration:none;}
  .v2nav-links a:hover,.v2nav-links a[aria-current="page"]{color:var(--v2-gold);}
  .v2nav-right{display:flex;align-items:center;gap:8px;}
  .v2nav-icon{width:34px;height:34px;border-radius:17px;display:flex;
    align-items:center;justify-content:center;color:var(--v2-ink);}
  .v2nav-cta{background:var(--v2-gold);color:var(--v2-navy);
    font-family:var(--body,'DM Sans',sans-serif);font-size:12.5px;font-weight:700;
    border-radius:999px;padding:8px 15px;text-decoration:none;white-space:nowrap;}
  @media(max-width:820px){ .v2nav-links{display:none;} }

  .v2foot{border-top:1px solid var(--v2-line);margin-top:64px;
    padding:24px 20px;background:var(--v2-bg);}
  .v2foot-inner{max-width:1280px;margin:0 auto;display:flex;flex-wrap:wrap;
    align-items:center;justify-content:space-between;gap:12px;}
  .v2foot-copy{font-family:var(--body,'DM Sans',sans-serif);font-size:12px;color:#8A91A3;}
  .v2foot-links{display:flex;flex-wrap:wrap;align-items:center;gap:8px;}
  .v2foot-links a{font-family:var(--body,'DM Sans',sans-serif);font-size:12.5px;
    font-weight:600;color:var(--v2-muted);text-decoration:none;}
  .v2foot-links a:hover{color:var(--v2-gold);}
  .v2foot-links span{color:#8A91A3;font-size:12px;}
  .v2foot-cta{background:var(--v2-gold);color:var(--v2-navy);
    font-family:var(--body,'DM Sans',sans-serif);font-size:12.5px;font-weight:700;
    border-radius:999px;padding:9px 16px;text-decoration:none;}
'''

JS = '''<script>
  (function(){
    var n=document.querySelector('.v2nav'); if(!n) return;
    var on=function(){ n.classList.toggle('is-scrolled', window.scrollY>8); };
    window.addEventListener('scroll',on,{passive:true}); on();
    var here=location.pathname.replace(/\\.html$/,'').replace(/\\/$/,'')||'/';
    document.querySelectorAll('.v2nav-links a').forEach(function(a){
      var href=a.getAttribute('href').replace(/\\/$/,'')||'/';
      if(href===here) a.setAttribute('aria-current','page');
    });
  })();
  </script>'''

root = pathlib.Path('.')

# concertoplus.html becomes premium.html (Concerto+ is a feature; the
# tier is Premium). Copy rather than move so nothing breaks mid-run.
if (root / 'concertoplus.html').exists() and not (root / 'premium.html').exists():
    shutil.copy('concertoplus.html', 'premium.html')
    print('premium.html created from concertoplus.html')

done = 0
for name in PAGES:
    p = root / name
    if not p.exists():
        print('skip (missing):', name)
        continue
    s = p.read_text(encoding='utf-8')

    already = 'v2nav' in s
    current = ('concerto-chrome ' + CHROME_VERSION) in s

    if already and current:
        print('up to date:', name)
        continue

    if already:
        # Previously retrofitted with an older chrome. Strip the old
        # blocks and re-apply, so re-running UPGRADES a page instead of
        # skipping it -- otherwise pages deployed with an earlier
        # version would never receive later fixes.
        s = re.sub(r'<nav[^>]*class="v2nav".*?</nav>', '', s, count=1, flags=re.S)
        s = re.sub(r'<footer[^>]*class="v2foot".*?</footer>', '', s, count=1, flags=re.S)
        # Strip any previously injected chrome CSS. v2.0 opened with
        # "/* ── V2 chrome"; v2.1+ carries an explicit version marker.
        # Matching both stops the block being appended twice on upgrade.
        s = re.sub(r'\n\s*/\* concerto-chrome.*?(?=</style>)', '', s, count=1, flags=re.S)
        s = re.sub(r'\n\s*/\* ── V2 chrome.*?(?=</style>)', '', s, count=1, flags=re.S)
        s = re.sub(r'<script>\s*\(function\(\)\{\s*var n=document\.querySelector\(\'\.v2nav\'\).*?</script>', '', s, count=1, flags=re.S)
        # re-insert placeholders the swaps below look for
        s = s.replace('<body', '<body', 1)
        # nav/footer were removed, so put minimal anchors back
        s = re.sub(r'(<body[^>]*>)', r'\1\n  <nav class="site-nav"></nav>', s, count=1)
        s = s.replace('</body>', '  <footer></footer>\n</body>', 1)

    # swap nav
    s = re.sub(r'<nav[^>]*class="site-nav".*?</nav>', NAV, s, count=1, flags=re.S)
    # swap footer
    s = re.sub(r'<footer.*?</footer>', FOOTER, s, count=1, flags=re.S)
    # inject chrome CSS at the end of the first <style> block
    if '<style>' in s:
        i = s.find('</style>')
        s = s[:i] + CSS + s[i:]
    else:
        s = s.replace('</head>', '  <style>' + CSS + '</style>\n</head>', 1)
    # smart app banner if absent
    if 'apple-itunes-app' not in s:
        s = s.replace('<meta name="viewport"',
                      '<meta name="apple-itunes-app" content="app-id=6744903414">\n  <meta name="viewport"', 1)
    # nav behaviour
    s = s.replace('</body>', '  ' + JS + '\n</body>', 1)

    p.write_text(s, encoding='utf-8')
    done += 1
    print('retrofitted:', name)

print(f'\ndone: {done} pages now carry the V2 nav + footer, bodies untouched.')
