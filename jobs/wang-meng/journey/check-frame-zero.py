#!/usr/bin/env python3
"""The frame-zero invariant, made checkable again.

THE INVARIANT. Every pixel inpaint-planes paints is, at rest, hidden behind the
very plane that was occluding it. So frame zero must be unchanged by filling.
inpaint-planes' own docstring says "FRAME ZERO MUST COME OUT BYTE-IDENTICAL".

IT IS NOT, AND THAT IS NOT A LEAK. Measured 2026-08-24 on z1: pre-fill vs
flux-filled differs at 39,210 px (1.89% of frame), pre-fill vs shiftmap-filled
at 40,130 px -- nearly identical, because the cause is the fill EXISTING, not
which fill. --behind grows each plane's layer box, --plane-fit resamples on the
shifted grid, and silhouette edges land on a different subpixel phase. The
differing pixels sit on edges: median |grad| 35.9 against 0.0 at random pixels.

WHY IT STILL MATTERS. A byte-exact test that is never byte-exact is not a test.
39,210 px of edge shimmer is a place for a real leak of a few thousand pixels to
hide, and nobody would see it. So the invariant is restated in a form the render
path can actually satisfy:

  EDGE SHIMMER is thousands of tiny components -- 22,162 of them on z1, the
  largest 49 px. A REAL LEAK is contiguous: a painted band that became visible
  is one blob of thousands of px. So threshold on COMPONENT AREA, not on total.

  leak = any connected difference component >= --min-blob px   (default 200,
         about 4x the largest edge artifact measured on z1)

That keeps the check blind to resampling and sensitive to content, and unlike a
gradient mask it does not go blind to a leak that happens to land on an edge.

Per checks-start-in-observation this reports and exits 0. --strict makes it an
error once it has a log behind it.

usage:
  check-frame-zero.py --before DIR --after DIR [--min-blob 200] [--strict]
    DIR = a rendered frame directory; 00000.png is read from each.
"""
import argparse, json, sys
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True, help="frames rendered from the pre-fill stack")
    ap.add_argument("--after", required=True, help="frames rendered from the filled stack")
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--min-blob", type=int, default=200)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    fn = f"{a.frame:05d}.png"
    p = np.asarray(Image.open(f"{a.before}/{fn}").convert("RGB")).astype(int)
    q = np.asarray(Image.open(f"{a.after}/{fn}").convert("RGB")).astype(int)
    if p.shape != q.shape:
        print(json.dumps({"error": "frame sizes differ", "before": p.shape, "after": q.shape}))
        sys.exit(1)

    d = np.abs(p - q).max(2)
    m = (d > 0).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    areas = stats[1:, 4] if n > 1 else np.array([], dtype=int)
    leaks = [i + 1 for i, s in enumerate(areas) if s >= a.min_blob]

    out = {
        "frame": a.frame,
        "differingPx": int(m.sum()),
        "differingPct": round(100.0 * m.mean(), 4),
        "components": int(n - 1),
        "largestComponentPx": int(areas.max()) if areas.size else 0,
        "maxChannelDelta": int(d.max()),
        "minBlob": a.min_blob,
        "leakComponents": len(leaks),
        "leakPx": int(sum(stats[i, 4] for i in leaks)),
        "verdict": "LEAK" if leaks else "edge-shimmer only",
    }
    if leaks:
        out["leakBoxes"] = [[int(v) for v in stats[i, :4]] for i in leaks[:10]]
    print(json.dumps(out, indent=1))
    if leaks and a.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
