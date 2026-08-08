// netlify/functions/weather.js
//
// Weather for a venue's coordinates, proxied server-side rather than
// calling Open Meteo straight from the phone. Two reasons: it keeps a
// user's IP off a third party the way tm.js and venue-photo.js already
// do for their calls, and it lets Netlify's CDN cache identical
// lat/lng requests instead of every phone hitting Open Meteo on its
// own. No API key needed -- Open Meteo's free tier is keyless -- so
// there's nothing to add to Netlify's environment variables.
//
// Query params: lat, lng, date (YYYY-MM-DD, the show date). Returns a
// same-day forecast when the date is inside Open Meteo's 16-day
// window, otherwise { available: false } so the app can fall back to
// no weather card rather than a wrong one.

exports.handler = async function (event) {
  const { lat, lng, date } = event.queryStringParameters || {};
  if (!lat || !lng || !date) {
    return { statusCode: 400, body: JSON.stringify({ error: 'lat, lng, and date are required' }) };
  }

  const today = new Date();
  const target = new Date(`${date}T00:00:00Z`);
  const daysOut = Math.round((target - today) / 86400000);
  if (daysOut < 0 || daysOut > 15) {
    return {
      statusCode: 200,
      headers: { 'Cache-Control': 'public, max-age=3600' },
      body: JSON.stringify({ available: false }),
    };
  }

  const params = new URLSearchParams({
    latitude: lat,
    longitude: lng,
    daily: 'weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
    temperature_unit: 'fahrenheit',
    timezone: 'auto',
    start_date: date,
    end_date: date,
  });

  try {
    const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
    if (!res.ok) throw new Error(`Open Meteo ${res.status}`);
    const data = await res.json();
    const d = data.daily;
    if (!d || !d.time?.length) {
      return { statusCode: 200, body: JSON.stringify({ available: false }) };
    }
    return {
      statusCode: 200,
      // Same forecast for the same day/place regardless of who asks,
      // so a short shared cache is safe and cuts upstream calls a lot
      // on popular shows.
      headers: { 'Cache-Control': 'public, max-age=3600' },
      body: JSON.stringify({
        available: true,
        date: d.time[0],
        highF: Math.round(d.temperature_2m_max[0]),
        lowF: Math.round(d.temperature_2m_min[0]),
        precipPercent: d.precipitation_probability_max[0],
        weatherCode: d.weathercode[0],
      }),
    };
  } catch (err) {
    return { statusCode: 200, body: JSON.stringify({ available: false, error: String(err) }) };
  }
};
