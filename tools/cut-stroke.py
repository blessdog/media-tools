#!/usr/bin/env python3
"""media-tools — cut-stroke: paths → a mask of the painted stroke along each. One job.

It cuts masks. It does not animate, hinge, composite or render — a stroke that
starts swinging is a rig, and that is walk-figure's business.

WHAT THIS IS FOR. Some painted things are STROKES: long, thin, drawn in one or
two passes, and separated from their neighbours by bare ground. A limb, a
branch, a rope, a bridge rail, a mast, a whisker, a falling ribbon of water. You
cannot cut them the ways the other maskers work:

  segment-points   SAM returns a FILLED silhouette. Pointed at a pack-animal it
                   swallowed the silk between the legs and omitted the two far
                   legs entirely — one connected component at every cut height,
                   so there was nothing to separate.
  segment-regions  automatic sampling gives objects, never parts of one.
  estimate-depth   separated the barrel and the antlers but never four legs, and
                   INVERTED the near foreleg (0.325) behind the far flank
                   (0.497), because thin dark strokes on light ground get pushed
                   back. Measured 2026-08-16.
  mask-bare-ground cuts by material, which is the opposite problem.

So you say where the stroke runs — two points — and this takes the ink inside
that corridor. Otsu is computed INSIDE each corridor, never globally, because
ground tone drifts across a painting and one threshold loses half the strokes.
Only ink connected to the corridor's own spine is kept, so a rock clipped by the
corridor does not come with it.

--grow MUST MATCH clean-plate's --grow when the stroke is going to move. The
plate erases a grown corridor; a stroke cut tight to its own ink cannot cover
that hole, and every one leaves a pale streak beside it. Measured: matching the
two took a frozen-limb round-trip from 2.17 to 2.11 /255.

Every extra key in a path object is copied into the plane, so a rig can carry
`phase`, `behind`, or anything else through this tool without it knowing what
they mean. `from` is recorded as the plane's `pivot`: it is the anchored end.

usage:
  cut-stroke.py --image IN --paths paths.json --out DIR
                [--width N] [--grow N] [--feather N]

  --image PATH   the painting
  --paths PATH   {"paths":[{"name","from":[x,y],"to":[x,y],"width"?,...}]}
                 from = the anchored end (a limb's hip, a branch's trunk)
  --out DIR      masks/NNN.png + layers.json + overlay.png land here
  --width N      corridor width in px, default 26; a path may override its own
  --grow N       dilate the ink so the stroke carries a margin of its own ground
                 (default 4 — match clean-plate)
  --feather N    soften the mask edge (default 1)

example:
  cut-stroke.py --image deer.png --paths legs.json --out mask-legs --grow 4
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

COLS = [(214, 62, 40), (36, 108, 190), (28, 150, 78), (176, 128, 24),
        (150, 70, 180), (30, 160, 160), (200, 90, 140), (110, 110, 40)]


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument('--image', required=True)
    p.add_argument('--paths', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--width', type=int, default=26)
    p.add_argument('--grow', type=int, default=4)
    p.add_argument('--feather', type=int, default=1)
    a = p.parse_args()

    rgb = np.asarray(Image.open(a.image).convert('RGB'))
    lum = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    H, W = lum.shape
    spec = json.load(open(a.paths))
    paths = spec['paths'] if isinstance(spec, dict) else spec

    out = Path(a.out)
    (out / 'masks').mkdir(parents=True, exist_ok=True)
    planes, vis = [], rgb.astype(np.float32) * 0.4 + 150

    for n, path in enumerate(paths, start=1):
        frm = tuple(int(q) for q in path['from'])
        to = tuple(int(q) for q in path['to'])
        width = int(path.get('width', a.width))

        corridor = np.zeros((H, W), np.uint8)
        cv2.line(corridor, frm, to, 255, width)
        cv2.circle(corridor, to, width // 2 + 3, 255, -1)      # the far end is often a blob
        sel = corridor > 0
        if not sel.any():
            sys.exit(f"{path.get('name', n)}: corridor falls outside the image")

        # Otsu inside THIS corridor only
        t, _ = cv2.threshold(lum[sel].reshape(-1, 1), 0, 255,
                             cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        ink = (sel & (lum <= t)).astype(np.uint8)
        ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((5, 3), np.uint8))

        # keep only ink touching the path's own spine
        nlab, lab = cv2.connectedComponents(ink)
        spine = np.zeros((H, W), np.uint8)
        cv2.line(spine, frm, to, 1, 3)
        keep = sorted(set(np.unique(lab[(spine > 0) & (ink > 0)]).tolist()) - {0})
        if not keep:
            sys.exit(f"{path.get('name', n)}: corridor caught no ink on its spine")
        ink = np.isin(lab, keep).astype(np.uint8) * 255

        if a.grow:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (a.grow * 2 + 1,) * 2)
            ink = cv2.dilate(ink, k)
        if a.feather:
            ink = cv2.GaussianBlur(ink, (0, 0), a.feather)

        ys, xs = np.nonzero(ink > 8)
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        Image.fromarray(ink[y0:y1, x0:x1]).save(out / 'masks' / f'{n:03d}.png')

        plane = {k: v for k, v in path.items() if k not in ('from', 'to', 'width')}
        plane.update({'n': n, 'name': path.get('name', f'stroke-{n}'),
                      'offset': [x0, y0],
                      'pivot': [frm[0] - x0, frm[1] - y0], 'pivotAbs': list(frm),
                      'lengthPx': int(round(float(np.hypot(to[0] - frm[0], to[1] - frm[1])))),
                      'inkPx': int((ink > 128).sum()), 'otsu': int(t), 'corridorWidth': width})
        planes.append(plane)
        vis[ink > 60] = np.array(COLS[(n - 1) % len(COLS)], np.float32)
        cv2.circle(vis, frm, 4, (20, 20, 20), -1)

    json.dump({'tool': 'cut-stroke', 'image': a.image, 'size': [W, H],
               'grow': a.grow, 'feather': a.feather,
               'note': 'ink inside a stated corridor; pivot is the anchored end of the path',
               'planeList': planes}, open(out / 'layers.json', 'w'), indent=2)
    Image.fromarray(np.clip(vis, 0, 255).astype('uint8')).save(out / 'overlay.png')
    print(json.dumps({'out': str(out), 'strokes': len(planes),
                      'cut': [{'name': q['name'], 'inkPx': q['inkPx'],
                               'lengthPx': q['lengthPx'], 'otsu': q['otsu']} for q in planes],
                      'overlay': str(out / 'overlay.png')}, indent=2))


if __name__ == '__main__':
    main()
