#!/usr/bin/env python3
"""Chart the per-drawing step of a cycle with the WRAP step drawn last.

A closed loop's wrap step (last drawing -> first) sits inside the same band as
every ordinary step. The pre-fix wave field carried a non-integer harmonic in
its cross-chop, so the wrap step towered over the band -- plain in this chart,
invisible in any average of the cycle.

Drawn with PIL: this machine's python is externally managed and has no
matplotlib, and a 40-line plotter is cheaper than fighting PEP 668.
"""
import argparse, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
ap = argparse.ArgumentParser()
ap.add_argument("--pair", nargs=3, action="append", required=True,
                metavar=("LABEL", "BEFORE_DIR", "AFTER_DIR"))
ap.add_argument("--out", required=True)
a = ap.parse_args()

def steps(d):
    d = Path(d)
    n = json.loads((d / "cycle.json").read_text())["drawings"]
    f = [np.asarray(Image.open(d / f"dr-{i:03d}.png").convert("L"), np.int16)
         for i in range(n)]
    return ([float(np.abs(f[i + 1] - f[i]).mean()) for i in range(n - 1)],
            float(np.abs(f[0] - f[-1]).mean()))

W, PH, PAD, TOP = 980, 250, 64, 34
img = Image.new("RGB", (W, (PH + TOP + 30) * len(a.pair) + 14), (250, 249, 245))
dr = ImageDraw.Draw(img)
RED, GRN = (176, 42, 42), (26, 106, 62)

for k, (label, before, after) in enumerate(a.pair):
    y0 = 14 + k * (PH + TOP + 30) + TOP
    series = [("before  (1.7 turns of chop per cycle)", steps(before), RED),
              ("after   (2.0 turns = an integer harmonic)", steps(after), GRN)]
    hi = max(max(o) for _, (o, _), _ in series)
    hi = max(hi, max(w for _, (_, w), _ in series)) * 1.18
    dr.rectangle([PAD, y0, W - 20, y0 + PH], outline=(210, 208, 200))
    dr.text((PAD, y0 - TOP + 4), f"{label} - change per drawing; X = the wrap "
            f"(last drawing back to first)", fill=(24, 24, 24))
    for g in range(1, 4):
        gy = y0 + PH - PH * g / 4
        dr.line([PAD, gy, W - 20, gy], fill=(232, 230, 224))
        dr.text((8, gy - 6), f"{hi*g/4:.3f}", fill=(150, 148, 142))
    for si, (tag, (ords, wrap), col) in enumerate(series):
        n = len(ords)
        px = lambda i: PAD + (W - 30 - PAD) * i / n
        py = lambda v: y0 + PH - PH * v / hi
        dr.line([(px(i), py(v)) for i, v in enumerate(ords)], fill=col, width=2)
        wx, wy = px(n), py(wrap)
        dr.line([wx - 7, wy - 7, wx + 7, wy + 7], fill=col, width=3)
        dr.line([wx - 7, wy + 7, wx + 7, wy - 7], fill=col, width=3)
        dr.text((PAD + 8, y0 + 8 + si * 15),
                f"{tag}    wrap / largest ordinary step = {wrap/max(ords):.2f}",
                fill=col)
    dr.text((PAD, y0 + PH + 6), "drawing", fill=(120, 118, 112))

img.save(a.out)
print(a.out)
