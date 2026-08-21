#!/usr/bin/env python3
"""Paste per-tile masks back into ONE mask in master-image pixels.

    composite-tile-masks.py --tiles tiles.json --masks DIR --out foliage-master.png
                            [--suffix -trees.png] [--feather 2]

A very large painting is segmented tile by tile because the models can only read
a tile. This is the inverse of tile-image.py: each tile mask is scaled back to
its sourceBox and OR-ed into a master canvas.

Tiles OVERLAP, and that is a feature here -- a leaf near a seam is usually found
from at least one side, so the union recovers what a single tile clipped. It is
also why the result must be judged as a whole: a mask can be right in every tile
and wrong at every join.

WHAT THIS IS NOT FOR: deciding what a thing is (a VLM catalogue) or finding the
exact edge (refine-mask-sam.py). This only moves masks between coordinate
spaces.
"""
import argparse, json
from pathlib import Path
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
p = argparse.ArgumentParser()
p.add_argument('--tiles', required=True)
p.add_argument('--masks', required=True, help='dir holding <tilestem><suffix>')
p.add_argument('--suffix', default='-trees.png')
p.add_argument('--out', required=True)
p.add_argument('--out-size', nargs=2, type=int, metavar=('W', 'H'),
               help='master canvas size; defaults to tiles.json sourceSize')
a = p.parse_args()

t = json.loads(Path(a.tiles).read_text())
W, H = a.out_size if a.out_size else t['sourceSize']
canvas = np.zeros((H, W), bool)
md = Path(a.masks)
found, missing = 0, []
for tile in t['tiles']:
    stem = Path(tile['file']).stem
    f = md / f'{stem}{a.suffix}'
    if not f.exists():
        missing.append(stem); continue
    x0, y0, x1, y1 = tile['sourceBox']
    m = Image.open(f).convert('L').resize((x1 - x0, y1 - y0), Image.NEAREST)
    canvas[y0:y1, x0:x1] |= np.array(m) > 127
    found += 1
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Image.fromarray((canvas * 255).astype(np.uint8)).save(a.out)
print(json.dumps({'out': a.out, 'tiles': found, 'missing': missing,
                  'size': [W, H], 'maskPx': int(canvas.sum()),
                  'coverage': round(float(canvas.mean()), 4)}, indent=1))
