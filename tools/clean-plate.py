#!/usr/bin/env python3
"""Remove a masked object from a still by patch synthesis. One job.

A cut-out puppet needs the background it stands in front of, because the moment
it moves it uncovers pixels the painter never painted. Averaging inpainters
(cv2 TELEA, NS) fail on ink on silk: they diffuse surrounding colour inward and
a figure-sized hole becomes mush with no weave and no brush. Patch-based
SHIFTMAP synthesis copies real patches from elsewhere in the image, so the silk
texture and the stroke grain survive -- measured 3.7s on a 720x1280 plate, free,
no model.

SHIFTMAP cost grows with the whole image, not the hole, so only a padded box
around the mask is synthesised and pasted back. That makes a clean plate over a
3000px pan strip cost the same as one over a single frame.

  ./clean-plate.py --image SRC.png --masks DIR [--only NAME] --out PLATE.png
      [--grow 3] [--pad 1.5] [--method shiftmap|telea|ns]
"""
import argparse, json, time
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

p = argparse.ArgumentParser()
p.add_argument('--image', required=True)
p.add_argument('--masks', required=True, action='append', help='dir holding layers.json + masks/')
p.add_argument('--only', action='append', default=None, help='plane name; repeatable')
p.add_argument('--mask-offset', default=None, help='x,y to add to every mask offset, when the masks '
                                                   'were cut against a smaller crop of this image')
p.add_argument('--out', required=True)
p.add_argument('--grow', type=int, default=3, help='px to dilate the mask, so no ink halo is left behind')
p.add_argument('--pad', type=float, default=1.5, help='synthesis box, as a multiple of the mask box')
p.add_argument('--method', default='shiftmap', choices=['shiftmap', 'telea', 'ns'])
a = p.parse_args()

img = np.array(Image.open(a.image).convert('RGB'))
H, W = img.shape[:2]

mox, moy = (int(q) for q in a.mask_offset.split(',')) if a.mask_offset else (0, 0)

m = np.zeros((H, W), np.uint8)
names = []
for d in a.masks:
    meta = json.load(open(Path(d) / 'layers.json'))
    # a mask cut against a 720x1280 shot silently lands in the wrong place on a
    # 1070x1380 pan strip, and the damage looks plausible: the hole appears in
    # empty silk and the figure stays painted in. Refuse instead.
    if meta.get('size') and list(meta['size']) != [W, H] and not a.mask_offset:
        raise SystemExit(f'masks in {d} were cut against {meta["size"]} but this image is '
                         f'{[W, H]}; pass --mask-offset to say where they belong')
    for pl in meta['planeList']:
        if a.only and pl['name'] not in a.only:
            continue
        mi = np.array(Image.open(Path(d) / 'masks' / f"{pl['n']:03d}.png").convert('L'))
        ox, oy = pl['offset'][0] + mox, pl['offset'][1] + moy; mh, mw = mi.shape
        sub = m[oy:oy + mh, ox:ox + mw]
        m[oy:oy + mh, ox:ox + mw] = np.maximum(sub, (mi > 96).astype(np.uint8) * 255)
        names.append(pl['name'])
if not names:
    raise SystemExit('no planes matched --only')
if a.grow:
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (a.grow * 2 + 1,) * 2)
    m = cv2.dilate(m, k)

ys, xs = np.nonzero(m)
bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
bw, bh = bx1 - bx0, by1 - by0
px, py = int(bw * (a.pad - 1) / 2), int(bh * (a.pad - 1) / 2)
x0, y0 = max(0, bx0 - px), max(0, by0 - py)
x1, y1 = min(W, bx1 + px + 1), min(H, by1 + py + 1)

t = time.time()
crop = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_RGB2BGR)
mc = m[y0:y1, x0:x1]
if a.method == 'shiftmap':
    dst = np.zeros_like(crop)
    cv2.xphoto.inpaint(crop, 255 - mc, dst, cv2.xphoto.INPAINT_SHIFTMAP)
else:
    flag = cv2.INPAINT_TELEA if a.method == 'telea' else cv2.INPAINT_NS
    dst = cv2.inpaint(crop, mc, 5, flag)
secs = round(time.time() - t, 2)

out = img.copy()
out[y0:y1, x0:x1] = cv2.cvtColor(dst, cv2.COLOR_BGR2RGB)
Image.fromarray(out).save(a.out)

# did the hole actually get filled with texture, or with a flat average? Local
# stddev inside the hole against the ring just outside it: a mush fill collapses.
hole = m > 0
ring = cv2.dilate(m, np.ones((41, 41), np.uint8)) > 0
ring &= ~hole
g = cv2.cvtColor(out, cv2.COLOR_RGB2GRAY).astype(np.float32)
print(json.dumps({'out': a.out, 'removed': names, 'method': a.method,
                  'maskPx': int(hole.sum()), 'synthBox': [int(x0), int(y0), int(x1), int(y1)],
                  'seconds': secs,
                  'textureInHole': round(float(g[hole].std()), 2),
                  'textureInRing': round(float(g[ring].std()), 2),
                  'note': 'textureInHole far below textureInRing means the fill is mush'},
                 indent=2))
