'use strict';
function dateOK(value) {
  if (!value) return true;
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
}
function livePerks(rows, today) {
  return (rows || []).filter(p => typeof p.offer === 'string' && p.offer.trim() && typeof p.details === 'string' && p.details.trim()
    && dateOK(p.starts_on) && dateOK(p.ends_on)
    && (!p.starts_on || p.starts_on <= today) && (!p.ends_on || p.ends_on >= today)
    && (!p.starts_on || !p.ends_on || p.starts_on <= p.ends_on)).map(p => {
      let url = null;
      try { const u = new URL(p.url); if (u.protocol === 'https:' && !u.username && !u.password) url = u.href; } catch (_) {}
      return { ...p, url };
    });
}
module.exports = { livePerks, dateOK };
