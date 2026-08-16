#!/usr/bin/env python3
"""media-tools — complete-planes: a plane stack with gaps → every pixel claimed.

One job: close the holes a segmenter left, so no painted object straddles two
depths. It does not re-segment, judge, or render. `probe-planes` is the lint that
says whether a stack needs this and whether it worked.

WHY A GAP IS NOT COSMETIC. render-parallax lays the whole source underneath as a
BASE plane so unclaimed pixels still show the painting rather than a hole. That
is the right default for a static look and a trap for a moving camera: the base
sits one step BEYOND the farthest plane, so any ink the segmenter missed is
rendered 2x further away than the object it belongs to. Under a dolly the object
is then magnified at two rates at once and visibly deforms. Measured on
wang-meng: 26.5% of the frame unclaimed, 18.3% of all INK landing on the base
plane, and Ge Hong split 81/13 between his ledge and the backing — parts of one
man growing 1.35x more than other parts of him.

SEAL BY PROXIMITY, NOT BY COMPONENT. The tempting fix is to reassign each ink
component wholesale to its majority plane. Do not, without checking: brushed ink
connects far more than intuition suggests, and on this painting one component was
17.7% of all ink at a sane threshold and 94% at a loose one. Reassigning that
flattens the stack. Proximity makes no such claim — an unclaimed pixel joins the
NEAREST claimed plane, which is what a human filling holes would do, and it
cannot merge two planes that were correctly separate.

Bare silk (留白) gets swept up too, and that is fine: an absence has no contour
and no detail, so which card carries it is invisible until it moves, whereas ink
falling to the base is visible immediately. Render the result with --no-base;
coverage is total, so the backing plane has nothing left to do.

usage:
  complete-planes.py --layers DIR --out DIR [--max-dist N] [--feather N]

  --layers DIR   a segment-points output dir (layers.json + layers/*.png)
  --out DIR      the sealed stack: layers.json + layers/*.png, same shape
  --max-dist N   refuse to expand ownership further than N px, leaving anything
                 beyond it unclaimed. Off by default — partial sealing leaves
                 exactly the failure this tool exists to remove. Use it only to
                 diagnose how far the gaps reach.
  --feather N    alpha feather on the sealed masks (default from the input)
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
UNCLAIMED = -1


def main() -> int:
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--layers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-dist", type=float, default=0.0)
    ap.add_argument("--feather", type=int, default=-1)
    a = ap.parse_args()

    lay = Path(a.layers)
    meta = json.loads((lay / "layers.json").read_text())
    W, H = meta["size"]
    src_path = Path(meta["image"])
    if not src_path.exists():
        print(f"layers.json names {src_path}, missing from here. Run from the "
              f"repo root.", file=sys.stderr)
        return 1
    out = Path(a.out)
    (out / "layers").mkdir(parents=True, exist_ok=True)

    planes = sorted([p for p in meta["planeList"] if p.get("layer")],
                    key=lambda p: p["depth"])
    # Ownership in render order: farthest first, nearer wins. Must match
    # render-parallax or this seals a stack nobody draws.
    own = np.full((H, W), UNCLAIMED, np.int32)
    for i, p in enumerate(planes):
        im = np.asarray(Image.open(lay / p["layer"]).convert("RGBA"))
        ox, oy = p["offset"]
        h, w = im.shape[:2]
        own[oy:oy + h, ox:ox + w][im[..., 3] > 128] = i     # index, not depth:
    # two planes may share a depth and must stay separate layers.

    claimed = own != UNCLAIMED
    before = float((~claimed).mean())
    if not claimed.any():
        print("every pixel unclaimed — nothing to expand from", file=sys.stderr)
        return 1

    # Nearest-claimed-pixel Voronoi. distanceTransformWithLabels finds, for every
    # pixel, the nearest ZERO pixel and hands back a unique label for it; the
    # label ids are opaque, so recover the mapping by reading the label image AT
    # the zero pixels themselves.
    src = np.where(claimed, 0, 255).astype(np.uint8)
    dist, labels = cv2.distanceTransformWithLabels(
        src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    lut = np.zeros(int(labels.max()) + 1, np.int32)
    lut[labels[claimed]] = own[claimed]
    filled = lut[labels]
    if a.max_dist > 0:
        filled = np.where(dist <= a.max_dist, filled, UNCLAIMED)

    feather = a.feather if a.feather >= 0 else int(meta.get("feather", 0))
    img = Image.open(src_path).convert("RGBA")
    arr = np.asarray(img)

    new_list, grown = [], []
    for i, p in enumerate(planes):
        m = (filled == i)
        if not m.any():
            print(f"  {p['name']}: sealed away entirely, dropped", file=sys.stderr)
            continue
        alpha = (m.astype(np.uint8) * 255)
        if feather > 0:
            k = feather * 2 + 1
            alpha = cv2.GaussianBlur(alpha, (k, k), 0)
        ys, xs = np.where(m)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        tile = arr[y0:y1, x0:x1].copy()
        tile[..., 3] = alpha[y0:y1, x0:x1]
        name = Path(p["layer"]).name
        Image.fromarray(tile).save(out / "layers" / name)
        q = dict(p)
        q["layer"] = f"layers/{name}"
        q["offset"] = [x0, y0]
        q["sealedFrom"] = int((own == i).sum())
        q["sealedTo"] = int(m.sum())
        new_list.append(q)
        grown.append((p["name"], q["sealedFrom"], q["sealedTo"]))

    for nm, b, c in sorted(grown, key=lambda g: -(g[2] - g[1]))[:6]:
        print(f"  {nm:24} {b:7} -> {c:7} px  (+{100*(c-b)/max(b,1):.0f}%)",
              file=sys.stderr)

    after = float((filled == UNCLAIMED).mean())
    new_meta = dict(meta)
    new_meta["planeList"] = new_list
    new_meta["tool"] = "complete-planes"
    new_meta["sealedFrom"] = str(lay)
    new_meta["unclaimedFraction"] = round(after, 6)
    new_meta["note"] = ("sealed by nearest-plane proximity; coverage is total, so "
                        "RENDER WITH --no-base — the backing plane is what made "
                        "unclaimed ink render at the wrong depth.")
    (out / "layers.json").write_text(json.dumps(new_meta, indent=1))

    print(json.dumps({
        "tool": "complete-planes", "layers": str(lay), "out": str(out),
        "planes": len(new_list),
        "unclaimedBefore": round(before, 4), "unclaimedAfter": round(after, 6),
        "maxExpansionPx": round(float(dist[~claimed].max()) if (~claimed).any() else 0.0, 1),
        "next": f"probe-planes.py --layers {out}   then render with --no-base",
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
