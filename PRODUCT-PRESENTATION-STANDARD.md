# Concerto Product Presentation Standard

The website presents the real app without simulated hardware, rounded device borders, floating cards, or rebuilt app interfaces.

Use supplied native screenshots as the source. Preserve their content and aspect ratio. Label them as example app views so event dates and times are not mistaken for live website information. Do not repaint status bars, change prices, or manufacture a successful result.

Encode sources with `scripts/refresh-product-captures.py`. It updates the content-hashed manifest without deleting previous assets. Then run `scripts/rebuild-consumer-site.py`.

Use `SCREENSHOT-REPLACEMENT-GUIDE.md` for filenames and exact app views. The old `build-product-screens.py` command now delegates to the same encoder and no longer repaints status bars.

The website and app share product facts and brand identity. The website has its own editorial presentation; the native app design stays unchanged.
