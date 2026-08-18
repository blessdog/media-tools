#!/usr/bin/env python3
"""Cut the deer's four legs as separate parts. Job-specific, by hand, on purpose.

WHY BY HAND (measured 2026-08-16). Every automatic route was tried and refused:
SAM returns a FILLED silhouette that swallows the silk between the legs and omits
the two far legs entirely, so the mask has one connected component below the
belly at every cut height. Depth Anything separates the barrel and the antlers
but never four legs -- the far legs are barely painted -- and it INVERTS the near
foreleg (0.325) behind the far flank (0.497), because thin dark strokes on light
silk get pushed back.

What is left is what an animator would have done in 1935: say where each leg is,
and take the ink inside that corridor. A leg here is a stroke pair from a pivot
at the body to a hoof, so two clicked points define it, and Otsu inside the
corridor separates stroke from silk without a global threshold that the changing
silk tone would break.

Legs are numbered by the gait, not by position: a four-beat walk fires
near-hind, near-fore, far-hind, far-fore at quarter-cycle offsets.

  ./cut-legs.py --image pan/deer-native.png --out pan/mask-legs [--width 26]
"""
import argparse, json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

# read off pan/deer-legs-zoom.png at 2x, converted back to deer-native crop px.
# each leg: pivot where it leaves the body, then the hoof.
LEGS = [
    {'name': 'near-hind',  'pivot': (127, 466), 'hoof': (120, 678), 'phase': 0.00},
    {'name': 'near-fore',  'pivot': (172, 463), 'hoof': (185, 663), 'phase': 0.50},
    {'name': 'far-hind',   'pivot': (227, 456), 'hoof': (212, 573), 'phase': 0.25},
    {'name': 'far-fore',   'pivot': (270, 452), 'hoof': (252, 588), 'phase': 0.75},
]

p = argparse.ArgumentParser()
p.add_argument('--image', required=True)
p.add_argument('--out', required=True)
p.add_argument('--width', type=int, default=26, help='corridor width in px around the leg line')
p.add_argument('--feather', type=int, default=1)
p.add_argument('--grow', type=int, default=4,
               help='dilate the ink so the limb carries a margin of its own silk. MUST match '
                    'clean-plate --grow: the plate erases a grown corridor, and a limb cut tight '
                    'to the ink cannot cover that hole, which leaves a pale streak beside every leg')
a = p.parse_args()

rgb = np.asarray(Image.open(a.image).convert('RGB'))
lum = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
H, W = lum.shape
out = Path(a.out); (out / 'masks').mkdir(parents=True, exist_ok=True)

planes, vis = [], rgb.astype(np.float32) * 0.4 + 150
cols = [(214, 62, 40), (36, 108, 190), (28, 150, 78), (176, 128, 24)]

for n, (leg, col) in enumerate(zip(LEGS, cols), start=1):
    corridor = np.zeros((H, W), np.uint8)
    cv2.line(corridor, leg['pivot'], leg['hoof'], 255, a.width)
    cv2.circle(corridor, leg['hoof'], a.width // 2 + 3, 255, -1)   # the hoof is a blob
    sel = corridor > 0
    vals = lum[sel]
    # Otsu inside this corridor only: silk tone drifts across the painting, and a
    # global threshold that works on one leg loses another
    t, _ = cv2.threshold(vals.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink = sel & (lum <= t)
    ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 3), np.uint8))
    # keep only what is connected to the leg's own line, so a rock clipped by the
    # corridor does not travel with the limb
    nlab, lab = cv2.connectedComponents(ink)
    spine = np.zeros((H, W), np.uint8)
    cv2.line(spine, leg['pivot'], leg['hoof'], 1, 3)
    keep = set(np.unique(lab[(spine > 0) & (ink > 0)])) - {0}
    ink = np.isin(lab, list(keep)).astype(np.uint8) * 255
    if a.grow:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (a.grow * 2 + 1,) * 2)
        ink = cv2.dilate(ink, k)
    if a.feather:
        ink = cv2.GaussianBlur(ink, (0, 0), a.feather)

    ys, xs = np.nonzero(ink > 8)
    if len(ys) == 0:
        raise SystemExit(f"{leg['name']}: corridor caught no ink")
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    Image.fromarray(ink[y0:y1, x0:x1]).save(out / 'masks' / f'{n:03d}.png')
    planes.append({'n': n, 'name': leg['name'], 'offset': [int(x0), int(y0)],
                   'pivot': [leg['pivot'][0] - int(x0), leg['pivot'][1] - int(y0)],
                   'pivotAbs': list(leg['pivot']), 'phase': leg['phase'],
                   'lengthPx': int(round(np.hypot(leg['hoof'][0] - leg['pivot'][0],
                                                  leg['hoof'][1] - leg['pivot'][1]))),
                   'inkPx': int((ink > 128).sum()), 'otsu': int(t)})
    m = ink > 60
    vis[m] = np.array(col, np.float32)
    cv2.circle(vis, leg['pivot'], 4, (20, 20, 20), -1)

json.dump({'tool': 'cut-legs', 'image': a.image, 'size': [W, H],
           'note': 'ink inside a hand-placed corridor; pivot is where the limb leaves the body',
           'planeList': planes}, open(out / 'layers.json', 'w'), indent=2)
Image.fromarray(np.clip(vis, 0, 255).astype('uint8')).save(out / 'overlay.png')
print(json.dumps({'out': str(out), 'legs': [(q['name'], q['inkPx'], q['lengthPx'], q['otsu'])
                                            for q in planes]}, indent=2))
