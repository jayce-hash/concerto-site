(function(){
  var APP='https://apps.apple.com/us/app/concerto-show-go/id6744903414';
  function norm(x){return (x||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'')}
  function initials(s){return (s||'').split(/\s+/).filter(Boolean).slice(0,2).map(function(x){return x[0]}).join('').toUpperCase()||'C'}
  function tmUrl(resource,params){var p=new URLSearchParams(params||{});p.set('resource',resource);return '/.netlify/functions/tm?'+p.toString()}
  function safeJSON(r){return r&&r.ok?r.json():Promise.reject(new Error('request failed'))}

  function mountHeader(){
    document.querySelectorAll('body > nav.nav,body > nav.topbar,body > header.site-header').forEach(function(n){n.remove()});
    var path=(location.pathname.replace(/\.html$/,'').replace(/\/$/,'')||'/');
    function activeFor(href){
      if(path===href)return true;
      if(href==='/venues'&&path.indexOf('/venue/')===0)return true;
      if(href==='/tours'&&path.indexOf('/tour/')===0)return true;
      if(href==='/setlists'&&path.indexOf('/setlist/')===0)return true;
      if(href==='/partners'&&path.indexOf('/partners/')===0)return true;
      return false;
    }
    function a(label,href){return '<a '+(activeFor(href)?'class="active" ':'')+'href="'+href+'">'+label+'</a>'}
    var h=document.createElement('header');h.className='site-header';
    h.innerHTML='<div class="site-shell wide header-inner"><a class="site-logo" href="/" aria-label="Concerto home"><img src="/img/lockup.png" alt="Concerto"></a><nav class="site-nav" aria-label="Main">'+a('Venues','/venues')+a('Tours','/tours')+a('Setlists','/setlists')+a('Near Me','/near-me')+a('Concerto+','/premium')+a('Perks','/perks')+a('Partners','/partners')+'</nav><div class="header-actions"><a class="header-text-link" href="/search">Search</a><a class="header-cta" href="'+APP+'" target="_blank" rel="noopener">Get the App</a><button class="menu-btn" aria-label="Open menu" aria-expanded="false">☰</button></div></div><nav class="mobile-nav site-shell" aria-label="Mobile">'+a('Venues','/venues')+a('Tours','/tours')+a('Setlists','/setlists')+a('Near Me','/near-me')+a('Concerto+','/premium')+a('Perks','/perks')+a('Partners','/partners')+'<a href="/about">About</a><a href="/help">Help</a><a class="header-cta" href="'+APP+'">Get the App</a></nav>';
    document.body.insertBefore(h,document.body.firstChild);
    var b=h.querySelector('.menu-btn'),m=h.querySelector('.mobile-nav');
    if(b)b.onclick=function(){var open=m.classList.toggle('open');b.textContent=open?'×':'☰';b.setAttribute('aria-expanded',open?'true':'false')};
  }

  function mountFooter(){
    document.querySelectorAll('body > footer,footer.concerto-footer').forEach(function(n){n.remove()});
    var f=document.createElement('footer');f.className='site-footer';
    f.innerHTML='<div class="site-shell footer-top"><div class="footer-brand"><img src="/img/lockup.png" alt="Concerto"><p class="footer-kicker">From the Concert to the City®</p><h2>One show. One connected night.</h2><p>Concerto connects the concert, venue, and city around it with trusted information and a plan that travels with you.</p><a class="footer-app" href="'+APP+'" target="_blank" rel="noopener">Get Concerto for iPhone →</a></div><div class="footer-nav"><div class="footer-col"><h3>Discover</h3><a href="/venues">Venues</a><a href="/tours">Tours</a><a href="/setlists">Setlists</a><a href="/near-me">Near Me</a><a href="/perks">Perks</a></div><div class="footer-col"><h3>Product</h3><a href="/premium">Concerto+</a><a href="/bagcheck">AI Bag Check</a><a href="'+APP+'">Get the App</a></div><div class="footer-col"><h3>Company</h3><a href="/about">About</a><a href="/press">Press & Media</a><a href="/investors">Investors</a><a href="/contact">Contact</a></div><div class="footer-col"><h3>Work With Us</h3><a href="/partners">Partners</a><a href="/creators">Creators</a><a href="/help">Help Center</a><a href="/faq">FAQ</a></div></div></div><div class="site-shell footer-bottom"><span>© 2026 Concerto LLC</span><div class="footer-bottom-links"><a href="https://instagram.com/theconcertoapp" target="_blank" rel="noopener">Instagram</a><a href="https://www.tiktok.com/@theconcertoapp" target="_blank" rel="noopener">TikTok</a><a href="https://www.youtube.com/@theconcertoapp" target="_blank" rel="noopener">YouTube</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a></div></div>';
    document.body.appendChild(f);
  }

  function bestImage(images){if(!images||!images.length)return null;var wide=images.filter(function(i){return i.ratio==='16_9'});var pool=(wide.length?wide:images).slice();pool.sort(function(a,b){return (b.width||0)-(a.width||0)});return pool[0]&&pool[0].url}
  function fallback(el,label){
    var staticSrc=el.getAttribute('data-fallback-src');
    if(staticSrc&&!el.dataset.staticTried){el.dataset.staticTried='1';if(setImg(el,staticSrc,label))return}
    el.classList.remove('is-loading');el.classList.add('image-fallback');
    if(!el.querySelector('.fallback-mark')){var x=document.createElement('span');x.className='fallback-mark';x.textContent=initials(label);el.insertBefore(x,el.firstChild)}
  }
  function setImg(el,src,alt){if(!src)return false;var im=new Image();im.alt=alt||'';im.loading='lazy';im.decoding='async';im.onload=function(){el.querySelectorAll('img.dynamic-photo').forEach(function(x){x.remove()});im.className='dynamic-photo';el.insertBefore(im,el.firstChild);el.classList.add('has-photo');el.classList.remove('is-loading','image-fallback')};im.onerror=function(){fallback(el,alt)};im.src=src;return true}
  function memoFetch(key,fn){try{var c=sessionStorage.getItem(key);if(c)return Promise.resolve(JSON.parse(c))}catch(e){}return fn().then(function(d){try{sessionStorage.setItem(key,JSON.stringify(d))}catch(e){}return d})}

  function loadVenue(el){
    var name=el.dataset.vname||'',city=el.dataset.vcity||'',lat=el.dataset.vlat||'',lng=el.dataset.vlng||'';
    if(!name)return;el.classList.add('is-loading');
    var key='concerto:vphoto:'+norm(name)+'|'+norm(city);
    memoFetch(key,function(){var p=new URLSearchParams({name:name,city:city,lat:lat,lng:lng});return fetch('/.netlify/functions/venue-photo?'+p.toString()).then(safeJSON)}).then(function(d){if(d&&d.src){setImg(el,d.src,name);return}else throw 0}).catch(function(){
      return fetch(tmUrl('venues',{keyword:name,city:city,size:'5'})).then(safeJSON).then(function(d){var vs=d&&d._embedded&&d._embedded.venues||[];var target=norm(name);var v=vs.find(function(x){return x.name&&norm(x.name)===target})||vs[0];if(!v||!v.id)throw 0;return fetch(tmUrl('events',{venueId:v.id,classificationName:'Music',size:'5',sort:'date,asc'})).then(safeJSON)}).then(function(d){var es=d&&d._embedded&&d._embedded.events||[];var src=null;for(var i=0;i<es.length&&!src;i++)src=bestImage(es[i].images);if(src)setImg(el,src,name);else fallback(el,name)})
    }).catch(function(){fallback(el,name)})
  }

  function loadArtist(el){
    var artist=el.dataset.artist;if(!artist)return;el.classList.add('is-loading');var key='concerto:artist:'+norm(artist);
    memoFetch(key,function(){return fetch(tmUrl('attractions',{keyword:artist,classificationName:'Music',size:'10'})).then(safeJSON)}).then(function(d){var list=d&&d._embedded&&d._embedded.attractions||[];var target=norm(artist);var a=list.find(function(x){return x.name&&norm(x.name)===target})||list.find(function(x){return x.name&&norm(x.name).indexOf(target)!==-1})||list[0];var src=a&&bestImage(a.images);if(src){setImg(el,src,artist);return}else throw 0}).catch(function(){
      fetch(tmUrl('events',{keyword:artist,classificationName:'Music',size:'5',sort:'date,asc'})).then(safeJSON).then(function(d){var es=d&&d._embedded&&d._embedded.events||[];var src=null;for(var i=0;i<es.length&&!src;i++)src=bestImage(es[i].images);if(src)setImg(el,src,artist);else fallback(el,artist)}).catch(function(){fallback(el,artist)})
    })
  }

  function mountPhoneStatus(){
    document.querySelectorAll('.iphone-frame').forEach(function(frame){if(frame.querySelector('.iphone-status'))return;var s=document.createElement('div');s.className='iphone-status';s.innerHTML='<span class="iphone-time">12:00</span><span class="iphone-island"></span><span class="iphone-icons"><svg class="status-signal" viewBox="0 0 18 12" aria-hidden="true"><rect x="0" y="8" width="3" height="4" rx="1"/><rect x="5" y="6" width="3" height="6" rx="1"/><rect x="10" y="3" width="3" height="9" rx="1"/><rect x="15" y="0" width="3" height="12" rx="1"/></svg><svg class="status-wifi" viewBox="0 0 18 13" aria-hidden="true"><path d="M1 4.5C5.4.5 12.6.5 17 4.5"/><path d="M4 7.5c2.8-2.4 7.2-2.4 10 0"/><path d="M7.1 10.2c1.1-.9 2.7-.9 3.8 0"/><circle cx="9" cy="12" r="1" fill="currentColor" stroke="none"/></svg><span class="status-battery"><i></i></span></span>';frame.appendChild(s)})
  }

  function mountSearch(){
    var input=document.querySelector('[data-site-search]'),results=document.querySelector('[data-site-search-results]');if(!input||!results)return;
    var index=[];
    Promise.all([fetch('/search-index.json').then(safeJSON),fetch('/setlists.json').then(safeJSON).catch(function(){return []})]).then(function(all){
      var d=all[0]||{}, rawSetlists=all[1]||{}, setlists=Array.isArray(rawSetlists)?rawSetlists:Object.keys(rawSetlists).map(function(slug){var x=rawSetlists[slug]||{};var y={};Object.keys(x).forEach(function(k){y[k]=x[k]});y.slug=slug;return y});
      if(Array.isArray(d)) index=d;
      else {
        index=(d.venues||[]).map(function(v){return {title:v.name,subtitle:v.type||'',city:v.city||'',type:'Venue',url:'/venue/'+v.slug}})
          .concat((d.tours||[]).map(function(t){return {title:t.artist||t.name,subtitle:t.name||'',type:'Tour',url:'/tour/'+t.slug}}));
      }
      setlists.filter(function(s){return Array.isArray(s.songs)&&s.songs.length}).forEach(function(s){
        var slug=s.slug||s.tourSlug||s.id;if(!slug)return;
        index.push({title:s.artist||s.name||s.tour||'Setlist',subtitle:(s.tour||s.tourName||s.name||'')+' · '+s.songs.length+' songs',type:'Setlist',url:'/setlist/'+slug});
      });
    }).catch(function(){});
    function render(){var q=norm(input.value);results.innerHTML='';if(!q){results.innerHTML='<div class="search-empty">Try an artist, tour, venue, city, or setlist.</div>';return}var hits=index.filter(function(x){return norm([x.title,x.subtitle,x.type,x.city].filter(Boolean).join(' ')).indexOf(q)!==-1}).slice(0,24);if(!hits.length){results.innerHTML='<div class="search-empty">No exact match yet. Try a broader artist, venue, or city.</div>';return}hits.forEach(function(x){var a=document.createElement('a');a.className='search-result';a.href=x.url||x.href||'#';a.innerHTML='<span class="search-result-type">'+(x.type||'Concerto')+'</span><strong>'+String(x.title||'').replace(/</g,'&lt;')+'</strong><span>'+String(x.subtitle||x.city||'').replace(/</g,'&lt;')+'</span>';results.appendChild(a)})}
    input.addEventListener('input',render);render();
  }

  document.addEventListener('DOMContentLoaded',function(){
    document.body.classList.add('public-site');mountHeader();mountFooter();mountPhoneStatus();mountSearch();
    document.querySelectorAll('[data-vphoto]').forEach(loadVenue);document.querySelectorAll('[data-artist]').forEach(loadArtist);
    document.querySelectorAll('[data-filter-target]').forEach(function(input){var sel=input.getAttribute('data-filter-target');var items=[].slice.call(document.querySelectorAll(sel));input.addEventListener('input',function(){var q=norm(input.value);items.forEach(function(item){item.style.display=!q||norm(item.textContent).indexOf(q)!==-1?'':'none'})})});
  });
})();
