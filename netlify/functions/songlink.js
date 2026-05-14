const https = require("https");

exports.handler = async (event) => {
  try {
    const artistRaw = (event.queryStringParameters?.artist || "").trim();
    const titleRaw  = (event.queryStringParameters?.title || "").trim();

    if (!artistRaw || !titleRaw) {
      return json(400, { error: "Missing artist or title" });
    }

    const term = `${titleRaw} ${artistRaw}`;
    const itunesUrl =
      `https://itunes.apple.com/search?` +
      `term=${encodeURIComponent(term)}&entity=song&limit=5`;

    const itunes = await getJson(itunesUrl);
    const results = Array.isArray(itunes?.results) ? itunes.results : [];

    const artistLower = normalize(artistRaw);
    const titleLower  = normalize(titleRaw);

    const best =
      results.find(r =>
        normalize(r.artistName || "").includes(artistLower) &&
        normalize(r.trackName  || "").includes(titleLower)
      ) || results[0];

    if (!best?.trackViewUrl) {
      return json(200, { appleUrl: null });
    }

    return json(200, { appleUrl: best.trackViewUrl });

  } catch (err) {
    return json(500, { error: "Song resolution failed", details: String(err) });
  }
};

function normalize(str) {
  return String(str)
    .toLowerCase()
    .replace(/['']/g, "'")
    .replace(/[""]/g, '"')
    .replace(/\([^)]*\)/g, " ")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          const parsed = JSON.parse(data || "{}");
          if (res.statusCode < 200 || res.statusCode >= 300) {
            return resolve({ __httpError: res.statusCode });
          }
          resolve(parsed);
        } catch (e) {
          reject(new Error(`Invalid JSON from ${url}`));
        }
      });
    }).on("error", reject);
  });
}

function json(statusCode, body) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    body: JSON.stringify(body)
  };
}
