#!/usr/bin/env python3
"""Parallax test, attempt three. Fit out the whole rigid camera first.

ATTEMPT 1 (zoom-or-parallax.py) scored a single global SCALE per depth band and
read the near/far residual ratio as parallax. The static control produced 1.75
with no motion, so that ratio was measuring detail drift. Dead.

ATTEMPT 2 (flow-parallax.py) used |flow|/radius, which is constant under a pure
zoom. But it is NOT constant under a pure TRANSLATION: a uniform flow projected
onto the radial direction varies as the cosine of the angle between the
translation and the radius, so a drifting camera fakes the same signature. The
side-by-side against a synthetic zoom showed fix1's camera does drift up-left.
So attempt 2 cannot separate drift from depth either.

ATTEMPT 3, here. A rigid camera looking at a FLAT picture produces flow that is
fully explained by scale + translation:

    flow(p) = (s - 1)(p - c) + t

Fit s and t over the whole frame by least squares. Whatever flow is LEFT OVER
cannot come from any global camera move over a flat plane — the only things that
generate it are real depth (near surfaces moving differently from far ones) and
noise/detail drift. The static control gives the noise floor for free, since it
has no camera motion at all: anything at or below its residual is nothing.

Then: does the leftover correlate with depth? In a 高遠 frame near is the bottom.
"""
import sys
import cv2
import numpy as np

def analyse(p0, p1, label, floor=None):
    a = cv2.imread(p0, cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(p1, cv2.IMREAD_GRAYSCALE)
    flow = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 4, 31, 5, 7, 1.5, 0)
    H, W = a.shape
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
    cx, cy = W / 2.0, H / 2.0
    dx, dy = (xs - cx).ravel(), (ys - cy).ravel()
    fx, fy = flow[..., 0].ravel().astype(np.float64), flow[..., 1].ravel().astype(np.float64)

    # least squares for k=(s-1), tx, ty:  fx = k*dx + tx ; fy = k*dy + ty
    #   [dx 1 0][k ]
    #   [dy 0 1][tx]
    n = dx.size
    A = np.zeros((2 * n, 3))
    A[0::2, 0], A[0::2, 1] = dx, 1.0
    A[1::2, 0], A[1::2, 2] = dy, 1.0
    rhs = np.empty(2 * n)
    rhs[0::2], rhs[1::2] = fx, fy
    (k, tx, ty), *_ = np.linalg.lstsq(A, rhs, rcond=None)

    rx = (fx - (k * dx + tx)).reshape(H, W)
    ry = (fy - (k * dy + ty)).reshape(H, W)
    resid = np.sqrt(rx * rx + ry * ry)

    print(f"--- {label}")
    print(f"    fitted rigid camera : scale {1+k:.4f}  translation ({tx:+.2f}, {ty:+.2f}) px/frame")
    print(f"    residual after fit  : {resid.mean():.4f} px  "
          f"(what no flat-plane camera move can explain)")
    bands = [resid[i * H // 4:(i + 1) * H // 4].mean() for i in range(4)]
    print(f"    by band  far {bands[0]:.4f} | {bands[1]:.4f} | {bands[2]:.4f} | near {bands[3]:.4f}")
    if floor is not None:
        print(f"    vs control noise floor {floor:.4f}  →  "
              f"{resid.mean() / floor:.2f}x the floor")
    return resid.mean()

if __name__ == "__main__":
    # control first: its residual IS the noise floor
    floor = analyse(sys.argv[1], sys.argv[2], "fix4 CONTROL (no camera motion)")
    print()
    for i in range(3, len(sys.argv), 3):
        analyse(sys.argv[i], sys.argv[i + 1], sys.argv[i + 2], floor)
        print()
