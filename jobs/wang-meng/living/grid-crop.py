#!/usr/bin/env python3
"""Gridded master crop for authoring water/foliage polygons by eye.

Polygons for the living layer cannot be cut by material: mask-bare-ground
looks for bright low-variance silk, and above the bridge the CLIFF is bright
low-variance silk too (evidence: living/native/w-midstream/mask-overlay.png —
blue confetti over dry rock). What separates water there is pictorial, not
photometric, so the boundary gets authored by eye against a labelled grid, the
same loop the 31 stations were authored with.

  grid-crop.py --box x0,y0,x1,y1 [--step 100] [--out P.png] [--poly poly.json]
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
R = json.loads((HERE / "regions.json").read_text())

ap = argparse.ArgumentParser()
ap.add_argument("--box", required=True, help="master px x0,y0,x1,y1")
ap.add_argument("--step", type=int, default=100, help="grid step in MASTER px")
ap.add_argument("--scale", type=float, default=None, help="output px per master px")
ap.add_argument("--out", default=None)
ap.add_argument("--poly", default=None, help="overlay polygons from this json")
ap.add_argument("--id", default=None, help="with --poly: only this id")
a = ap.parse_args()

x0, y0, x1, y1 = [int(v) for v in a.box.split(",")]
img = Image.open(ROOT / R["master"]).convert("RGB").crop((x0, y0, x1, y1))
s = a.scale or min(1.0, 1500 / max(img.size))
img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
d = ImageDraw.Draw(img, "RGBA")

if a.poly:
    polys = json.loads(Path(a.poly).read_text())["polys"]
    for p in polys:
        if a.id and p["id"] != a.id:
            continue
        pts = [((mx - x0) * s, (my - y0) * s) for mx, my in p["points"]]
        col = (30, 90, 200, 110) if p["class"] in ("wave", "fall") else (200, 90, 30, 110)
        d.polygon(pts, fill=col, outline=(255, 255, 0, 255))

for gx in range(x0 - x0 % a.step + a.step, x1, a.step):
    X = (gx - x0) * s
    d.line([(X, 0), (X, img.height)], fill=(255, 0, 0, 90), width=1)
    d.text((X + 2, 2), str(gx), fill=(255, 0, 0, 255))
for gy in range(y0 - y0 % a.step + a.step, y1, a.step):
    Y = (gy - y0) * s
    d.line([(0, Y), (img.width, Y)], fill=(255, 0, 0, 90), width=1)
    d.text((2, Y + 2), str(gy), fill=(255, 0, 0, 255))

out = a.out or str(HERE / "_grid.png")
img.save(out)
print(json.dumps({"out": out, "box": [x0, y0, x1, y1], "scale": round(s, 4),
                  "size": list(img.size)}))
