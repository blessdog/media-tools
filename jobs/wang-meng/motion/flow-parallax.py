#!/usr/bin/env python3
"""Zoom or parallax, decided by optical flow instead of residuals.

WHY NOT RESIDUALS: the first attempt scored how badly a single global scale fit
each depth band and read a high near/far ratio as parallax. The static control
(fix4, "nothing moves") produced a ratio of 1.75 with NO camera motion at all,
which killed that method — the ratio tracks where fine DETAIL sits in the frame,
because detail drift dominates the residual. Measured 2026-08-13.

THE REAL TEST. Under a pure zoom about the optical centre, every pixel flows
radially outward and its speed is exactly proportional to its distance from the
centre. So the ratio

    expansion = |flow| / radius

is a CONSTANT over the whole frame, whatever the content. Under true parallax a
near surface sweeps outward faster than a far surface at the same radius, so
expansion rises toward the near part of the scene. In a 高遠 scroll near is the
bottom of the frame and far is the top, so a vertical gradient in expansion is
the signature we want.

Reported: expansion per horizontal band, bottom-vs-top ratio, and the spread of
expansion within a fixed radius annulus (which removes the radius term entirely).
"""
import sys
import cv2
import numpy as np

def flow_between(p0, p1):
    a = cv2.imread(p0, cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(p1, cv2.IMREAD_GRAYSCALE)
    return cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 4, 31, 5, 7, 1.5, 0), a.shape

def main(p0, p1, label):
    flow, (H, W) = flow_between(p0, p1)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2.0, H / 2.0
    dx, dy = xs - cx, ys - cy
    r = np.sqrt(dx * dx + dy * dy)

    # radial component of flow (positive = moving away from centre)
    with np.errstate(invalid="ignore", divide="ignore"):
        ux, uy = dx / r, dy / r
        radial = flow[..., 0] * ux + flow[..., 1] * uy
        expansion = radial / r

    valid = (r > 0.18 * min(H, W)) & np.isfinite(expansion)
    print(f"--- {label}")
    print(f"    mean expansion {np.nanmean(expansion[valid]):+.5f} /px "
          f"(positive = pushing in)")

    # expansion by horizontal band: in a gaoyuan frame, bottom = near, top = far
    bands = []
    for i, name in enumerate(["top(far)", "upper", "lower", "bottom(near)"]):
        s = slice(i * H // 4, (i + 1) * H // 4)
        m = valid[s]
        v = float(np.nanmean(expansion[s][m])) if m.any() else float("nan")
        bands.append(v)
        print(f"    {name:>13}: {v:+.5f}")
    if np.isfinite(bands[0]) and abs(bands[0]) > 1e-6:
        print(f"    near/far expansion ratio: {bands[3] / bands[0]:.2f}   "
              f"(1.00 = pure zoom)")

    # annulus check: same radius, so a pure zoom must give near-zero spread
    ann = valid & (r > 0.28 * min(H, W)) & (r < 0.34 * min(H, W))
    if ann.sum() > 500:
        e = expansion[ann]
        print(f"    within one annulus: mean {np.nanmean(e):+.5f}  "
              f"sd {np.nanstd(e):.5f}  sd/mean {abs(np.nanstd(e)/np.nanmean(e)):.2f}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "clip")
