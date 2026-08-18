#!/usr/bin/env python3
"""Does the flux fill survive motion? Two questions, one pass over the frames.

1. FLICKER. I claimed layer-space filling makes per-frame flicker structurally
   impossible. That is an argument, not evidence. Measured here as the mean
   frame-to-frame difference. THE CLASSICAL CLIP IS THE FLOOR, not zero: both
   clips resample real texels through a moving camera, so both have a non-zero
   temporal derivative from resampling alone. Flux is stable if it sits AT the
   classical floor. Sitting above it means the fill is doing something the
   camera is not.

2. WHERE DID IT INVENT. The single-frame gate caught flux hallucinating a red
   flower. In layer space that invention is baked into a plane and travels with
   it. This finds the pixels where the two clips diverge most across the whole
   clip and crops both there, so the divergence can be watched rather than
   described.

usage: python3 probe-fill-motion.py
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
A, B = HERE / "ab/layers-final", HERE / "ab/layers-flux"


def frames(d: Path):
    fs = sorted(d.glob("*.png"))
    if not fs:
        raise SystemExit(f"no frames in {d} — run flux-vs-classical.sh first")
    return fs


def main() -> int:
    fa, fb = frames(A), frames(B)
    n = min(len(fa), len(fb))
    print(f"{n} frames each\n")

    prev_a = prev_b = None
    ta = tb = 0.0
    peak = None                      # max |flux - classical| over the whole clip
    for i in range(n):
        a = np.asarray(Image.open(fa[i]).convert("RGB")).astype(np.int16)
        b = np.asarray(Image.open(fb[i]).convert("RGB")).astype(np.int16)
        d = np.abs(a - b).sum(2)
        peak = d if peak is None else np.maximum(peak, d)
        if prev_a is not None:
            ta += float(np.abs(a - prev_a).mean())
            tb += float(np.abs(b - prev_b).mean())
        prev_a, prev_b = a, b

    print("FLICKER  (mean frame-to-frame difference, 0-255 per channel)")
    print(f"  classical (the floor) : {ta/(n-1):6.3f}")
    print(f"  flux                  : {tb/(n-1):6.3f}")
    ratio = tb / max(ta, 1e-9)
    print(f"  flux / classical      : {ratio:6.3f}"
          f"   {'— at the floor, no added flicker' if ratio < 1.08 else '— ABOVE the floor, investigate'}\n")

    assert peak is not None
    print("DIVERGENCE  (where the two clips differ most)")
    print(f"  pixels ever differing : {int((peak > 12).sum())} "
          f"({(peak > 12).mean()*100:.2f}% of frame)")
    print(f"  worst pixel           : {int(peak.max())} / 765")

    Image.fromarray(np.clip(peak, 0, 255).astype(np.uint8)).save(HERE / "fill-divergence.png")

    # Crop both clips around the single worst divergence and render it side by
    # side, slowed, so the thing can be watched instead of argued about.
    ys, xs = np.nonzero(peak > 60)
    if len(ys) == 0:
        print("\nno region diverges enough to be worth zooming.")
        return 0
    cy, cx = int(np.median(ys)), int(np.median(xs))
    s = 150
    H, W = peak.shape
    y0, x0 = max(0, cy - s), max(0, cx - s)
    y1, x1 = min(H, y0 + 2 * s), min(W, x0 + 2 * s)
    print(f"  zooming on ({cx},{cy})")

    vf = (f"crop={x1-x0}:{y1-y0}:{x0}:{y0},scale=600:-1:flags=neighbor,"
          f"setpts=2.0*PTS")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-i", str(HERE / "ab/layers-final.mp4"),
                    "-i", str(HERE / "ab/layers-flux.mp4"),
                    "-filter_complex",
                    f"[0:v]{vf}[a];[1:v]{vf}[b];[a][b]hstack=inputs=2[v]",
                    "-map", "[v]", "-c:v", "libx264", "-crf", "16",
                    "-pix_fmt", "yuv420p", str(HERE / "FILL-DIVERGENCE.mp4")],
                   check=True)
    print(f"\nwrote fill-divergence.png and FILL-DIVERGENCE.mp4 "
          f"(classical | flux, 2x slow, nearest-neighbour)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
