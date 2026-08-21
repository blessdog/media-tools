#!/usr/bin/env python3
"""Cut a very large image into overlapping tiles a vision model can read.

    tile-image.py --image master.png --out DIR --tile 2000 --overlap 0.12 [--box x0 y0 x1 y1]

Writes DIR/t000.jpg... plus DIR/tiles.json mapping every tile back to SOURCE px,
so anything a model says about a tile can be placed on the original. Tiles are
JPEG and capped at --max-side px because a vision model reads a 6586x15923 scroll
as nothing at all -- 105 megapixels is one grey smear at any thumbnail size the
context can hold.
"""
import argparse, json
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

p = argparse.ArgumentParser()
p.add_argument('--image', required=True)
p.add_argument('--out', required=True)
p.add_argument('--tile', type=int, default=2000, help='source px per tile')
p.add_argument('--overlap', type=float, default=0.12)
p.add_argument('--max-side', type=int, default=1400, help='tile is downscaled to this before writing')
p.add_argument('--box', nargs=4, type=int, help='x0 y0 x1 y1 in source px; default whole image')
p.add_argument('--quality', type=int, default=88)
a = p.parse_args()

im = Image.open(a.image).convert('RGB')
X0, Y0, X1, Y1 = a.box if a.box else (0, 0, *im.size)
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
step = max(1, int(a.tile * (1 - a.overlap)))
xs = list(range(X0, max(X1 - a.tile, X0) + 1, step))
ys = list(range(Y0, max(Y1 - a.tile, Y0) + 1, step))
if xs[-1] + a.tile < X1: xs.append(X1 - a.tile)
if ys[-1] + a.tile < Y1: ys.append(Y1 - a.tile)
tiles = []
for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        x1, y1 = min(x + a.tile, X1), min(y + a.tile, Y1)
        crop = im.crop((x, y, x1, y1))
        w, h = crop.size
        s = min(1.0, a.max_side / max(w, h))
        if s < 1.0:
            crop = crop.resize((round(w * s), round(h * s)), Image.LANCZOS)
        name = f't{len(tiles):03d}.jpg'
        crop.save(out / name, quality=a.quality)
        tiles.append({'file': name, 'row': j, 'col': i, 'sourceBox': [x, y, x1, y1],
                      'tileSize': list(crop.size), 'scale': round(s, 4)})
meta = {'tool': 'tile-image', 'image': a.image, 'sourceSize': list(im.size),
        'box': [X0, Y0, X1, Y1], 'tile': a.tile, 'overlap': a.overlap,
        'maxSide': a.max_side, 'grid': [len(ys), len(xs)], 'tiles': tiles}
(out / 'tiles.json').write_text(json.dumps(meta, indent=1))
print(json.dumps({k: meta[k] for k in ('sourceSize', 'box', 'tile', 'grid')} | {'n': len(tiles), 'out': str(out)}, indent=1))
