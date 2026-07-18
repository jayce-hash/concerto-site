/* Concerto analytics loader.
   To activate: create a GA4 property at analytics.google.com,
   then replace the placeholder ID below with your G- ID. One file, whole site. */
(function () {
  var ID = 'G-GBM2Z91QJX';
  if (ID.indexOf('XXXXXXXX') !== -1) return; // not configured yet, do nothing
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('config', ID);
})();
