#!/usr/bin/env python3
"""How thick is each tree's thickest stroke, in plate px.

Wang Meng paints a tree at near-constant real size, so a distant tree is
the same drawing made smaller -- and its trunk stroke is thinner by the same
ratio. A branch-radius that is right for one tree is therefore wrong for every
tree drawn at another scale. This measures the scale directly: the ink
mask's distance transform, 99th percentile, doubled = the widest stroke.
Same ink read as hinge-foliage --from-ink (V below the 75th-percentile
ground by --ink-offset, closed by 1).
"""
import json, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image

out = {}
for wd in sorted(Path(sys.argv[1]).glob('s-*')):
    lj = wd / 'mask' / 'layers.json'
    if not lj.exists() or not (wd / 'plate.png').exists():
        continue
    src = np.array(Image.open(wd / 'plate.png').convert('RGB'))
    meta = json.loads(lj.read_text())
    m = np.zeros(src.shape[:2], bool)
    for pl in meta['planeList']:
        a = np.array(Image.open(wd / 'mask' / 'masks' / f"{pl['n']:03d}.png").convert('L')) > 128
        m |= a
    v = cv2.cvtColor(src, cv2.COLOR_RGB2HSV)[..., 2].astype(np.float32) / 255
    ground = float(np.percentile(v[m], 75))
    ink = ((v < ground - 0.11) & m).astype(np.uint8)
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    dt = cv2.distanceTransform(ink, cv2.DIST_L2, 3)
    d = dt[ink > 0]
    out[wd.name] = {'inkPx': int(ink.sum()),
                    'halfWidth_p99': round(float(np.percentile(d, 99)), 2),
                    'halfWidth_p999': round(float(np.percentile(d, 99.9)), 2),
                    'halfWidth_max': round(float(d.max()), 2)}
print(json.dumps(out, indent=1))
