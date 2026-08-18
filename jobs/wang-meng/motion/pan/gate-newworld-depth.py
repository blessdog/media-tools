#!/usr/bin/env python3
"""GATE 2 — is MODEL-GENERATED territory depth-estimable, when the painting is not?

This is the gate the whole perpetual-view idea rests on. Every re-grounding step
has to turn a generated image back into a card stack, and that needs depth. The
oldest measured failure on this project is that monocular depth CANNOT read this
painting: Depth Anything V2 returned a smooth vertical gradient, with 55% of the
depth variance explained by image ROW alone.

THE CONTROL IS THE PAINTING ITSELF, re-measured in the same run. Quoting 55%
from a note written days ago and comparing it to a number computed today is not
a comparison, it is two numbers. Both go through the same model, same max-side,
same statistic, now.

THE STATISTIC. R-squared of depth against row index. A depth map that is really
just "lower in the frame = nearer" is a ramp and tells us nothing about the
scene; that is the failure signature. A LOW value means the estimator found
structure that is not explained by height in frame — which is what a card stack
needs. Reported alongside the correlation between depth and ink luminance,
because an estimator that merely traces dark brushstrokes is also not reading
depth (the figure work used the same check).
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
Image.MAX_IMAGE_PIXELS = None

CASES = [
    ("original painting (control)", HERE.parent / "shot-real.png"),
    ("card render, no fill", HERE / "new/void.png"),
    ("MODEL-GENERATED territory", HERE / "new/newworld.png"),
]


def depth_of(img: Path) -> np.ndarray:
    out = HERE / "new" / f"depth-{img.stem}.png"
    if not out.exists():
        subprocess.run([sys.executable, str(ROOT / "tools/estimate-depth.py"),
                        "--image", str(img), "--out", str(out),
                        "--max-side", "768"], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
    return np.asarray(Image.open(out).convert("I;16")).astype(float)


def main() -> int:
    print(f"{'image':30} {'R2 vs row':>10} {'corr ink':>9}  reading")
    print(f"{'':30} {'(lower=better)':>10}")
    for label, p in CASES:
        if not p.exists():
            print(f"  missing {p}", file=sys.stderr)
            continue
        d = depth_of(p)
        H, W = d.shape
        rows = np.repeat(np.arange(H)[:, None], W, 1).ravel()
        dv = d.ravel()
        # R^2 of a straight line fit of depth against row.
        r_row = float(np.corrcoef(rows, dv)[0, 1])
        r2 = r_row ** 2

        src = np.asarray(Image.open(p).convert("L").resize((W, H))).astype(float)
        r_ink = float(np.corrcoef(src.ravel(), dv)[0, 1])

        verdict = ("a RAMP — height in frame, not depth" if r2 > 0.40 else
                   "structure beyond height" if r2 < 0.20 else "partly a ramp")
        print(f"{label:30} {r2*100:>9.1f}% {r_ink:>9.3f}  {verdict}")
    print("\nThe painting's recorded failure signature is 55% R2 vs row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
