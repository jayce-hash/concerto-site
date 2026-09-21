/* Concerto Partner Console. Magic-link sign in, then one of two views:
   venue (edit the eight sections, stage times, report) or partner (Perks, report).
   Writes go straight to Supabase under row level security; the app and website read
   the result through /.netlify/functions/partner-content. */
(function () {
  'use strict';
  var SUPABASE_URL = 'https://qgvukssbtfkbvahaiejm.supabase.co';
  var SUPABASE_ANON = 'sb_publishable_xuc86SqqrndgPMj5ToBuvw_EHDkRwYY';
  var sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON);
  var FN = '/.netlify/functions';
  var SECTIONS = [['bagPolicy', 'Bag Policy'], ['parking', 'Parking'], ['rideshare', 'Rideshare'], ['concessions', 'Concessions'], ['accessibility', 'Accessibility'], ['reEntry', 'Re-entry'], ['ticketPickup', 'Ticket Pickup'], ['gates', 'Entrances & Doors']];
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };
  var venues = [], venueInfo = {}, session = null, org = null;

  function show(view) { $$('[data-view]').forEach(function (v) { v.hidden = v.getAttribute('data-view') !== view; }); $('[data-signout]').hidden = view === 'signin'; }
  function status(msg, ok) { var s = $('[data-status]'); if (s) { s.textContent = msg; s.style.color = ok === false ? '#B3261E' : ''; } }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function loadCatalog() {
    return Promise.all([fetch('/data/venues.json').then(function (r) { return r.json(); }), fetch('/data/venue_info.json').then(function (r) { return r.json(); })]).then(function (d) {
      venues = d[0]; venueInfo = d[1];
      var opts = venues.slice().sort(function (a, b) { return a.name.localeCompare(b.name); }).map(function (v) { return '<option value="' + esc(v.id) + '">' + esc(v.name) + ' · ' + esc(v.city) + '</option>'; }).join('');
      $$('select[name=venueSlug], select[name=venue_slugs]').forEach(function (s) { s.insertAdjacentHTML('beforeend', opts); });
    });
  }

  /* ---------- sign in ---------- */
  function wireSignin() {
    $('[data-form=claim]').addEventListener('submit', function (e) {
      e.preventDefault(); var f = e.target; status('Sending your sign-in link…');
      fetch(FN + '/partner-claim', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'venue', venueSlug: f.venueSlug.value, email: f.email.value }) })
        .then(function (r) { return r.json(); }).then(function (d) { status(d.error || 'Check your email for the link. Open it on this device.', !d.error); });
    });
    $('[data-form=partner]').addEventListener('submit', function (e) {
      e.preventDefault(); var f = e.target; status('Sending your sign-in link…');
      fetch(FN + '/partner-claim', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: f.kind.value, name: f.name.value, email: f.email.value }) })
        .then(function (r) { return r.json(); }).then(function (d) { status(d.error || 'Check your email for the link. Open it on this device.', !d.error); });
    });
    $('[data-signout]').addEventListener('click', function () { sb.auth.signOut().then(function () { location.reload(); }); });
  }

  /* ---------- after sign in ---------- */
  function resolveOrg() {
    return fetch(FN + '/partner-claim?approve=1', { headers: { Authorization: 'Bearer ' + session.access_token } }).then(function (r) { return r.json(); }).catch(function () { return {}; })
      .then(function () { return sb.from('partner_members').select('org_id, partner_orgs(*)').eq('user_id', session.user.id); })
      .then(function (r) { var rows = r.data || []; return rows.length ? rows[0].partner_orgs : null; });
  }

  /* ---------- venue view ---------- */
  function renderVenue() {
    $('[data-venue-name]').textContent = (venues.find(function (v) { return v.id === org.venue_slug; }) || {}).name || org.venue_slug;
    show('venue'); wireTabs('venue');
    Promise.all([sb.from('venue_overrides').select('*').eq('venue_slug', org.venue_slug), sb.from('stage_times').select('*').eq('venue_slug', org.venue_slug).order('event_date')]).then(function (r) {
      renderSections(r[0].data || []); renderStage(r[1].data || []);
    });
    renderReport($('[data-view=venue] [data-pane=report]'), { venue: org.venue_slug });
    $('[data-form=stage]').addEventListener('submit', function (e) {
      e.preventDefault(); var f = e.target;
      var row = { venue_slug: org.venue_slug, event_date: f.event_date.value, doors: f.doors.value || null, opener: f.opener.value || null, headliner: f.headliner.value || null, note: f.note.value || null, source: 'venue' };
      sb.from('stage_times').insert(row).then(function () { f.reset(); return sb.from('stage_times').select('*').eq('venue_slug', org.venue_slug).order('event_date'); }).then(function (r) { renderStage(r.data || []); });
    });
  }
  function renderSections(overrides) {
    var base = venueInfo[org.venue_slug] || {}; var byKey = {}; overrides.forEach(function (o) { byKey[o.section] = o; });
    $('[data-pane=sections]').innerHTML = SECTIONS.map(function (s) {
      var key = s[0], cur = byKey[key] ? byKey[key].content : (base[key] || {}); var stamp = byKey[key] ? 'Verified by the venue · ' + byKey[key].verified_at : (cur.verified ? 'Researched by Concerto · ' + cur.verified : 'Not yet published');
      return '<article class="section-card" data-section="' + key + '"><header><h3>' + s[1] + '</h3><span class="stamp ' + (byKey[key] ? 'venue' : '') + '">' + esc(stamp) + '</span></header>' +
        '<p class="summary">' + esc(cur.summary || cur.note || 'Nothing published yet.') + '</p>' +
        '<details><summary>Edit what fans see</summary><form>' +
        '<label>Summary<textarea name="summary" maxlength="600">' + esc(cur.summary || '') + '</textarea></label>' +
        (key === 'bagPolicy' ? '<label>Allowed (one per line)<textarea name="allowed">' + esc((cur.allowed || []).join('\n')) + '</textarea></label><label>Not allowed (one per line)<textarea name="prohibited">' + esc((cur.prohibited || []).join('\n')) + '</textarea></label>' : '') +
        '<label>Note<input name="note" maxlength="200" value="' + esc(cur.note || '') + '"></label>' +
        '<label>Official link<input type="url" name="officialLink" value="' + esc(cur.officialLink || '') + '"></label>' +
        '<button class="btn-primary" type="submit">Publish as verified by the venue</button></form></details></article>';
    }).join('');
    $$('[data-pane=sections] form').forEach(function (f) {
      f.addEventListener('submit', function (e) {
        e.preventDefault(); var key = f.closest('[data-section]').getAttribute('data-section'); var base = (venueInfo[org.venue_slug] || {})[key] || {};
        var content = Object.assign({}, base, { summary: f.summary.value.trim(), note: f.note.value.trim(), officialLink: f.officialLink.value.trim() });
        if (f.allowed) { content.allowed = f.allowed.value.split('\n').map(function (x) { return x.trim(); }).filter(Boolean); content.prohibited = f.prohibited.value.split('\n').map(function (x) { return x.trim(); }).filter(Boolean); }
        sb.from('venue_overrides').upsert({ venue_slug: org.venue_slug, section: key, content: content, verified_at: new Date().toISOString().slice(0, 10), updated_by: session.user.id }).then(function () {
          return sb.from('venue_overrides').select('*').eq('venue_slug', org.venue_slug);
        }).then(function (r) { renderSections(r.data || []); });
      });
    });
  }
  function renderStage(rows) {
    $('[data-stage-list]').innerHTML = rows.length ? rows.map(function (r) {
      return '<div class="list-row"><div><b>' + esc(r.event_date) + '</b><br><span>' + ['Doors ' + (r.doors || '—'), 'Opener ' + (r.opener || '—'), 'Headliner ' + (r.headliner || '—')].join(' · ') + (r.note ? ' · ' + esc(r.note) : '') + '</span></div><button data-del="' + r.id + '">Remove</button></div>';
    }).join('') : '<p class="console-hint">No stage times yet. Fans see "Doors 7:30 · stage time not yet known" until you add one.</p>';
    $$('[data-del]', $('[data-stage-list]')).forEach(function (b) { b.addEventListener('click', function () { sb.from('stage_times').delete().eq('id', b.getAttribute('data-del')).then(function () { return sb.from('stage_times').select('*').eq('venue_slug', org.venue_slug).order('event_date'); }).then(function (r) { renderStage(r.data || []); }); }); });
  }

  /* ---------- partner view ---------- */
  function renderPartner() {
    $('[data-partner-kind]').textContent = { restaurant: 'Restaurant partner', hotel: 'Hotel partner', artist: 'Artist partner' }[org.kind] || 'Partner';
    $('[data-partner-name]').textContent = org.name; show('partner'); wireTabs('partner');
    listPerks(); renderReport($('[data-view=partner] [data-pane=report]'), { partner: org.name });
    $('[data-form=perk]').addEventListener('submit', function (e) {
      e.preventDefault(); var f = e.target;
      var slugs = [].slice.call(f.venue_slugs.selectedOptions).map(function (o) { return o.value; });
      var row = { org_id: org.id, kind: org.kind, partner_name: org.name, offer: f.offer.value.trim(), details: f.details.value.trim() || null, url: f.url.value.trim() || null, venue_slugs: slugs, starts_on: f.starts_on.value || null, ends_on: f.ends_on.value || null, status: 'draft' };
      sb.from('perks').insert(row).then(function () { f.reset(); listPerks(); });
    });
  }
  function listPerks() {
    sb.from('perks').select('*').eq('org_id', org.id).order('created_at', { ascending: false }).then(function (r) {
      var rows = r.data || [];
      $('[data-perk-list]').innerHTML = rows.length ? rows.map(function (p) {
        return '<div class="list-row"><div><b>' + esc(p.offer) + '</b><br><span>' + esc((p.venue_slugs || []).map(function (s) { return (venues.find(function (v) { return v.id === s; }) || { name: s }).name; }).join(', ') || 'No venues yet') + '</span></div><span class="pill">' + esc(p.status === 'draft' ? 'In review' : p.status) + '</span></div>';
      }).join('') : '<p class="console-hint">No Perks yet. The first one you submit is reviewed within a day.</p>';
    });
  }

  /* ---------- report ---------- */
  function renderReport(host, filter) {
    var q = sb.from('partner_report_monthly').select('*');
    if (filter.venue) q = q.eq('venue_slug', filter.venue); if (filter.partner) q = q.eq('partner', filter.partner);
    q.order('month', { ascending: false }).limit(3).then(function (r) {
      var rows = r.data || []; var m = rows[0] || {};
      var cards = filter.venue
        ? [['Shows saved here', m.shows_saved], ['Guide opens', m.guide_opens], ['Bag Checks against your policy', m.bag_checks], ['Parking and rideshare taps', m.arrival_taps]]
        : [['Perk impressions', m.perk_impressions], ['Perk taps', m.perk_taps]];
      host.innerHTML = '<p class="console-hint">' + (rows[0] ? 'This month so far. Updates daily.' : 'Your report starts the day your page or Perk goes live.') + '</p><div class="report-grid">' + cards.map(function (c) { return '<div class="report-card"><b>' + (c[1] || 0) + '</b><span>' + c[0] + '</span></div>'; }).join('') + '</div>';
    });
  }

  function wireTabs(view) {
    var root = $('[data-view=' + view + ']');
    $$('[data-tab]', root).forEach(function (b) { b.addEventListener('click', function () {
      $$('[data-tab]', root).forEach(function (x) { x.classList.toggle('on', x === b); });
      $$('[data-pane]', root).forEach(function (p) { p.hidden = p.getAttribute('data-pane') !== b.getAttribute('data-tab'); });
    }); });
  }

  function init() {
    loadCatalog().then(function () { return sb.auth.getSession(); }).then(function (r) {
      session = r.data.session; wireSignin();
      if (!session) { show('signin'); return; }
      return resolveOrg().then(function (o) {
        org = o;
        if (!org) { show('signin'); status('Signed in as ' + session.user.email + '. We could not match you to a venue or business yet; if you claimed a venue, the email domain must match the venue\'s own website.', false); return; }
        if (org.kind === 'venue') renderVenue(); else renderPartner();
      });
    });
    sb.auth.onAuthStateChange(function (ev) { if (ev === 'SIGNED_IN' && !session) location.reload(); });
  }
  init();
})();
