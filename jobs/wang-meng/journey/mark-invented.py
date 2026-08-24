"""Rebuild the invented-material marker stack for z1.

The invented pixels are the ones inpaint-planes painted OUTSIDE the mask that
segment/pin produced: alpha(layers-filled) AND NOT alpha(layers-pinned), aligned
by each layer's own offset because --behind 100 grows the layer box.
"""
import json, os, sys
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

Z = "jobs/wang-meng/journey/z1"
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

filled = json.load(open(f"{Z}/layers-filled/layers.json"))
pinned = json.load(open(f"{Z}/layers-pinned/layers.json"))
pin_by = {p["name"]: p for p in pinned["planeList"] if p.get("layer")}

tot_inv = tot_paint = 0
for p in filled["planeList"]:
    if not p.get("layer"):
        continue
    fim = Image.open(f"{Z}/layers-filled/{p['layer']}").convert("RGBA")
    fa = np.asarray(fim.split()[3]) > 0
    keep = np.zeros_like(fa)
    q = pin_by.get(p["name"])
    if q is not None:
        pim = Image.open(f"{Z}/layers-pinned/{q['layer']}").convert("RGBA")
        pa = np.asarray(pim.split()[3]) > 0
        dx, dy = q["offset"][0] - p["offset"][0], q["offset"][1] - p["offset"][1]
        h, w = pa.shape
        y0, x0 = max(0, dy), max(0, dx)
        y1, x1 = min(fa.shape[0], dy + h), min(fa.shape[1], dx + w)
        if y1 > y0 and x1 > x0:
            keep[y0:y1, x0:x1] = pa[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    inv = fa & ~keep
    tot_inv += int(inv.sum()); tot_paint += int((fa & keep).sum())
    # WHITE = invented, BLACK = the painter's own ink. Alpha unchanged so the
    # marker stack projects through exactly the same geometry as the real one.
    rgb = np.zeros(fa.shape + (3,), np.uint8)
    rgb[inv] = 255
    m = Image.fromarray(np.dstack([rgb, np.asarray(fim.split()[3])]), "RGBA")
    os.makedirs(os.path.dirname(f"{OUT}/{p['layer']}"), exist_ok=True)
    m.save(f"{OUT}/{p['layer']}")

json.dump(filled, open(f"{OUT}/layers.json", "w"), indent=1)
print(json.dumps({"inventedPx": tot_inv, "paintedPx": tot_paint,
                  "stackPctInvented": round(100.0 * tot_inv / (tot_inv + tot_paint), 2)}))
