// Features page: as each Your Night caption reaches the middle of the screen, the pinned
// phone's screen moves to that part of the page (desktop only; phones get one crop per caption).
(function () {
  var wrap = document.querySelector('.c-yn');
  if (!wrap || !('IntersectionObserver' in window)) return;
  var img = wrap.querySelector('.c-yn-phone img');
  var caps = wrap.querySelectorAll('.c-yn-cap');
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      caps.forEach(function (c) { c.classList.remove('is-on'); });
      en.target.classList.add('is-on');
      img.style.transform = 'translateY(-' + en.target.getAttribute('data-shift') + '%)';
    });
  }, { rootMargin: '-45% 0px -45% 0px' });
  caps.forEach(function (c) { io.observe(c); });
})();
