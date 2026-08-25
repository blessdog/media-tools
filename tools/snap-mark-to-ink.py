#!/usr/bin/env python3
"""Tighten a hand-drawn loop onto the ink it encloses. One job.

    snap-mark-to-ink.py --marks jobs/wang-meng/marks/z3w-polys.json \
        --image corpus/grabs/wang-meng.png \
        --foliage jobs/wang-meng/catalogue/foliage-master-z3w.png \
        --out jobs/wang-meng/marks/z3w-snapped.json [--sheet before-after.png]

A hand loop says WHICH marks are one thing -- the judgement that is not in the
pixels (knowledge/no-whole-tree-to-segment.md). It should never become the
OUTLINE: a crayon line over precise brushwork throws away the cut this repo
already paid for. So the loop SELECTS and the ink's own edge DEFINES.

    in   a sloppy loop, hundreds of jittery points, drawn in seconds
    out  the precise boundary of the painted marks inside it

WHAT THIS IS NOT FOR: deciding WHICH ink is one bushel. That is the loop's job
and it is human. This only answers "given that these marks are one thing, where
exactly do they end", which is a measurement and belongs to the machine.
Also not a segmenter: it never proposes a region, it only tightens one.
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

p = argparse.ArgumentParser(prog='snap-mark-to-ink.py')
p.add_argument('--marks', required=True, help='polys in MASTER px, from blender-read-marks')
p.add_argument('--image', required=True, help='the master painting')
p.add_argument('--foliage', help='authored foliage mask at master size; limits the snap to real foliage territory')
p.add_argument('--out', required=True)
p.add_argument('--sheet', help='before/after PNG so the snap can be judged by eye')
p.add_argument('--ink-delta', type=int, default=18,
               help='how much darker than local paper counts as a mark')
p.add_argument('--min-px', type=int, default=40, help='ignore specks smaller than this')
p.add_argument('--bind', type=int, default=9,
               help='morphological close radius: binds a spray of separate marks into one bushel')
p.add_argument('--keep-frac', type=float, default=0.5,
               help='a component joins the bushel when this fraction of it is inside the loop')
a = p.parse_args()

marks = json.loads(Path(a.marks).read_text())
img = np.array(Image.open(a.image).convert('RGB'))
H, W = img.shape[:2]
foliage = None
if a.foliage:
    foliage = np.array(Image.open(a.foliage).convert('L')) > 0
    if foliage.shape != (H, W):
        sys.exit(f'foliage mask {foliage.shape} != image {(H, W)}')

sheet = None
if a.sheet:
    sheet = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2BGR)

out = []
for poly in marks.get('polys', []):
    pts = np.array(poly['points'], np.int32)
    x0, y0 = np.clip(pts.min(0) - a.bind * 3, 0, [W, H])
    x1, y1 = np.clip(pts.max(0) + a.bind * 3, 0, [W, H])
    if x1 - x0 < 3 or y1 - y0 < 3:
        continue
    sub = img[y0:y1, x0:x1]

    loop = np.zeros(sub.shape[:2], np.uint8)
    cv2.fillPoly(loop, [pts - [x0, y0]], 1)

    grey = cv2.cvtColor(sub, cv2.COLOR_RGB2GRAY)
    # Local paper tone, not a global threshold: the silk darkens across the
    # scroll and a fixed cut would take the whole bottom of the painting.
    paper = cv2.medianBlur(grey, 31)
    ink = (paper.astype(np.int16) - grey.astype(np.int16)) > a.ink_delta
    if foliage is not None:
        ink &= foliage[y0:y1, x0:x1]

    n, lab, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    keep = np.zeros_like(ink)
    kept = 0
    for i in range(1, n):
        if st[i, 4] < a.min_px:
            continue
        comp = lab == i
        # A component counts as SELECTED by majority, so a spray clipped by a
        # hasty loop still joins instead of being sliced down the middle.
        if (comp & (loop > 0)).sum() >= a.keep_frac * comp.sum():
            keep |= comp
            kept += 1
    if not keep.any():
        continue

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.bind + 1,) * 2)
    bound = cv2.morphologyEx(keep.astype(np.uint8), cv2.MORPH_CLOSE, k)
    cnts, _ = cv2.findContours(bound, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        continue
    big = max(cnts, key=cv2.contourArea)
    eps = 0.002 * cv2.arcLength(big, True)
    tight = cv2.approxPolyDP(big, eps, True).reshape(-1, 2) + [x0, y0]

    snapped = dict(poly)
    snapped['points'] = [[int(x), int(y)] for x, y in tight]
    snapped['drawnPoints'] = len(poly['points'])
    snapped['inkPx'] = int(keep.sum())
    snapped['marksBound'] = kept
    out.append(snapped)

    if sheet is not None:
        cv2.polylines(sheet, [pts], True, (60, 60, 255), 6, cv2.LINE_AA)      # drawn: red
        cv2.polylines(sheet, [tight.astype(np.int32)], True, (60, 220, 60), 6, cv2.LINE_AA)  # snapped: green
        for pv in poly.get('pivots', []):
            cv2.circle(sheet, tuple(pv), 14, (0, 215, 255), -1, cv2.LINE_AA)

Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text(json.dumps(
    {'note': 'loops tightened onto their own ink by snap-mark-to-ink.py; '
             'the drawn line selects, the ink defines the boundary',
     'source': a.marks, 'polys': out}, indent=1, ensure_ascii=False))

if sheet is not None:
    xs = [q[0] for pl in out for q in pl['points']]
    ys = [q[1] for pl in out for q in pl['points']]
    if xs:
        m = 320
        cx0, cy0 = max(0, min(xs) - m), max(0, min(ys) - m)
        cx1, cy1 = min(W, max(xs) + m), min(H, max(ys) + m)
        crop = sheet[cy0:cy1, cx0:cx1]
        s = min(1.0, 1500 / max(crop.shape[:2]))
        if s < 1.0:
            crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        Path(a.sheet).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(a.sheet, crop)

print(json.dumps({'out': a.out, 'snapped': len(out),
                  'drawnPoints': [p['drawnPoints'] for p in out],
                  'snappedPoints': [len(p['points']) for p in out],
                  'marksBound': [p['marksBound'] for p in out],
                  'sheet': a.sheet}, indent=1))
