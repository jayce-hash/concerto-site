// netlify/functions/top-picks.js
// Serves Concerto Top Picks as JSON, sourced from a published Google Sheet (CSV).
// Edit the sheet -> changes appear here within the cache window (~5 min).
// Falls back to the static top_picks.json if the sheet isn't configured or is unreachable,
// so the site always has data.

const FALLBACK_URL = 'https://concerto-venue-map.netlify.app/data/top_picks.json';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Cache-Control': 'public, max-age=300',
  'Content-Type': 'application/json',
};

// Minimal RFC-4180 CSV parser: handles quoted fields, escaped quotes, and commas/newlines inside quotes.
function parseCSV(text) {
  const rows = [];
  let row = [], field = '', i = 0, inQ = false;
  text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  while (i < text.length) {
    const c = text[i];
    if (inQ) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
        inQ = false; i++; continue;
      }
      field += c; i++; continue;
    }
    if (c === '"') { inQ = true; i++; continue; }
    if (c === ',') { row.push(field); field = ''; i++; continue; }
    if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; i++; continue; }
    field += c; i++;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function slugify(s) {
  return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function rowsToTopPicks(rows) {
  if (!rows.length) return [];
  const header = rows[0].map(h => h.trim());
  const idx = {};
  header.forEach((h, n) => { idx[h] = n; });
  const get = (r, k) => (idx[k] != null && r[idx[k]] != null ? String(r[idx[k]]).trim() : '');
  const byVenue = new Map();
  for (let r = 1; r < rows.length; r++) {
    const row = rows[r];
    if (!row || !row.some(c => (c || '').trim())) continue;       // skip blank lines
    const venueName = get(row, 'venueName');
    const spotName = get(row, 'spotName');
    if (!venueName || !spotName) continue;                         // need at least venue + spot
    const slug = get(row, 'slug') || slugify(venueName);
    if (!byVenue.has(slug)) {
      byVenue.set(slug, { venueName, slug, city: get(row, 'city'), state: get(row, 'state'), items: [] });
    }
    const tier = (get(row, 'tier') || 'editorial').toLowerCase();
    byVenue.get(slug).items.push({
      name: spotName,
      address: get(row, 'address'),
      placeId: get(row, 'placeId') || null,
      notes: get(row, 'notes'),
      tier,
      badge: get(row, 'badge') || (tier === 'partner' ? 'Partner' : 'Concerto Top Pick'),
      sponsored: /^(true|yes|1)$/i.test(get(row, 'sponsored')),
      partnerId: get(row, 'partnerId') || null,
      term: get(row, 'term') || null,
      trackingId: get(row, 'trackingId') || (slug + '__' + slugify(spotName)),
    });
  }
  return [...byVenue.values()];
}

export async function handler(event) {
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: CORS, body: '' };
  const sheetUrl = process.env.TOP_PICKS_SHEET_CSV_URL;
  try {
    if (!sheetUrl) throw new Error('sheet not configured');
    const res = await fetch(sheetUrl);
    if (!res.ok) throw new Error('sheet fetch ' + res.status);
    const data = rowsToTopPicks(parseCSV(await res.text()));
    if (!data.length) throw new Error('sheet empty');
    return { statusCode: 200, headers: CORS, body: JSON.stringify(data) };
  } catch (e) {
    try {
      const res = await fetch(FALLBACK_URL);
      return { statusCode: 200, headers: CORS, body: JSON.stringify(await res.json()) };
    } catch (e2) {
      return { statusCode: 200, headers: CORS, body: '[]' };
    }
  }
}
