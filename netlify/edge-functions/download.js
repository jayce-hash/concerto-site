// concertocity.com/download: one link (and one QR code) for every phone.
// Android goes to Google Play, iPhone and iPad to the App Store, anything else to the
// homepage's download section. ?ct= carries the campaign name to either store.
const APP = 'https://apps.apple.com/us/app/concerto-show-go/id6744903414';
const PLAY = 'https://play.google.com/store/apps/details?id=com.v8ef92dbd0a8.www';

export default async (request) => {
  const url = new URL(request.url);
  const ct = (url.searchParams.get('ct') || 'website-download').replace(/[^a-z0-9-]/gi, '').slice(0, 60);
  const ua = request.headers.get('user-agent') || '';
  let to;
  if (/Android/i.test(ua)) to = `${PLAY}&referrer=${encodeURIComponent(`utm_source=concertocity&utm_campaign=${ct}`)}`;
  else if (/iPhone|iPad|iPod/i.test(ua)) to = `${APP}?pt=127753814&ct=${ct}&mt=8`;
  else to = `${url.origin}/#download`;
  return new Response(null, { status: 302, headers: { Location: to, 'Cache-Control': 'no-store', Vary: 'User-Agent' } });
};

export const config = { path: ['/download', '/app'] };
