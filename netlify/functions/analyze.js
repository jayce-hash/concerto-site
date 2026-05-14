// netlify/functions/analyze.js
// Proxies bag photo + venue policy to Claude — keeps API key server-side

export async function handler(event) {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, body: 'Invalid JSON' };
  }

  const { imageB64, venue } = body;
  if (!imageB64 || !venue) {
    return { statusCode: 400, body: 'Missing imageB64 or venue' };
  }

  const policy = `Venue: ${venue.n} (${venue.loc})
Policy: ${venue.policy_text || ''}
Allowed: ${(venue.allows || []).join('; ')}
Prohibited: ${(venue.denies || []).join('; ')}`;

  const prompt = `You are Concerto's Bag Check AI. Analyze the bag in this photo for entry to ${venue.n}.

${policy}

Respond ONLY with valid JSON, no markdown:
{"verdict":"pass"|"warn"|"fail","bag_type":"e.g. Small Leather Clutch","dims":"e.g. Est. 6\\" × 4\\" · Leather · Metal clasp","confidence":<60-98>,"label":"2-4 word headline","findings":[{"s":"pass"|"warn"|"fail","rule":"Short rule","detail":"1-2 sentence explanation"}]}

Include 3-5 findings citing specific policy rules.`;

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY,
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
      })
    });

    if (!response.ok) {
      const err = await response.text();
      console.error('Anthropic error:', err);
      return { statusCode: 502, body: 'AI service error' };
    }

    const data = await response.json();
    const text = data.content[0].text.trim().replace(/```json|```/g, '').trim();
    const result = JSON.parse(text);

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(result)
    };
  } catch (err) {
    console.error('analyze error:', err);
    return { statusCode: 500, body: 'Internal error' };
  }
}
