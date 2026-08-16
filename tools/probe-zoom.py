#!/usr/bin/env python3
"""media-tools — probe-zoom: is a camera move a ZOOM or a FLIGHT? One job.

It can only FALSIFY. A low score proves the move is a zoom; a high score is
consistent with parallax but is not on its own proof of anything, which is why
this is a probe- tool and not a measure- tool.

THE DEFINITION IS THE INSTRUMENT. A pure zoom means every output frame is the
FIRST frame magnified by ONE scalar about the optical centre. So: search for the
best single scale mapping frame 0 onto frame N, apply it, and report what is
left over. Motion a single scalar cannot explain is, by construction, motion
that came from depth.

WHY THIS AND NOT OPTICAL FLOW. Four earlier attempts on this project used flow
(residual after fitting scale+translation, radial expansion, per-band residual)
and every one failed its own control: a synthetic pure zoom, flat by
construction, scored 3.77px where the real clip scored 4.91px, because flow on
ink texture measures flow error, not depth. Direct image matching has no
correspondence step to be wrong about.

RUN THE CONTROL. --control takes a single still and synthesises the pure zoom
from it, then scores that. A flat image zoomed cannot contain parallax, so the
control score is this instrument's noise floor — resampling and nothing else.
Any clip must beat that floor by a wide margin before its number means anything.
Reporting a clip score without the floor beside it is how the last four
measurements got published wrong.

usage:
  probe-zoom.py --frames DIR [--control STILL] [--inset F] [--json]

  --frames DIR   a render-parallax output dir of %05d.png
  --control PNG  also synthesise + score a pure zoom of this still (the floor)
  --inset F      ignore this fraction of the border, where edge fill and
                 disocclusion live and would flatter the score (default 0.15)
  --scales N     search resolution for the scale fit (default 241)
  --json         manifest on stdout
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def zoom_about_centre(img: Image.Image, s: float) -> Image.Image:
    """Magnify by s about the image centre, output same size. Inverse affine."""
    W, H = img.size
    a = 1.0 / s
    cx = W / 2.0 - (W / 2.0) * a
    cy = H / 2.0 - (H / 2.0) * a
    return img.transform((W, H), Image.AFFINE, (a, 0, cx, 0, a, cy),
                         resample=Image.BILINEAR)


def best_scale(ref: Image.Image, tgt: np.ndarray, lo: float, hi: float,
               n: int, sl):
    """Smallest mean-abs-error over a scale sweep, and the scale that got it."""
    best, best_s = None, 1.0
    for s in np.linspace(lo, hi, n):
        w = np.asarray(zoom_about_centre(ref, float(s)).convert("L"), dtype=np.float32)
        e = float(np.abs(w[sl] - tgt[sl]).mean())
        if best is None or e < best:
            best, best_s = e, float(s)
    return best, best_s


def score(frames, inset, n_scales, label):
    ref = Image.open(frames[0]).convert("L")
    W, H = ref.size
    mx, my = int(W * inset), int(H * inset)
    sl = (slice(my, H - my), slice(mx, W - mx))
    rows = []
    # Scale grows monotonically on a dolly-in; 1.0..2.4 covers any sane push.
    for f in frames[1:]:
        tgt = np.asarray(Image.open(f).convert("L"), dtype=np.float32)
        e, s = best_scale(ref, tgt, 1.0, 2.4, n_scales, sl)
        rows.append({"frame": Path(f).stem, "residual": round(e, 4), "scale": round(s, 4)})
        print(f"  {label:16} {Path(f).stem}  best scale {s:.4f}  residual {e:7.4f}",
              file=sys.stderr)
    return rows


def main() -> int:
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--control")
    ap.add_argument("--inset", type=float, default=0.15)
    ap.add_argument("--scales", type=int, default=241)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    fr = sorted(Path(a.frames).glob("*.png"))
    if len(fr) < 2:
        print(f"need at least 2 frames in {a.frames}", file=sys.stderr)
        return 1
    # Quarter, half, three-quarter, end. Enough to see the trend, cheap enough
    # that there is no excuse to skip the control.
    n = len(fr)
    picks = [fr[0]] + [fr[i] for i in (n // 4, n // 2, 3 * n // 4, n - 1)]

    out = {"tool": "probe-zoom", "frames": a.frames, "inset": a.inset,
           "clip": score(picks, a.inset, a.scales, Path(a.frames).name)}
    out["clipResidual"] = round(float(np.mean([r["residual"] for r in out["clip"]])), 4)

    if a.control:
        # THE FLOOR. One still, zoomed by the scales the clip actually used.
        still = Image.open(a.control).convert("RGB")
        if still.size != Image.open(fr[0]).size:
            still = still.resize(Image.open(fr[0]).size, Image.LANCZOS)
        tmp = Path(a.frames).parent / "_probe_control"
        tmp.mkdir(exist_ok=True)
        for i, r in enumerate([{"scale": 1.0}] + out["clip"]):
            zoom_about_centre(still, r["scale"]).save(tmp / f"{i:05d}.png")
        out["control"] = score(sorted(tmp.glob("*.png")), a.inset, a.scales, "CONTROL")
        out["controlResidual"] = round(
            float(np.mean([r["residual"] for r in out["control"]])), 4)
        out["overFloor"] = round(out["clipResidual"] - out["controlResidual"], 4)
        out["ratio"] = round(out["clipResidual"] / max(out["controlResidual"], 1e-6), 3)

    print(json.dumps(out, indent=2) if a.json else json.dumps(
        {k: v for k, v in out.items() if not isinstance(v, list)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
