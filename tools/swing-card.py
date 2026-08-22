#!/usr/bin/env python3
"""media-tools — swing-card: rotate AUTHORED cards on a gust envelope. One job.

Given masks somebody has already decided are the moving parts, swing each one
rigidly about its own pivot and write a loop. Nothing is cut here and nothing is
deformed: a card is a rigid transform of ink Wang Meng already painted
(knowledge/rigid-cards-preserve-the-brushwork.md).

WHAT THIS IS NOT FOR, AND WHAT IS:

  hinge-foliage.py   a CANOPY. Its job includes DECIDING the decomposition --
                     cutting one card per ink cluster and finding where each
                     joins a branch. That judgement is the hard part of foliage
                     and belongs to the tool that swings them. Use it for
                     leaves; never hand it authored cards.
  walk-figure.py     a figure that TRAVELS. It starts every frame from the clean
                     plate and repaints the whole body from its cels, which is
                     right for a walk and wrong for a standing figure: any part
                     whose mask is missing or wrong is DELETED before anything
                     moves. Measured 2026-08-21 on Ge Hong -- three of his four
                     puppet masks did not match their names.
  animate-strokes.py thin marks quivering in place with no pivot. That is water.

  swing-card.py      one authored part, hinged, over the painting left standing.
                     A fan on a wrist. A sleeve on a shoulder. A signboard.

THE BASE IS THE SOURCE, NOT THE PLATE. Every pixel outside a card's own rest
footprint is left exactly as painted, so a wrong or missing mask can only fail
to move something -- it can never erase it. The clean plate is sampled ONLY
where a card can vacate. This is the fix that hinge-foliage learned the hard way
on 2026-08-20, when starting from the plate deleted 54% of a pine.

THE ENVELOPE is hinge-foliage's, unchanged: attack -> hold -> decay -> calm,
zero at both ends so the loop closes, and a rest floor so nothing is ever
perfectly still. Ryan's brief: not constant motion -- little gusts blow through.

usage:
  swing-card.py --source IMG --masks DIR --pivots P.json --out DIR
      [--only NAME] [--plate CLEAN.png] [--swing 5] [--gust 0.10,0.08,0.22]
      [--gust-rest 0.15] [--frames 96] [--on 2] [--feather 2]

example:
  swing-card.py --source jobs/wang-meng/motion/gehong-hi.png \\
      --masks jobs/wang-meng/motion/mask/gehong \\
      --pivots jobs/wang-meng/motion/mask/gehong/pivots.json \\
      --only fan --swing 5 --out jobs/wang-meng/living/cycles/g-ge-fan

JSON on stdout. Progress on stderr.
"""
import argparse, json, sys, zlib
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

p = argparse.ArgumentParser()
p.add_argument('--source', required=True, help='the painting, with the parts still in it')
p.add_argument('--masks', required=True, help='dir with layers.json + masks/NNN.png')
p.add_argument('--pivots', required=True, help='{"<name>": {"pivot": [x, y]}} in SOURCE px')
p.add_argument('--only', default=None, help='swing just this named part')
p.add_argument('--plate', default=None,
               help='clean plate for what a card uncovers. Without it the card '
                    'rotates over its own old ink, which reads as a smear at the '
                    'trailing edge -- fine for a probe, not for a deliverable.')
p.add_argument('--swing', type=float, default=5.0, help='degrees at full gust')
p.add_argument('--gust', default='0.10,0.08,0.22', help='attack,hold,decay as fractions of the loop')
p.add_argument('--gust-rest', type=float, default=0.15, help='floor so nothing is ever dead still')
p.add_argument('--frames', type=int, default=96)
p.add_argument('--on', type=int, default=2, help='hold each drawing this many frames')
p.add_argument('--feather', type=int, default=2)
p.add_argument('--prefix', default='',
               help="filename prefix for the drawings; the living-layer builder "
                    "reads dr-%%03d.png, so pass --prefix dr- when feeding it")
p.add_argument('--out', required=True)
a = p.parse_args()

src = np.array(Image.open(a.source).convert('RGB'), np.float32)
H, W = src.shape[:2]
plate = np.array(Image.open(a.plate).convert('RGB'), np.float32) if a.plate else None
if plate is not None and plate.shape[:2] != (H, W):
    sys.exit(f'--plate is {plate.shape[1]}x{plate.shape[0]}, --source is {W}x{H}')

meta = json.loads((Path(a.masks) / 'layers.json').read_text())
piv = json.loads(Path(a.pivots).read_text())

ga, gh, gd = (float(q) for q in a.gust.split(','))
if ga + gh + gd >= 0.95:
    sys.exit('--gust A+H+D must leave calm air in the loop: keep the sum under 0.95')


def envelope(u):
    """attack -> hold -> decay -> calm, zero at both ends so the loop closes."""
    u = u % 1.0
    if u < ga:
        return 0.5 - 0.5 * np.cos(np.pi * u / ga)
    if u < ga + gh:
        return 1.0
    if u < ga + gh + gd:
        return 0.5 + 0.5 * np.cos(np.pi * (u - ga - gh) / gd)
    return 0.0


cards = []
for pl in meta['planeList']:
    name = pl['name']
    if a.only and name != a.only:
        continue
    if name not in piv:
        print(f'  skip {name}: no pivot authored', file=sys.stderr)
        continue
    ox, oy = pl['offset']
    m = np.asarray(Image.open(Path(a.masks) / 'masks' / f"{pl['n']:03d}.png").convert('L'))
    full = np.zeros((H, W), np.uint8)
    full[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
    solid = (full > 128)
    if not solid.any():
        print(f'  skip {name}: empty mask', file=sys.stderr)
        continue
    al = cv2.GaussianBlur(solid.astype(np.float32), (0, 0), a.feather) if a.feather else solid.astype(np.float32)
    pvx, pvy = piv[name]['pivot']
    ys, xs = np.nonzero(solid)
    length = float(np.hypot(np.abs(xs - pvx).max(), np.abs(ys - pvy).max()))
    pad = int(length * np.deg2rad(abs(a.swing)) + 8)
    x0, y0 = max(0, int(min(xs.min(), pvx)) - pad), max(0, int(min(ys.min(), pvy)) - pad)
    x1, y1 = min(W, int(max(xs.max(), pvx)) + pad + 1), min(H, int(max(ys.max(), pvy)) + pad + 1)
    cards.append({
        'name': name, 'box': (x0, y0, x1, y1),
        'pivot': (float(pvx - x0), float(pvy - y0)),
        'rgb': src[y0:y1, x0:x1].copy(),
        'al': al[y0:y1, x0:x1].copy(),
        'solid': solid[y0:y1, x0:x1].copy(),
        'lengthPx': length,
        # crc32, not hash(): str hash is salted per process, so the same flags
        # gave a different gust phase on every run (hinge-foliage, 2026-08-20).
        'seed': zlib.crc32(name.encode()) % 1000 / 1000.0,
    })
if not cards:
    sys.exit('no cards: check --only and that --pivots names match layers.json')

# WHERE A CARD CAN VACATE, and nowhere else. Everything outside this stands as
# painted, so a wrong mask can fail to move something but can never delete it.
vacate = np.zeros((H, W), bool)
for c in cards:
    x0, y0, x1, y1 = c['box']
    vacate[y0:y1, x0:x1] |= c['solid']
if plate is None:
    print('  no --plate: cards rotate over their own ink (probe quality)', file=sys.stderr)

out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
peak_d = 0
n_draw = max(1, a.frames // max(a.on, 1))
maxdeg = 0.0
for d in range(n_draw):
    u = d / n_draw
    frame = src.copy()
    if plate is not None:
        frame[vacate] = plate[vacate]
    for c in cards:
        ang = a.swing * (a.gust_rest + (1 - a.gust_rest) * envelope(u))
        if abs(ang) > maxdeg:
            maxdeg, peak_d = abs(ang), d
        x0, y0, x1, y1 = c['box']
        M = cv2.getRotationMatrix2D(c['pivot'], float(ang), 1.0)
        bw, bh = x1 - x0, y1 - y0
        rgb = cv2.warpAffine(c['rgb'], M, (bw, bh), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        alf = cv2.warpAffine(c['al'], M, (bw, bh), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=0)[..., None]
        frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - alf) + rgb * alf
    Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(out / f'{a.prefix}{d:03d}.png')

# LOOP SEAM: the last drawing must flow into the first, or the cycle ticks.
f0 = np.asarray(Image.open(out / f'{a.prefix}000.png'), np.float32)
fl = np.asarray(Image.open(out / f'{a.prefix}{n_draw - 1:03d}.png'), np.float32)
seam = float(np.abs(f0 - fl).mean())
# MEASURE AT THE PEAK DRAWING, not at the midpoint. The gust peaks around
# u = attack+hold (~0.14 of the loop), and the midpoint sits in the calm air
# where the angle equals frame 0's -- comparing there reported 0.00% moved on a
# cycle that was working perfectly.
fp = np.asarray(Image.open(out / f'{a.prefix}{peak_d:03d}.png'), np.float32)
moved = float((np.abs(f0 - fp).sum(2) > 6).mean() * 100)

(out / 'cycle.json').write_text(json.dumps({
    'tool': 'swing-card', 'source': a.source, 'masks': a.masks,
    'cards': [{'name': c['name'], 'box': list(c['box']), 'lengthPx': round(c['lengthPx'], 1),
               'pivot': [round(v, 1) for v in c['pivot']]} for c in cards],
    'swingDeg': a.swing, 'gust': a.gust, 'gustRest': a.gust_rest,
    'drawings': n_draw, 'on': a.on, 'plate': a.plate,
    'loopSeamLevels': round(seam, 3), 'movedPctAtPeak': round(moved, 2),
 'peakDrawing': peak_d,
}, indent=1))
print(json.dumps({'tool': 'swing-card', 'out': str(out), 'drawings': n_draw, 'on': a.on,
                  'cards': [c['name'] for c in cards], 'maxDeg': round(maxdeg, 2),
                  'loopSeamLevels': round(seam, 3), 'movedPctAtPeak': round(moved, 2),
                  'peakDrawing': peak_d}, indent=1))
