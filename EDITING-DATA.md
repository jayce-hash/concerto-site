# Editing Concerto data

Everything below is done in the GitHub web editor. No terminal.

After you commit, two things happen automatically:

1. A GitHub Action regenerates `search-index.json` and `sitemap.xml`
   and checks your edit for mistakes.
2. Netlify deploys. The **app picks up the new data on its next
   launch**, with no App Store update, because the app fetches these
   files from concertocity.com at runtime.

If the Action goes red, something is wrong with the edit. Open the
Actions tab and read the FAIL lines. Nothing ships until it is green.

---

## The only four files you ever edit

| File | What lives there |
|---|---|
| `data/venues.json` | The venue list: id, name, city, state, lat, lng |
| `data/venue_info.json` | The real content: bag policy, parking, concessions, rideshare |
| `data/tours.json` | The tour list: tourId, tourName, artist, tourWebsite |
| `setlists.json` | Setlists, keyed by artist slug |

**Never hand-edit `search-index.json` or `sitemap.xml`.** They are
generated. Editing them by hand is what caused four tours to become
unsearchable.

---

## Add a tour

One entry in `data/tours.json`:

```json
{
  "tourId": "artist-name-tour-name-tour",
  "tourName": "Tour Name Tour",
  "artist": "Artist Name",
  "tourWebsite": "https://example.com/tour",
  "lastShowDate": "2027-03-14"
}
```

`tourId` must be lowercase letters, numbers and single hyphens only.
It becomes the URL: `concertocity.com/tour/artist-name-tour-name-tour`.

`lastShowDate` is optional but add it. It is what lets the build warn
you when a tour has ended instead of you noticing months later.

Setlists are separate: add the artist to `setlists.json` under their
slug (`artist-name`).

---

## Remove a tour

Delete its entry from `data/tours.json`. That is the whole job. The
search index and sitemap update themselves.

If the tour was well known, add a redirect in `_redirects` above the
404 line so old links do not dead-end:

```
/tour/that-tour-id   /tours   301
```

---

## Add a venue

Two files, both required. Miss either one and the build fails loudly
rather than shipping a broken page.

**1. `data/venues.json`**

```json
{
  "id": "venue-slug",
  "name": "Venue Name",
  "city": "City",
  "state": "ST",
  "country": "US",
  "lat": 32.7767,
  "lng": -96.797,
  "guideUrl": "https://concertocity.com/venue/venue-slug"
}
```

**2. `data/venue_info.json`** under the same `"venue-slug"` key: bag
policy, parking, concessions, rideshare. Copy the shape from a
similar venue already in the file and include a `"verified"` date.

The venue page works immediately. Its own title tag and Google
listing appear after the next app export, since those are generated
at build time.

---

## Update venue info

Edit that venue's entry in `data/venue_info.json` and **update its
`verified` date to today**. The date is shown in the app. It is the
trust product; a stale date is worse than no date.

---

## When the build fails

Common causes, all caught before anything ships:

- Venue in `venues.json` with no entry in `venue_info.json`, or the
  reverse
- A slug with capitals, spaces or underscores
- A duplicate id
- Missing name, city, lat or lng
- Broken JSON, usually a trailing comma or a missing brace

Fix the file and commit again. The Action re-runs on its own.
