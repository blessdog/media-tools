#!/usr/bin/env python3
"""How much does a MEANDERING path reveal that a straight push does not?

The question this answers (Pissjug, 2026-08-17, looking at the radial
divergence map): the fill was made for a push toward one point — what happens
when the camera walks a trail instead?

WHAT IS AND IS NOT PATH-DEPENDENT. `inpaint-planes` fills in LAYER space: what
sits behind a plane does not change when the camera moves, so the painted
material is reusable across every path, for free. What IS path-dependent is the
REACH — `--behind N` is a budget, and a path that reveals more than N pixels
behind an occluder runs off the end of the paint into void. So the fill never
needs redoing per shot; the BUDGET has to be sized for the widest move planned.

This measures that budget instead of guessing it, which is what
inpaint-planes' own docs demand: "set it from the measured hole width, not
taste."

Two numbers per path:
  coverage   how much of the frame is ever unpainted (holes)
  reach      the deepest a hole runs from the nearest painted pixel — this is
             the number --behind has to beat

usage: python3 probe-path-budget.py
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
PATHS = {"straight push": "path-push-deep.json", "meander": "path-meander.json"}


def render(pathfile: str, out: Path, fill: str) -> None:
    subprocess.run([
        sys.executable, str(ROOT / "tools/render-parallax.py"),
        "--layers", "jobs/wang-meng/motion/pan/layers-pinned",
        "--out", str(out.relative_to(ROOT)),
        "--path", f"jobs/wang-meng/motion/pan/{pathfile}",
        "--geometry", "jobs/wang-meng/motion/pan/geometry-shot.json",
        "--plane-fit", "--z-step", "0.15", "--width", "720", "--height", "1280",
        "--fps", "24", "--preview", "6", "--no-base", "--fill", fill,
    ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    rows = []
    for label, pf in PATHS.items():
        d = json.loads((HERE / pf).read_text())
        base = HERE / "budget" / pf.replace(".json", "")
        render(pf, base.with_name(base.name + "-b"), "black")
        render(pf, base.with_name(base.name + "-p"), "paper")
        bs = sorted((base.with_name(base.name + "-b")).glob("*.png"))
        ps = sorted((base.with_name(base.name + "-p")).glob("*.png"))

        union = None
        worst_cov, worst_reach = 0.0, 0
        for fb, fp in zip(bs, ps):
            b = np.asarray(Image.open(fb).convert("RGB")).astype(int)
            p = np.asarray(Image.open(fp).convert("RGB")).astype(int)
            m = (np.abs(b - p).sum(2) > 12)
            union = m if union is None else (union | m)
            worst_cov = max(worst_cov, float(m.mean()))
            # How deep does a hole run? Distance from each hole pixel to the
            # nearest NON-hole pixel; the max is the reach --behind must cover.
            dt = cv2.distanceTransform((m * 255).astype(np.uint8), cv2.DIST_L2, 5)
            worst_reach = max(worst_reach, int(dt.max()))

        assert union is not None
        rows.append((label, d["duration"], worst_cov, float(union.mean()), worst_reach))
        Image.fromarray((union * 255).astype(np.uint8)).save(
            HERE / f"holes-{pf.replace('.json','').replace('path-','')}.png")

    print(f"{'path':16} {'secs':>5} {'worst frame':>12} {'union':>8} {'reach px':>9}")
    for label, dur, wc, un, wr in rows:
        print(f"{label:16} {dur:>5} {wc*100:>11.2f}% {un*100:>7.2f}% {wr:>9}")

    print(f"\n--behind is currently 100.")
    need = max(r[4] for r in rows)
    print(f"widest reach measured: {need}px "
          f"→ {'COVERED' if need <= 100 else f'NOT COVERED, raise --behind to ~{int(need*1.3)}'}")
    print("\nwrote holes-push-deep.png and holes-meander.png "
          "(union of every hole across the clip)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
