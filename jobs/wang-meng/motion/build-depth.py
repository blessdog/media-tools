#!/usr/bin/env python3
"""Compose a depth map for the shot from the two sources that actually work.

Measured 2026-08-16, and the split is the whole point:

  LANDSCAPE  Depth Anything V2 returns a vertical ramp here -- 55% of its
             variance is image row alone, and the cliff, gorge, ledge, river and
             the entire trestle bridge are absent. A Yuan scroll encodes space
             by overlap, contour and 留白, and the model has no prior for a
             layout with no station point. So landscape depth comes from the
             VLM-authored plane stack (layers-v4), where a language model read
             the pictorial convention.

  FIGURES    The same model sculpts Ge Hong correctly: relief 0.0698 against a
             flat-card null of 0, and corr(depth, ink luminance) -0.064, so it
             is completing a shape rather than tracing brushwork. A standing
             robed human is a category it has seen a million times.

Figure relief is added as a small band around the figure's own plane depth: the
figure must not poke through the plane it stands on, it must only stop being
flat. --relief is that band, in the same 0..1 units as the map.

  ./build-depth.py --layers ../layers-v4 --out pan/depth-authored.png
      [--figure pan/depth-native.png --figure-mask M.png --figure-at X,Y]
      [--relief 0.04] [--grade 9]
"""
import argparse, json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# the shot's window on the master, from locate-crop.py
CROP = {'x': 901, 'y': 10604, 'w': 1684, 'h': 2995, 'k': 2.34}

p = argparse.ArgumentParser()
p.add_argument('--layers', required=True, help='dir holding layers.json + masks/')
p.add_argument('--out', required=True)
p.add_argument('--size', default='720,1280', help='output W,H (the shot frame)')
p.add_argument('--space', default='master', choices=['master', 'shot'],
               help='coordinates the plane masks are cut in. The scroll-scale stack is in '
                    'master px and must be mapped down; a stack planned on the shot itself '
                    'is already in shot px and must NOT be')
p.add_argument('--figure', action='append', default=None, help='a DAv2 depth map for one figure')
p.add_argument('--figure-mask', action='append', default=None)
p.add_argument('--figure-at', action='append', default=None, help='x,y of that crop in SHOT px')
p.add_argument('--relief', type=float, default=0.04, help='depth band a figure may occupy')
p.add_argument('--grade', type=int, default=9, help='blur that turns cards into a graded surface')
a = p.parse_args()

W, H = (int(q) for q in a.size.split(','))
k = CROP['k']

meta = json.load(open(Path(a.layers) / 'layers.json'))
planes = meta['planeList']
dmax = max(pl['depth'] for pl in planes)

# rasterise farthest first so nearer planes win, straight into shot pixels
depth = np.full((H, W), np.nan, np.float32)
hits = []
for pl in sorted(planes, key=lambda q: q['depth']):
    mi = np.array(Image.open(Path(a.layers) / 'masks' / f"{pl['n']:03d}.png").convert('L'))
    ox, oy = pl['offset']
    if a.space == 'master':
        sx0, sy0 = (ox - CROP['x']) / k, (oy - CROP['y']) / k
        sw, sh = mi.shape[1] / k, mi.shape[0] / k
    else:
        sx0, sy0 = float(ox), float(oy)
        sw, sh = float(mi.shape[1]), float(mi.shape[0])
    if sx0 + sw < 0 or sy0 + sh < 0 or sx0 > W or sy0 > H:
        continue
    small = cv2.resize(mi, (max(1, int(round(sw))), max(1, int(round(sh)))), interpolation=cv2.INTER_AREA)
    x0, y0 = int(round(sx0)), int(round(sy0))
    xs0, ys0 = max(0, x0), max(0, y0)
    xs1, ys1 = min(W, x0 + small.shape[1]), min(H, y0 + small.shape[0])
    if xs1 <= xs0 or ys1 <= ys0:
        continue
    sub = small[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    sel = sub > 96
    if not sel.any():
        continue
    depth[ys0:ys1, xs0:xs1][sel] = pl['depth'] / dmax
    hits.append((pl['name'], pl['depth'], int(sel.sum())))

claimed = ~np.isnan(depth)
print(json.dumps({'planesInShot': hits, 'coverage': round(float(claimed.mean()), 4)}, indent=2))
if not claimed.any():
    raise SystemExit('no plane from this stack overlaps the shot window')

# fill the unclaimed silk from the nearest claimed pixel, so there are no holes
# for a displacement to tear open
idx = cv2.distanceTransformWithLabels((~claimed).astype(np.uint8), cv2.DIST_L2, 5,
                                      labelType=cv2.DIST_LABEL_PIXEL)[1]
ys, xs = np.nonzero(claimed)
order = np.zeros(idx.max() + 1, np.int64)
order[idx[claimed]] = np.arange(len(ys))
flat = depth[claimed]
depth = flat[order[idx]].reshape(H, W)

# grade the cards: a hard plane edge IS the flat-card look, and blurring is what
# turns a stack of cutouts into a surface. Too much and real occlusion edges
# become rubber sheet, so this is the knob to A/B.
graded = cv2.GaussianBlur(depth, (0, 0), a.grade) if a.grade else depth

for fpath, fmask, fat in zip(a.figure or [], a.figure_mask or [], a.figure_at or []):
    fd = np.asarray(Image.open(fpath)).astype(np.float32)
    fd = (fd - fd.min()) / (fd.max() - fd.min())
    fm = np.asarray(Image.open(fmask).convert('L'), np.float32) / 255
    fx, fy = (float(q) for q in fat.split(','))
    tw, th = int(round(fd.shape[1] / k)), int(round(fd.shape[0] / k))
    fd = cv2.resize(fd, (tw, th), interpolation=cv2.INTER_AREA)
    fm = cv2.resize(fm, (tw, th), interpolation=cv2.INTER_AREA)
    x0, y0 = int(round(fx)), int(round(fy))
    xs0, ys0 = max(0, x0), max(0, y0)
    xs1, ys1 = min(W, x0 + tw), min(H, y0 + th)
    sub_d = fd[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    sub_m = fm[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
    inside = sub_m > 0.5
    if not inside.any():
        continue
    # centre the figure's own relief on the plane it stands on, then scale it
    # into the allowed band. It gains volume; it does not leave its ground.
    rel = sub_d - sub_d[inside].mean()
    span = max(np.abs(rel[inside]).max(), 1e-6)
    rel = rel / span * a.relief
    base = graded[ys0:ys1, xs0:xs1]
    graded[ys0:ys1, xs0:xs1] = np.where(inside, base + rel, base)
    print(f'  figure {Path(fpath).name}: {int(inside.sum())} px at shot ({x0},{y0}), '
          f'relief band +-{a.relief}')

out = np.clip(graded, 0, 1)
Image.fromarray((out * 65535).astype(np.uint16)).save(a.out)
print(json.dumps({'out': a.out, 'size': [W, H], 'range': [round(float(out.min()), 4),
                  round(float(out.max()), 4)], 'grade': a.grade,
                  'note': 'near = white, normalised, the convention DepthFlow expects'}, indent=2))
