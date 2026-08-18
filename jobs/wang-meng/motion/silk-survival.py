#!/usr/bin/env python3
"""Per frame: how much of the image still carries the PAINTING's tonal signature?

First attempt hand-picked HSV thresholds (V>0.62, S<0.22) and scored frame 0 of
the real painting at 1% — nonsense, since the frame is almost entirely silk. The
scan's silk actually sits at S≈0.27, and S<0.22 is below its 10th percentile. So
the threshold excluded the very thing it was meant to count.

Fixed by refusing to invent the band. Frame 0 of every clip IS the untouched
source image, so the band is measured FROM it: the 5th–95th percentile of
saturation and the 5th percentile of value. Then each later frame is scored as
the fraction of its pixels still inside that band.

Ink on silk is a narrow, warm, low-saturation distribution. Photographic water is
not — it is darker, with a far wider spread. So this number reads directly as
"how much of the painting is left", it is calibrated per clip, and it involves no
model and no magic constants.
"""
import sys, json
import cv2
import numpy as np

def hsv_of(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    return hsv[..., 1] / 255.0, hsv[..., 2] / 255.0

def series(path):
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()

    s0, v0 = hsv_of(frames[0])                       # calibrate on the source frame
    s_lo, s_hi = np.percentile(s0, 5), np.percentile(s0, 95)
    v_lo = np.percentile(v0, 5)
    band = lambda s, v: float(((s >= s_lo) & (s <= s_hi) & (v >= v_lo)).mean())

    vals = []
    for f in frames:
        s, v = hsv_of(f)
        vals.append(round(band(s, v), 5))
    return vals, (float(s_lo), float(s_hi), float(v_lo))

if __name__ == "__main__":
    out = {}
    for arg in sys.argv[1:]:
        name, path = arg.split("=", 1)
        vals, cal = series(path)
        out[name] = vals
        print(f"{name:9s} n={len(vals):3d}  frame0 {vals[0]:.3f} -> final {vals[-1]:.3f}   "
              f"retained {100*vals[-1]/vals[0]:5.1f}%   band S[{cal[0]:.2f},{cal[1]:.2f}] V>{cal[2]:.2f}",
              file=sys.stderr)
    print(json.dumps(out))
