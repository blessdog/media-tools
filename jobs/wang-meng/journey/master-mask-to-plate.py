#!/usr/bin/env python3
"""Bring one or more MASTER-space masks into a zone's PLATE space.

    master-mask-to-plate.py --zone z1 --masks a.png b.png --out leaf.png

One job. It does not build masks, cut cards, or animate -- it moves an existing
mask from the coordinate system the catalogue works in to the one the renderer
and hinge-foliage work in.

WHY IT IS NEEDED. The catalogue and its SAM refinement live in MASTER px
(6586x15923). Every zone plate is a crop of the master scaled by k, and
plate.json records that crop as masterBox. A mask is useless to hinge-foliage
until it has been through that transform, and doing the arithmetic inline each
time is how an off-by-a-scale-factor bug gets written twice.

MULTIPLE MASKS ARE UNIONED because the catalogue was built in bands: z3w covers
master y 4712-12594 and z1lower covers 12594-15923, while zone z1 spans
9596-15923 and needs both.
"""
import argparse, json, os
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
J = "jobs/wang-meng"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default="z1")
    ap.add_argument("--masks", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    Z = f"{REPO}/{J}/journey/{a.zone}"
    box = json.load(open(f"{Z}/plate.json"))["masterBox"]      # x0, y0, x1, y1
    W, H = Image.open(f"{Z}/plate.png").size
    acc = np.zeros((H, W), bool)
    per = {}
    for m in a.masks:
        src = np.asarray(Image.open(m).convert("L"))
        sub = src[box[1]:box[3], box[0]:box[2]]
        # INTER_AREA on a binary mask averages; threshold after, or a thin leaf
        # spray downsampled 2.34x disappears below any rounding.
        small = cv2.resize(sub.astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)
        got = small > 40
        per[os.path.basename(m)] = int(got.sum())
        acc |= got
    Image.fromarray((acc * 255).astype(np.uint8)).save(a.out)
    rep = {"zone": a.zone, "masterBox": box, "plate": [W, H],
           "out": a.out, "perMask": per,
           "leafPx": int(acc.sum()), "pctOfPlate": round(100.0 * acc.mean(), 2)}
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
