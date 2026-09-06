(function(){
  const APP_STORE='https://apps.apple.com/us/app/concerto-show-go/id6744903414';
  const groups=[
    ['Explore',[['Venues','/venues'],['Tours','/tours'],['Setlists','/setlists'],['Near Me','/near-me'],['Perks','/perks'],['Concerto+','/premium']]],
    ['Company',[['About','/about'],['Press & Media','/press'],['Investors','/investors'],['Contact','/contact']]],
    ['Work With Us',[['Partners','/partners'],['Creators','/creators'],['Get the App',APP_STORE,'app']]],
    ['Support',[['Help Center','/help'],['FAQ','/faq'],['Account','/account'],['Search','/search']]]
  ];
  const path=(location.pathname.replace(/\.html$/,'').replace(/\/$/,'')||'/');
  function current(href){
    if(!href.startsWith('/')) return '';
    const h=href.replace(/\/$/,'')||'/';
    return path===h?' aria-current="page"':'';
  }
  function links(items){return items.map(([label,href,kind])=>`<a href="${href}"${href.startsWith('http')?' target="_blank" rel="noopener noreferrer"':''}${current(href)}${kind==='app'?' class="concerto-footer-app"':''}>${label}</a>`).join('')}
  const footer=document.createElement('footer');
  footer.className='concerto-footer'; footer.setAttribute('role','contentinfo');
  footer.innerHTML=`<div class="concerto-footer-shell"><div class="concerto-footer-grid"><div class="concerto-footer-brand"><a href="/" aria-label="Concerto home"><img src="/img/lockup.png" alt="Concerto"></a><p class="concerto-footer-tagline">From the Concert to the City®</p><p class="concerto-footer-note">Discover the show. Save it. Know the venue. Plan the night around it.</p><div class="concerto-footer-social"><a href="https://instagram.com/theconcertoapp" target="_blank" rel="noopener noreferrer">Instagram</a><a href="https://www.tiktok.com/@theconcertoapp" target="_blank" rel="noopener noreferrer">TikTok</a><a href="https://www.youtube.com/@theconcertoapp" target="_blank" rel="noopener noreferrer">YouTube</a></div></div>${groups.map(([title,items])=>`<nav aria-label="${title}"><h2>${title}</h2>${links(items)}</nav>`).join('')}</div><div class="concerto-footer-bottom"><span>© 2026 Concerto. Independent from artists, venues, teams and promoters.</span><div class="concerto-footer-bottom-links"><a href="/privacy"${current('/privacy')}>Privacy</a><a href="/terms"${current('/terms')}>Terms</a></div></div></div>`;
  document.querySelectorAll('footer').forEach(el=>el.remove());
  document.body.appendChild(footer);
})();
