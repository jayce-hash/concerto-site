// netlify/functions/geo.js
// Where is this visitor, roughly? Netlify attaches an edge geolocation to
// every function call (context.geo). No IP leaves Concerto, no third-party
// lookup, no permission prompt. The site uses it to open on shows near the
// visitor tonight; the app uses the phone's own location instead.
exports.handler = async function (event, context) {
  const g = (context && context.geo) || {};
  const city = g.city || (g.subdivision && g.subdivision.name) || '';
  const lat = g.latitude, lng = g.longitude;
  const body = lat && lng
    ? { ok: true, city, region: g.subdivision && g.subdivision.code, country: g.country && g.country.code, lat, lng }
    : { ok: false };
  return { statusCode: 200, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'private, max-age=600' }, body: JSON.stringify(body) };
};
