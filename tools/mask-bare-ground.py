#!/usr/bin/env python3
"""Cut a mask of 留白 — unpainted silk — inside a hand-drawn box. One job.

WHY NOT SAM (measured 2026-08-14). Pointed at the river in shot-real.png, SAM
returned the two ROCKS sitting in the river and refused the river itself. That is
not a bug in SAM: it segments objects by their contours, and Wang Meng painted
water as absence — bare silk between drawn things. An absence has no contour.
The same click on the cascade under the bridge swallowed the trestle posts,
because the posts are the only thing there with an edge.

So the mask is defined by the MATERIAL instead. Unpainted silk is the bright,
low-variance ground; ink is dark and locally busy. Threshold on both, inside a
box the operator draws, and the cut follows the painting's own logic.

  ./mask-bare-ground.py --image IN.png --box X0,Y0,X1,Y1 --name NAME --out DIR
    [--vmin 0.62]     keep pixels at least this bright (0..1 of HSV value)
    [--busy 0.055]    reject pixels whose local std dev exceeds this — kills
                      ink dashes, trestle timber, texture. Raise to keep the
                      drawn current lines inside the water; lower for bare silk.
    [--close 5]       morphological close, px: bridges the ink dashes so the
                      current reads as one body of water rather than confetti
    [--feather 6]     blur the edge, px
    [--min-area 200]  drop islands smaller than this, px

Writes DIR/masks/NNN.png (cropped) + appends to DIR/layers.json in the same
shape segment-points.py writes, so composite-protect.py consumes either.
"""
import argparse, json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageFilter

p = argparse.ArgumentParser()
p.add_argument('--image', required=True); p.add_argument('--box', required=True)
p.add_argument('--name', required=True);  p.add_argument('--out', required=True)
p.add_argument('--vmin', type=float, default=0.62)
p.add_argument('--busy', type=float, default=0.055)
p.add_argument('--close', type=int, default=5)
p.add_argument('--feather', type=int, default=6)
p.add_argument('--min-area', type=int, default=200)
a = p.parse_args()

img = np.array(Image.open(a.image).convert('RGB'))
H, W = img.shape[:2]
x0, y0, x1, y1 = (int(v) for v in a.box.split(','))
crop = img[y0:y1, x0:x1]

v = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)[..., 2].astype(np.float32) / 255.0
# local std dev = "is there ink working here"
mean = cv2.blur(v, (9, 9))
busy = np.sqrt(np.maximum(cv2.blur(v * v, (9, 9)) - mean * mean, 0))

m = ((v >= a.vmin) & (busy <= a.busy)).astype(np.uint8) * 255
if a.close:
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (a.close * 2 + 1,) * 2)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
n, lab, stats, _ = cv2.connectedComponentsWithStats((m > 0).astype(np.uint8), 8)
for i in range(1, n):
    if stats[i, cv2.CC_STAT_AREA] < a.min_area:
        m[lab == i] = 0
if a.feather:
    m = np.array(Image.fromarray(m).filter(ImageFilter.GaussianBlur(a.feather)))

out = Path(a.out); (out / 'masks').mkdir(parents=True, exist_ok=True)
lj = out / 'layers.json'
meta = json.load(open(lj)) if lj.exists() else {
    'tool': 'mask-liubai', 'image': a.image, 'size': [W, H], 'planeList': []}
nn = max([q['n'] for q in meta['planeList']], default=0) + 1
Image.fromarray(m).save(out / 'masks' / f'{nn:03d}.png')
meta['planeList'].append({
    'n': nn, 'name': a.name, 'source': 'mask-liubai', 'box': [x0, y0, x1, y1],
    'offset': [x0, y0], 'vmin': a.vmin, 'busy': a.busy,
    'coveragePctOfBox': round(float((m > 127).mean()) * 100, 1),
    'coveragePctOfFrame': round(float((m > 127).sum()) / (W * H) * 100, 2)})
json.dump(meta, open(lj, 'w'), indent=1)
print(json.dumps(meta['planeList'][-1], indent=2))
