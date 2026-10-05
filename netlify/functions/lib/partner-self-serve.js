// Shared helpers for self-serve Concerto Partner signup.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SITE = 'https://concertocity.com';
let VENUES = null;
function venues() {
  if (!VENUES) {
    // Packaged functions can place included files at slightly different depths; try each.
    const tries = [path.join(__dirname, '..', '..', '..', 'data', 'venues.json'), path.join(__dirname, '..', '..', 'data', 'venues.json'),
      path.join(process.cwd(), 'data', 'venues.json'), path.join(__dirname, 'data', 'venues.json')];
    const f = tries.find((t) => { try { return fs.existsSync(t); } catch { return false; } });
    VENUES = f ? JSON.parse(fs.readFileSync(f, 'utf8')) : [];
  }
  return VENUES;
}
function venueBySlug(slug) { return venues().find((v) => v.id === slug) || null; }
function miles(a, b) {
  const R = 3958.8, r = (x) => (x * Math.PI) / 180;
  const dLat = r(b.lat - a.lat), dLng = r(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
// Same list as the app and the website's "Around the venue": never a partner category.
const NOT_A_PICK = new Set(['convenience_store', 'gas_station', 'pharmacy', 'drugstore', 'supermarket', 'grocery_store', 'atm', 'bank', 'car_wash', 'car_repair', 'parking', 'apartment_building', 'apartment_complex', 'condominium_complex', 'housing_complex', 'real_estate_agency', 'travel_agency']);
const FOOD = /restaurant|bar|cafe|coffee|bakery|food|meal_|pub|brewery|winery|night_club|dessert|ice_cream|steak|pizza|sushi|bistro|diner|deli/;
const STAY = /lodging|hotel|motel|inn|resort|bed_and_breakfast|hostel/;
function kindFits(kind, types) {
  const t = types || [];
  if (t.some((x) => NOT_A_PICK.has(x))) return false;
  return t.some((x) => (kind === 'hotel' ? STAY : FOOD).test(x));
}
// Remove links: an HMAC of the partner id, keyed by a server-only secret, so links can't be guessed.
function removeToken(orgId) {
  return crypto.createHmac('sha256', String(process.env.SUPABASE_SERVICE_ROLE_KEY || 'x')).update('remove:' + orgId).digest('hex').slice(0, 32);
}
function removeLink(orgId) { return `${SITE}/.netlify/functions/partner-remove?org=${encodeURIComponent(orgId)}&t=${removeToken(orgId)}`; }
function tokenOk(orgId, t) {
  const want = Buffer.from(removeToken(orgId)), got = Buffer.from(String(t || ''));
  return want.length === got.length && crypto.timingSafeEqual(want, got);
}
module.exports = { SITE, venues, venueBySlug, miles, kindFits, removeLink, tokenOk };
