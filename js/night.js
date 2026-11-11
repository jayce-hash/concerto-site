// A night shared from the Concerto app: the plan is in the link's #fragment (percent-encoded
// JSON, base64url), so it never reaches a server. Fill the page in, or say the link is incomplete.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  function decode(h) {
    try {
      var b = h.replace(/-/g, '+').replace(/_/g, '/');
      while (b.length % 4) b += '=';
      return JSON.parse(decodeURIComponent(atob(b)));
    } catch (e) { return null; }
  }
  function text(el, t) { el.textContent = t || ''; }
  var data = decode((location.hash || '').slice(1));
  if (!data || !data.a || !Array.isArray(data.s)) { $('n-empty').hidden = false; return; }
  var when = '';
  try {
    when = new Date(data.d).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: data.z || undefined });
  } catch (e) {}
  text($('n-eyebrow'), 'A night planned with Concerto');
  text($('n-artist'), String(data.a).slice(0, 80));
  text($('n-when'), [when, String(data.v || '').slice(0, 80)].filter(Boolean).join(' · '));
  document.title = data.a + ' · A night planned with Concerto';
  // Going to the same show: the link carries the show's id, so one tap saves it in the app.
  var id = String(data.i || '');
  if (/^[A-Za-z0-9_-]{4,40}$/.test(id) && $('n-save')) {
    $('n-save').setAttribute('data-app-link', 'concerto://save/' + encodeURIComponent(id));
    $('n-going').hidden = false;
  }
  var list = $('n-stops');
  data.s.slice(0, 14).forEach(function (s) {
    var li = document.createElement('li');
    var t = document.createElement('span'); t.className = 'c-night-time'; text(t, String(s[0] || '').slice(0, 14));
    var b = document.createElement('div');
    var h = document.createElement('h2'); text(h, String(s[1] || '').slice(0, 90));
    b.appendChild(h);
    if (s[2]) { var p = document.createElement('p'); text(p, String(s[2]).slice(0, 220)); b.appendChild(p); }
    li.appendChild(t); li.appendChild(b); list.appendChild(li);
  });
})();
