# Website screenshots

The phone screenshots on the Features and Concerto+ pages are the real app, captured from its web build, with Concerto's own illustrations in place of every Ticketmaster and Google photo, then drawn inside an iPhone.

1. In the app repo: `npx expo export --platform web --output-dir <web>`. Bag Check only opens on the web when `globalThis.__cap` is set, which needs a one-line temporary change in `app/bagcheck.tsx` (do not ship it).
2. Serve `<web>` beside this repo's `data/` on port 8791.
3. `node shoot.js` writes one 402 x 815 capture per screen to `raw/`. `node frame.js` draws each inside the phone and writes `framed/`.
4. Save each as WebP in `img/features/<key>.<hash>.webp` and delete the file it replaces. The build stops if a key has two files.

`artist*.jpg` and `venue*.jpg` are the illustrations. `map.jpg` is the Near Me map as the phone app draws it. Tour dates and listings in `lib.js` are typed in from public announcements; check them before recapturing.
