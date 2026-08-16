#!/usr/bin/env python3
"""media-tools — probe-planes: is a plane stack OBJECT-COMPLETE? One job.

It can only falsify. It never edits a stack; `complete-planes` does that.

THE INVARIANT. A depth plane is a rigid card, so every painted thing must sit
WHOLLY on one card. If a single object straddles two depths, a camera move
magnifies its halves at different rates and the object visibly deforms — and the
more depth separation you add to escape a zoom, the worse the deformation gets.
That trade is what makes this a lint and not a nicety: without it, fixing the
zoom and deforming the painting are the same action.

MEASURED ON WANG-MENG (2026-08-16), which is why this tool exists. Ge Hong's ink
sat 81.1% on foreground-path-ledge, 12.9% on the unclaimed BASE plane 2.2x
further away, plus fragments on two more. Parts of one man magnified 1.35x more
than other parts of the same man. The stack reported 75.3% coverage and looked
fine; the unclaimed quarter was invisible until a camera moved.

WHERE THE TEARS COME FROM, in the order they matter:
  1. UNCLAIMED ink falling through to the base plane, which sits at max depth.
     Segmentation leaves holes inside objects, not just between them.
  2. One object genuinely split between two claimed planes.
Both read identically in a render. This tool separates them, because the fixes
are different: (1) is sealed by proximity, (2) needs the plane redrawn.

READ THE COMPONENT SIZES BEFORE FIXING. If a painting's ink is one giant
connected blob, per-component reassignment would flatten the whole stack to a
single depth. Ink in a brushed landscape connects far more than intuition
suggests, so this tool prints the size distribution first and refuses to
recommend anything.

usage:
  probe-planes.py --layers DIR [--ink N] [--min-size N] [--pure F] [--json]

  --layers DIR   a segment-points output dir (layers.json + layers/*.png)
  --ink N        luminance below this is ink (default 110). TUNE THIS FIRST and
                 read the largest-component line: on wang-meng 150 caught the
                 wash as well as the ink and fused 94% of it into one blob,
                 which makes every component look torn and hides the real
                 signal. 110 gave 15.9% of frame and 42 components.
  --min-size N   ignore ink components smaller than this (default 400 px)
  --pure F       a component is TORN below this majority fraction (default 0.95)
  --json         full manifest on stdout, including every torn component
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
BASE = -2      # what unclaimed ink actually renders as: the backing plane


def ownership(meta, lay, H, W):
    """Depth index per pixel, painted farthest-first so nearer planes win.

    This reproduces render-parallax's paint order exactly. Any other order would
    measure a stack nobody renders.
    """
    own = np.full((H, W), UNCLAIMED, np.int32)
    names = {}
    planes = sorted([p for p in meta["planeList"] if p.get("layer")],
                    key=lambda p: p["depth"])
    for p in planes:
        im = np.asarray(Image.open(lay / p["layer"]).convert("RGBA"))
        ox, oy = p["offset"]
        h, w = im.shape[:2]
        sub = own[oy:oy + h, ox:ox + w]
        sub[im[..., 3] > 128] = p["depth"]
        names.setdefault(p["depth"], p["name"])
    return own, names, planes


def main() -> int:
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--layers", required=True)
    ap.add_argument("--ink", type=int, default=110)
    ap.add_argument("--min-size", type=int, default=400)
    ap.add_argument("--pure", type=float, default=0.95)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    lay = Path(a.layers)
    meta = json.loads((lay / "layers.json").read_text())
    W, H = meta["size"]
    src = Path(meta["image"])
    if not src.exists():
        print(f"layers.json names {src}, which does not exist from here. "
              f"Run from the repo root.", file=sys.stderr)
        return 1

    own, names, planes = ownership(meta, lay, H, W)
    max_depth = max(p["depth"] for p in planes)
    # Unclaimed ink does not vanish, it renders on the backing plane one step
    # BEYOND the farthest real plane. Naming that explicitly is the point.
    base_depth = max_depth + 1
    names[base_depth] = "(base plane — unclaimed)"
    own_r = np.where(own == UNCLAIMED, base_depth, own)

    grey = np.asarray(Image.open(src).convert("L"))
    ink = (grey < a.ink).astype(np.uint8)
    n_lab, lab, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)

    sizes = stats[1:, cv2.CC_STAT_AREA]
    keep = np.where(sizes >= a.min_size)[0] + 1
    print(f"  ink {100 * ink.mean():.1f}% of frame · {n_lab - 1} components, "
          f"{len(keep)} over {a.min_size}px", file=sys.stderr)
    if len(sizes):
        big = int(sizes.max())
        print(f"  LARGEST COMPONENT is {big} px = {100 * big / max(ink.sum(), 1):.1f}% "
              f"of all ink. If that is most of the ink, per-component "
              f"reassignment would flatten the stack — seal by proximity "
              f"instead.", file=sys.stderr)

    torn, ink_total, ink_torn = [], 0, 0
    for li in keep:
        m = lab == li
        n = int(m.sum())
        ink_total += n
        d = own_r[m]
        counts = np.bincount(d, minlength=base_depth + 1)
        maj = int(counts.argmax())
        frac = float(counts[maj]) / n
        spread = [int(x) for x in np.unique(d)]
        if frac < a.pure:
            ink_torn += n
            ys, xs = np.where(m)
            torn.append({
                "size": n, "majority": names.get(maj, str(maj)),
                "majorityFrac": round(frac, 4),
                "depths": [names.get(x, str(x)) for x in spread],
                "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                "onBaseFrac": round(float(counts[base_depth]) / n, 4),
            })
    torn.sort(key=lambda t: -t["size"])

    ink_on_base = float((own_r[ink.astype(bool)] == base_depth).mean())
    out = {
        "tool": "probe-planes", "layers": str(lay),
        "components": len(keep),
        "tornComponents": len(torn),
        "inkTornFrac": round(ink_torn / max(ink_total, 1), 4),
        "inkOnBasePlaneFrac": round(ink_on_base, 4),
        "unclaimedPixelFrac": round(float((own == UNCLAIMED).mean()), 4),
        "largestComponentFracOfInk": round(float(sizes.max()) / max(int(ink.sum()), 1), 4) if len(sizes) else 0.0,
        "verdict": "OBJECT-COMPLETE" if not torn else "TORN",
    }
    for t in torn[:8]:
        print(f"    TORN {t['size']:7}px  {t['majorityFrac']*100:5.1f}% on "
              f"{t['majority']:24} + {len(t['depths'])-1} more"
              f"{'  (' + str(round(t['onBaseFrac']*100,1)) + '% on base)' if t['onBaseFrac'] > 0.01 else ''}",
              file=sys.stderr)
    if a.json:
        out["torn"] = torn
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
