#!/usr/bin/env python3
"""How far can the camera wander before the card stack stops supporting it?

Pissjug, 2026-08-17, before committing to any fly-through. The straight push
needs 53px of paint behind each occluder; the aggressive meander needs 298px.
Reach is CONTINUOUS between those, so the useful question is not "meander or
not" but "how much wander fits inside a budget we trust".

THE PARAMETER. One scalar a scales how far the camera strays from a fixed
target. a=0 is the pure dolly (x,y pinned at 0.5). a=1 is the aggressive
meander. Everything else is interpolated: x = 0.5 + a*(x_meander - 0.5), same
for y. The Z PROFILE AND DURATION ARE HELD IDENTICAL at every a, so the only
thing changing is lateral wander — otherwise a longer or faster path would
confound the result.

WHAT IS MEASURED. `reach` is the deepest a hole runs from the nearest painted
pixel, via a distance transform. That is exactly the number `--behind` must
beat, so this reads directly as a budget. `union` is how much of the frame is
ever holed, which is what governs how much a model is being asked to invent —
the safety argument for this whole architecture was that the model touches a
few percent, and union is the number that argument lives or dies on.

usage: python3 probe-path-envelope.py [--amplitudes 0,0.2,...]
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
ROOT = HERE.parents[3]

# a=1 keys, from path-meander.json. z and t are the invariants.
KEYS = [(0, 0.38, 0.72, 0.00), (2, 0.30, 0.60, 0.12), (4, 0.48, 0.46, 0.24),
        (6, 0.62, 0.34, 0.34), (8, 0.55, 0.22, 0.45)]
BUDGET_NOW = 100      # what inpaint-planes was last run with
BUDGET_TRUST = 150    # 1.5x the proven budget — the line we agreed to test


def font(sz: int):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", sz)
    except OSError:
        return ImageFont.load_default()


def measure(a: float, tmp: Path) -> tuple[float, float, int]:
    keys = [{"t": t, "x": 0.5 + a * (x - 0.5), "y": 0.5 + a * (y - 0.5),
             "z": z, "fov": 1.0} for t, x, y, z in KEYS]
    pj = tmp / f"p{a:.2f}.json"
    pj.write_text(json.dumps({"fps": 24, "duration": 8, "keys": keys}))

    outs = {}
    for fill in ("black", "paper"):
        o = tmp / f"a{a:.2f}-{fill}"
        subprocess.run([
            sys.executable, str(ROOT / "tools/render-parallax.py"),
            "--layers", str(HERE / "layers-pinned"), "--out", str(o),
            "--path", str(pj), "--geometry", str(HERE / "geometry-shot.json"),
            "--plane-fit", "--z-step", "0.15", "--width", "720", "--height", "1280",
            "--fps", "24", "--preview", "6", "--no-base", "--fill", fill,
        ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        outs[fill] = sorted(o.glob("*.png"))

    union, worst, reach = None, 0.0, 0
    for fb, fp in zip(outs["black"], outs["paper"]):
        b = np.asarray(Image.open(fb).convert("RGB")).astype(int)
        p = np.asarray(Image.open(fp).convert("RGB")).astype(int)
        m = np.abs(b - p).sum(2) > 12
        union = m if union is None else (union | m)
        worst = max(worst, float(m.mean()))
        dt = cv2.distanceTransform((m * 255).astype(np.uint8), cv2.DIST_L2, 5)
        reach = max(reach, int(dt.max()))
    assert union is not None
    return worst, float(union.mean()), reach


def chart(rows: list[tuple[float, float, float, int]], out: Path) -> None:
    # Panel geometry is explicit, not derived. The first version computed ph
    # from the height and collided the main title with the first panel title
    # and the first panel's axis labels with the second panel's title — which
    # is what opening the PNG is for.
    W, H, pad = 980, 720, 78
    PH, GAP, TOP0 = 230, 82, 92
    img = Image.new("RGB", (W, H), (247, 247, 243))
    d = ImageDraw.Draw(img)
    f9, f11, f14 = font(13), font(15), font(20)
    panels = [("reach — the paint budget --behind must beat", 3, "px", (44, 91, 109)),
              ("union — how much of the frame a model would be inventing into", 2, "%", (140, 58, 50))]
    ph = PH
    xs = [r[0] for r in rows]

    for pi, (title, idx, unit, col) in enumerate(panels):
        top = TOP0 + pi * (ph + GAP)
        vals = [(r[idx] * 100 if unit == "%" else r[idx]) for r in rows]
        vmax = max(max(vals) * 1.18, BUDGET_TRUST * 1.18 if unit == "px" else 10)
        d.text((pad, top - 24), title, font=f11, fill=(30, 33, 31))
        x0, y0, x1, y1 = pad, top, W - pad, top + ph
        d.rectangle([x0, y0, x1, y1], outline=(200, 204, 196))

        def px(i): return x0 + (x1 - x0) * (xs[i] - xs[0]) / (xs[-1] - xs[0])
        def py(v): return y1 - (y1 - y0) * v / vmax

        if unit == "px":                       # budget lines
            for lvl, lab, c in ((BUDGET_NOW, f"--behind {BUDGET_NOW} (as filled)", (150, 150, 145)),
                                (BUDGET_TRUST, f"{BUDGET_TRUST}px (trusted ceiling)", (138, 104, 28))):
                yy = py(lvl)
                for xx in range(int(x0), int(x1), 9):
                    d.line([xx, yy, xx + 5, yy], fill=c, width=2)
                d.text((x0 + 8, yy - 17), lab, font=f9, fill=c)

        pts = [(px(i), py(v)) for i, v in enumerate(vals)]
        d.line(pts, fill=col, width=3)
        for (cx, cy), v in zip(pts, vals):
            d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=col)
            d.text((cx - 14, cy - 26), f"{v:.0f}{'' if unit=='px' else '%'}",
                   font=f9, fill=col)
        for i in range(len(xs)):
            d.text((px(i) - 12, y1 + 7), f"{xs[i]:.2f}", font=f9, fill=(110, 117, 111))
        d.text((x0, y1 + 24), "camera wander  (0 = straight push, 1 = full meander)",
               font=f9, fill=(110, 117, 111))

    d.text((pad, 8), "How far the camera can wander before the cards stop supporting it",
           font=f14, fill=(25, 28, 26))
    img.save(out)


def main() -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--amplitudes", default="0,0.15,0.3,0.45,0.6,0.8,1.0")
    a_ = ap.parse_args()
    amps = [float(x) for x in a_.amplitudes.split(",")]

    rows = []
    with tempfile.TemporaryDirectory() as td:
        for a in amps:
            worst, union, reach = measure(a, Path(td))
            rows.append((a, worst, union, reach))
            print(f"  wander {a:.2f}   worst frame {worst*100:5.2f}%   "
                  f"union {union*100:5.2f}%   reach {reach:4d}px", file=sys.stderr)

    print(f"\n{'wander':>7} {'worst frame':>12} {'union':>8} {'reach':>7}")
    for a, w, u, r in rows:
        print(f"{a:>7.2f} {w*100:>11.2f}% {u*100:>7.2f}% {r:>6}px")

    # Where does reach cross each budget? Linear between measured points.
    def crossing(limit: int):
        for (a0, _, _, r0), (a1, _, _, r1) in zip(rows, rows[1:]):
            if r0 <= limit <= r1:
                return a0 + (a1 - a0) * (limit - r0) / max(r1 - r0, 1e-9)
        return None

    print()
    for lim in (BUDGET_NOW, BUDGET_TRUST):
        c = crossing(lim)
        print(f"reach hits {lim}px at wander "
              + (f"{c:.2f}" if c is not None else "— never, in this range"))
    chart(rows, HERE / "PATH-ENVELOPE.png")
    print(f"\nwrote {HERE/'PATH-ENVELOPE.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
