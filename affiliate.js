/* affiliate.js — single source for all Concerto affiliate links.
 *
 * WHY THIS EXISTS: affiliate links must never be hand-pasted across 346 pages.
 * You set your IDs here once; every page generates correct, tagged links from
 * this config. Same discipline as build_static.py: the config is the memory.
 *
 * HOW TO ACTIVATE: fill in the IDs below as you get approved for each program
 * (see affiliate-setup.md). A program with an empty id is treated as "not yet
 * active" and Concerto falls back to the plain, un-tagged link so nothing
 * breaks and users still get where they're going — you just don't earn on it
 * until the id is filled. Flip a program on by pasting its id. That's it.
 *
 * DISCLOSURE: FTC requires disclosure when you earn commissions. Keep the
 * data-affiliate attribute on generated links (renderers add a small
 * "Concerto may earn a commission" note where these appear).
 */
(function (global) {
  'use strict';

  const AFFILIATE = {
    // ── Tickets ───────────────────────────────────────────────
    // SeatGeek Affiliate (via Partnerize/impact). Easiest to join; pays on sale.
    // Get: seatgeek.com/affiliates  →  your "aid" tracking id.
    seatgeek: {
      id: '',                         // e.g. 'concerto_123'
      // SeatGeek supports an ?aid= param on any event/search URL.
      wrap: (url, id) => addParams(url, { aid: id }),
    },

    // Ticketmaster (via Impact Radius partner program).
    // Get: ticketmaster.com/partners  →  Impact tracking template.
    // TM uses a redirect template; paste the impact "irgwc" click URL prefix.
    ticketmaster: {
      id: '',                         // your Impact publisher id
      clickPrefix: '',                // e.g. 'https://ticketmaster.evyy.net/c/PUBID/CAMP/TARGET?u='
      wrap: (url, id, cfg) =>
        cfg.clickPrefix ? cfg.clickPrefix + encodeURIComponent(url)
                        : addParams(url, {}),   // no prefix set → plain link
    },

    // ── Hotels (near-venue overnight) ─────────────────────────
    // Booking.com Affiliate Partner. Get: booking.com/affiliate → aid.
    booking: {
      id: '',                         // your Booking 'aid'
      // Build a search near the venue's lat/lng.
      searchNear: (lat, lng, id, label) => addParams(
        'https://www.booking.com/searchresults.html',
        id ? { aid: id, latitude: lat, longitude: lng, ss: label || '' }
           : { latitude: lat, longitude: lng, ss: label || '' }
      ),
    },

    // ── Parking ───────────────────────────────────────────────
    // SpotHero Affiliate (via Impact). Get: spothero.com/developers or their
    // Impact program → click template. Falls back to a venue search.
    spothero: {
      id: '',
      clickPrefix: '',
      searchNear: (lat, lng, id, cfg, label) => {
        const base = addParams('https://spothero.com/search',
          { latitude: lat, longitude: lng, q: label || '' });
        return cfg.clickPrefix ? cfg.clickPrefix + encodeURIComponent(base) : base;
      },
    },

    // ── Rideshare ─────────────────────────────────────────────
    // Uber deep-link (you already build these). Uber's affiliate/referral is
    // limited; keep the deep-link, add client_id if you get one.
    uber: {
      id: '',                         // Uber client_id if enrolled
      // your existing deep links already work; this just tags them if id set.
      tag: (url, id) => id ? addParams(url, { client_id: id }) : url,
    },

    // ── Restaurants (Top Picks) ───────────────────────────────
    // OpenTable Affiliate (via CJ/Impact). Get: opentable.com/affiliate.
    opentable: {
      id: '',
      clickPrefix: '',
      restaurant: (otUrl, id, cfg) =>
        cfg.clickPrefix ? cfg.clickPrefix + encodeURIComponent(otUrl) : otUrl,
    },
  };

  // ── helpers ─────────────────────────────────────────────────
  function addParams(url, params) {
    try {
      const u = new URL(url);
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') u.searchParams.set(k, v);
      });
      return u.toString();
    } catch (e) {
      return url; // malformed url → return untouched, never break the link
    }
  }

  // ── public API ──────────────────────────────────────────────
  // Each returns { href, earning } so renderers know whether to show the
  // "Concerto may earn a commission" note (earning=true only when id present).
  const Aff = {
    isActive(program) {
      const p = AFFILIATE[program];
      return !!(p && (p.id || p.clickPrefix));
    },

    ticket(url, provider) {
      // provider: 'seatgeek' | 'ticketmaster' (default: whatever the url is)
      const prov = provider
        || (url.includes('seatgeek') ? 'seatgeek'
            : url.includes('ticketmaster') ? 'ticketmaster' : null);
      if (!prov || !AFFILIATE[prov]) return { href: url, earning: false };
      const cfg = AFFILIATE[prov];
      const href = cfg.wrap(url, cfg.id, cfg);
      return { href, earning: this.isActive(prov) };
    },

    hotelNear(lat, lng, label) {
      const cfg = AFFILIATE.booking;
      return { href: cfg.searchNear(lat, lng, cfg.id, label), earning: !!cfg.id };
    },

    parkingNear(lat, lng, label) {
      const cfg = AFFILIATE.spothero;
      return { href: cfg.searchNear(lat, lng, cfg.id, cfg, label), earning: this.isActive('spothero') };
    },

    ride(url) {
      const cfg = AFFILIATE.uber;
      return { href: cfg.tag(url, cfg.id), earning: !!cfg.id };
    },

    restaurant(otUrl) {
      const cfg = AFFILIATE.opentable;
      return { href: cfg.restaurant(otUrl, cfg.id, cfg), earning: this.isActive('opentable') };
    },
  };

  global.ConcertoAffiliate = Aff;
})(typeof window !== 'undefined' ? window : this);
