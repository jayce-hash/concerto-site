// netlify/functions/maps-key.js
// Serves the browser-restricted Google Maps JS API key at runtime so the key
// never lives in the repo (keeps deploy secret-scanning happy).
// Set GOOGLE_MAPS_BROWSER_KEY in Netlify → Site settings → Environment variables.
export async function handler() {
  const key = process.env.GOOGLE_MAPS_BROWSER_KEY || '';
  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'text/plain',
      'Cache-Control': 'public, max-age=3600'
    },
    body: key
  };
}
