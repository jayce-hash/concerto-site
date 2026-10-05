// Self-serve signup, final step: validate, create the partner (unpaid), hand off to Stripe Checkout.
// Paid = live automatically through stripe-webhook. Nothing is public until Stripe says paid.
const guard = require('./lib/guard');
const { createClient } = require('@supabase/supabase-js');
const { SITE, venueBySlug, miles, kindFits } = require('./lib/partner-self-serve');

const clean = (s, n) => String(s || '').replace(/[\u0000-\u001f\u007f<>]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, n);

exports.handler = async (event) => {
  const H = { ...guard.corsHeaders(event, 'POST, OPTIONS'), 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: H, body: '' };
  if (event.httpMethod !== 'POST') return guard.refuse(event, 405, 'method not allowed', 'POST, OPTIONS');
  if (!guard.originOf(event).ok) return guard.refuse(event, 403, 'forbidden', 'POST, OPTIONS');
  if (guard.limited(event, 6, 10 * 60000)) return guard.refuse(event, 429, 'Too many attempts. Try again in a few minutes.', 'POST, OPTIONS');
  let b; try { b = JSON.parse(event.body || '{}'); } catch { return guard.refuse(event, 400, 'Bad request.', 'POST, OPTIONS'); }
  if (b.company) return { statusCode: 200, headers: H, body: JSON.stringify({ ok: true }) }; // honeypot: quietly ignore bots

  const kind = b.kind === 'hotel' ? 'hotel' : 'restaurant';
  const plan = b.plan === 'annual' ? 'annual' : 'monthly';
  const venue = venueBySlug(String(b.venue || ''));
  const name = clean(b.name, 60);
  const blurb = clean(b.blurb, 110);
  let url = String(b.url || '').trim();
  const fail = (msg) => guard.refuse(event, 400, msg, 'POST, OPTIONS');
  if (!venue) return fail('Choose a venue from the list.');
  if (!b.placeId) return fail('Search for your business and select it.');
  if (name.length < 2) return fail('Add the name for your card.');
  if (blurb.length < 10) return fail('Add one line for fans (at least 10 characters).');
  if (/https?:\/\/|www\./i.test(blurb)) return fail('Please keep links out of your one line for fans.');
  try { const u = new URL(url); if (u.protocol !== 'https:' || !u.hostname.includes('.')) throw 0; url = u.toString(); } catch { return fail('Add a link that starts with https://'); }
  if (!b.agree) return fail('Please agree to the terms.');

  // Re-check the business with Google on the server: real place, right kind, near the venue.
  const key = process.env.GOOGLE_PLACES_SERVER_KEY;
  let place;
  try {
    const r = await fetch(`https://places.googleapis.com/v1/places/${encodeURIComponent(String(b.placeId))}`, {
      headers: { 'X-Goog-Api-Key': key, 'X-Goog-FieldMask': 'id,displayName,formattedAddress,location,types' } });
    if (!r.ok) return fail('We could not confirm that business. Search again and select it.');
    place = await r.json();
  } catch { return guard.refuse(event, 502, 'Could not confirm your business. Try again.', 'POST, OPTIONS'); }
  const loc = { lat: place.location?.latitude, lng: place.location?.longitude };
  if (loc.lat == null) return fail('We could not confirm that business. Search again and select it.');
  if (miles(venue, loc) > 5) return fail(`That business is more than 5 miles from ${venue.name}.`);
  if (!kindFits(kind, place.types)) return fail(kind === 'hotel' ? 'That business is not listed as a hotel.' : 'That business is not listed as a restaurant, bar, or cafe.');

  const sb = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } });
  // Reuse an unpaid signup for the same business and venue, so retries don't create duplicates.
  const { data: existing } = await sb.from('partner_orgs').select('id,plan,listed_until').eq('name', name).contains('venue_slugs', [venue.id]).limit(1);
  let id = existing && existing[0] && existing[0].id;
  const row = { kind, name, venue_slugs: [venue.id], address: clean(place.formattedAddress, 200), url, blurb, lat: loc.lat, lng: loc.lng, listed: true };
  if (id) {
    const today = new Date().toISOString().slice(0, 10);
    if (existing[0].plan === 'paid' && (!existing[0].listed_until || existing[0].listed_until >= today))
      return fail(`${name} is already an active Concerto Partner at ${venue.name}.`);
    const { error } = await sb.from('partner_orgs').update(row).eq('id', id);
    if (error) return guard.refuse(event, 500, 'Could not save. Try again.', 'POST, OPTIONS');
  } else {
    const { data, error } = await sb.from('partner_orgs').insert({ ...row, plan: 'pending' }).select('id').single();
    if (error || !data) return guard.refuse(event, 500, 'Could not save. Try again.', 'POST, OPTIONS');
    id = data.id;
  }
  return { statusCode: 200, headers: H, body: JSON.stringify({ ok: true, checkout: `${SITE}/.netlify/functions/partner-checkout?org=${encodeURIComponent(id)}&plan=${plan}` }) };
};
