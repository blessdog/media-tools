#!/usr/bin/env python3
"""media-tools — compose-depth: labelled planes (+ per-object relief) → one depth
map. One job.

It assembles a depth map. It does not estimate depth (estimate-depth), cut planes
(segment-points), or render a camera move (render-parallax, probe-parallax).

WHY ASSEMBLE ONE AT ALL, when a model will hand you a depth map for free:

Measured 2026-08-16, and the split is the whole point:

  LANDSCAPE  Depth Anything V2 returns a vertical ramp here -- 55% of its
             variance is image row alone, and the cliff, gorge, ledge, river and
             the entire trestle bridge are absent. A Yuan scroll encodes space
             by overlap, contour and 留白, and the model has no prior for a
             layout with no station point. So landscape depth comes from the
             VLM-authored plane stack (plan-planes → segment-points), where a
             language model read the pictorial convention.

             PLAN THE PLANES AT SHOT SCALE. A stack authored for a whole scroll
             has scroll-sized planes, and one frame sits INSIDE one or two of
             them: measured 3 planes in shot, 69.6% of pixels on a single plane,
             depth σ 0.098. Re-planned on the shot itself: 13 planes, σ 0.394.
             It encodes depth BETWEEN shots, not within one.

  FIGURES    The same model sculpts Ge Hong correctly: relief 0.0698 against a
             flat-card null of 0, and corr(depth, ink luminance) -0.064, so it
             is completing a shape rather than tracing brushwork. A standing
             robed human is a category it has seen a million times.

Figure relief is added as a small band around the figure's own plane depth: the
figure must not poke through the plane it stands on, it must only stop being
flat. --relief is that band, in the same 0..1 units as the map.

DO NOT EXPECT A GRADE TO ESCAPE THE CARDS. --grade blurs plane boundaries, and it
is worth having, but it only feathers seams: measured across 13 planes, every
plane INTERIOR stayed 0.0% from its nominal depth. Under a push, a graded stack
and explicit 3-level cards uncovered the same area (25.5% vs 25.0%) and looked
identical -- and against a FAIR constant-depth null of 24.8% that is under one
point of real disocclusion either way, i.e. the parallax is barely doing
anything. A card with a soft edge is still a card. Relief inside a region has to come from somewhere else — which is
what --figure is for. Verify with probe-parallax before believing otherwise.

usage:
  compose-depth.py --planes DIR --out DEPTH.png [--size W,H]
      [--space master|shot] [--crop crop.json]
      [--figure D.png --figure-mask M.png --figure-at X,Y] ...
      [--relief 0.04] [--grade 9]

  --planes DIR   layers.json + masks/, each plane carrying an integer `depth`
  --space        coordinates the plane masks are cut in. `shot` (default) means
                 they were cut on the output frame itself. `master` means they
                 came off the full-resolution source and must be mapped down,
                 which requires --crop
  --crop PATH    crop.json from locate-crop; required when --space master
  --figure*      repeatable triples: a depth map, its mask, and where its crop
                 sits in output px. Its relief is centred on whatever plane it
                 stands on, so it gains volume without leaving the ground
  --relief F     depth band a figure may occupy (default 0.04)
  --grade N      blur sigma over plane boundaries (default 9; 0 = hard cards)

example:
  compose-depth.py --planes jobs/x/layers-shot --out jobs/x/depth.png \
      --figure fig-depth.png --figure-mask fig-mask.png --figure-at 137,613
"""
import argparse, json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

p = argparse.ArgumentParser()
p.add_argument('--planes', '--layers', dest='planes', required=True,
               help='dir holding layers.json + masks/')
p.add_argument('--out', required=True)
p.add_argument('--size', default='720,1280', help='output W,H (the frame)')
p.add_argument('--space', default='shot', choices=['master', 'shot'],
               help='coordinates the plane masks are cut in')
p.add_argument('--crop', default=None, help='crop.json from locate-crop; required for --space master')
p.add_argument('--figure', action='append', default=None, help='a DAv2 depth map for one figure')
p.add_argument('--figure-mask', action='append', default=None)
p.add_argument('--figure-at', action='append', default=None, help='x,y of that crop in SHOT px')
p.add_argument('--relief', type=float, default=0.04, help='depth band a figure may occupy')
p.add_argument('--grade', type=int, default=9, help='blur that turns cards into a graded surface')
a = p.parse_args()

W, H = (int(q) for q in a.size.split(','))

# the master<->frame transform is read, never carried. A transform duplicated in
# two files is a transform that will disagree with itself.
if a.space == 'master':
    if not a.crop:
        raise SystemExit('--space master needs --crop crop.json (write one with locate-crop)')
    C = json.load(open(a.crop))['crop']
    k = C['masterPxPerShotPx']
else:
    C, k = {'x': 0, 'y': 0}, 1.0

# A figure's depth map is cut at the SOURCE's resolution whichever space the
# planes live in, so it is scaled by the master->frame factor, never by k. These
# two were the same number while planes were always master-space; they are not
# the same number, and conflating them silently pastes the figure 2.3x too big.
if a.figure:
    if not a.crop:
        raise SystemExit('--figure needs --crop crop.json: a figure crop is at master '
                         'resolution and must be scaled to the frame')
    fk = json.load(open(a.crop))['crop']['masterPxPerShotPx']
else:
    fk = 1.0

meta = json.load(open(Path(a.planes) / 'layers.json'))
planes = meta['planeList']
dmax = max(pl['depth'] for pl in planes)

# rasterise farthest first so nearer planes win, straight into shot pixels
depth = np.full((H, W), np.nan, np.float32)
hits = []
for pl in sorted(planes, key=lambda q: q['depth']):
    mi = np.array(Image.open(Path(a.planes) / 'masks' / f"{pl['n']:03d}.png").convert('L'))
    ox, oy = pl['offset']
    if a.space == 'master':
        sx0, sy0 = (ox - C['x']) / k, (oy - C['y']) / k
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
    tw, th = int(round(fd.shape[1] / fk)), int(round(fd.shape[0] / fk))
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
