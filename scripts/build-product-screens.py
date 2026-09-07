#!/usr/bin/env python3
"""Turn raw iPhone captures into web-ready app screens.

Drop real captures into img/product/source/<name>.png and run this script.
It repaints the iOS status bar to the marketing standard (12:00, full signal,
full Wi-Fi, full battery, no location or recording indicators) so the site
never shows a stale clock, then writes a compact WebP to img/product/screens/.
The device frame in css/public-v6.css draws the Dynamic Island and is sized to
this exact aspect ratio, so the whole screen is visible with nothing cut off.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'img/product/source'
OUT = ROOT / 'img/product/screens'
FONT = ROOT / 'scripts/assets/Inter-SemiBold.ttf'
OUT.mkdir(parents=True, exist_ok=True)
SS = 4  # supersample for crisp edges


def status_bar_box(im):
    # iOS status bar occupies the top ~4.9% of a full-height capture.
    return round(im.height * 0.049)


def background_color(im):
    px = im.load()
    return px[6, 6]


def is_dark(rgb):
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) < 128


def paint_status_bar(im):
    w, h = im.size
    bar = status_bar_box(im)
    bg = background_color(im)
    ink = (255, 255, 255) if is_dark(bg) else (0, 0, 0)
    s = w / 941.0  # everything below is tuned at 941px wide and scaled

    layer = Image.new('RGB', (w * SS, bar * SS), bg)
    d = ImageDraw.Draw(layer)
    S = SS * s
    cy = 76 * S  # vertical centre of the bar contents

    # Clock
    font = ImageFont.truetype(str(FONT), int(34 * S))
    tx, ty = 68 * S, cy
    d.text((tx, ty), '12:00', font=font, fill=ink, anchor='lm')

    # Signal: four bars, all full
    x = 670 * S
    for i, hh in enumerate((11, 16, 21, 26)):
        bx = x + i * 11 * S
        d.rounded_rectangle((bx, cy + 14 * S - hh * S, bx + 7 * S, cy + 14 * S), radius=2 * S, fill=ink)

    # Wi-Fi: three arcs plus the dot
    wx, wy = 760 * S, cy + 13 * S  # fan centre sits on the dot
    for r in (27, 19, 11):
        d.arc((wx - r * S, wy - r * S, wx + r * S, wy + r * S), 228, 312, fill=ink, width=int(5.2 * S))
    d.ellipse((wx - 4.5 * S, wy - 4.5 * S, wx + 4.5 * S, wy + 4.5 * S), fill=ink)

    # Battery: outline, full fill, nub
    bx, by = 810 * S, cy - 14 * S
    bw, bh = 54 * S, 27 * S
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=8 * S, fill=ink)  # iOS 17 full battery is a solid pill
    d.rounded_rectangle((bx + bw + 2.5 * S, by + 9 * S, bx + bw + 6.5 * S, by + bh - 9 * S), radius=2 * S, fill=ink)

    layer = layer.resize((w, bar), Image.LANCZOS)
    im.paste(layer, (0, 0))
    return im


built = []
for f in sorted(SRC.glob('*.png')):
    im = Image.open(f).convert('RGB')
    im = paint_status_bar(im)
    out = OUT / f'{f.stem}.webp'
    im.save(out, 'WEBP', quality=86, method=6)
    built.append((f.stem, im.width, im.height, out.stat().st_size // 1024))

for name, w, h, kb in built:
    print(f'{name:12s} {w}x{h}  {kb} KB')
if built:
    print(f'\nCSS aspect ratio for .device: {built[0][1]}/{built[0][2]}')
