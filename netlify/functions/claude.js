// netlify/functions/claude.js
// Shared proxy for all Concerto premium features
// Handles: Claude AI, Ticketmaster, Google Places, Geocode, Bag Check

exports.handler = async function(event) {
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
      },
      body: '',
    };
  }

  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
  };

  try {
    const { service, ...body } = JSON.parse(event.body);

    // ── Claude (AI itinerary, bag check, chat) ──────
    if (service === 'claude') {
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type':      'application/json',
          'x-api-key':         process.env.ANTHROPIC_API_KEY,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    // ── Bag Check (image analysis) ──────────────────
    if (service === 'bag_check') {
      const { imageB64, venue } = body;
      const policy = `Venue: ${venue.n} (${venue.loc})
Policy: ${venue.policy_text || ''}
Allowed: ${(venue.allows || []).join('; ')}
Prohibited: ${(venue.denies || []).join('; ')}`;

      const prompt = `You are Concerto's Bag Check AI. Analyze the bag in this photo for entry to ${venue.n}.

${policy}

Respond ONLY with valid JSON, no markdown:
{"verdict":"pass"|"warn"|"fail","bag_type":"e.g. Small Leather Clutch","dims":"e.g. Est. 6\\" × 4\\" · Leather · Metal clasp","confidence":<60-98>,"label":"2-4 word headline","findings":[{"s":"pass"|"warn"|"fail","rule":"Short rule","detail":"1-2 sentence explanation"}]}

Include 3-5 findings citing specific policy rules.`;

      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type':      'application/json',
          'x-api-key':         process.env.ANTHROPIC_API_KEY,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 1000,
          messages: [{
            role: 'user',
            content: [
              { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: imageB64 } },
              { type: 'text', text: prompt }
            ]
          }]
        }),
      });
      const data = await response.json();
      const text = (data?.content?.[0]?.text || '').trim().replace(/```json|```/g, '').trim();
      try {
        return { statusCode: 200, headers, body: JSON.stringify(JSON.parse(text)) };
      } catch {
        return { statusCode: 500, headers, body: JSON.stringify({ error: 'Parse failed', raw: text.slice(0, 200) }) };
      }
    }

    // ── Ticketmaster ────────────────────────────────
    if (service === 'ticketmaster') {
      const { keyword, size = 10 } = body;
      const url = `https://app.ticketmaster.com/discovery/v2/events.json`
        + `?apikey=${process.env.TICKETMASTER_API_KEY}`
        + `&keyword=${encodeURIComponent(keyword)}`
        + `&size=${size}&sort=date,asc&classificationName=music`;
      const response = await fetch(url);
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    // ── Google Places nearby ────────────────────────
    if (service === 'places_nearby') {
      const { lat, lng, type, keyword, radius = 2000 } = body;
      const url = `https://maps.googleapis.com/maps/api/place/nearbysearch/json`
        + `?location=${lat},${lng}`
        + `&radius=${radius}`
        + `&type=${encodeURIComponent(type)}`
        + `&keyword=${encodeURIComponent(keyword)}`
        + `&key=${process.env.GOOGLE_MAPS_API_KEY}`;
      const response = await fetch(url);
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    // ── Google Geocode ──────────────────────────────
    if (service === 'geocode') {
      const { address } = body;
      const url = `https://maps.googleapis.com/maps/api/geocode/json`
        + `?address=${encodeURIComponent(address)}`
        + `&key=${process.env.GOOGLE_MAPS_API_KEY}`;
      const response = await fetch(url);
      const data = await response.json();
      return { statusCode: response.status, headers, body: JSON.stringify(data) };
    }

    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Unknown service' }) };

  } catch (err) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: err.message }) };
  }
};
