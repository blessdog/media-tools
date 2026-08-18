#!/usr/bin/env python3
"""Split a clip's damage into: inside the protect mask, outside it, and global.

Reconciles two numbers that disagreed on 2026-08-14. The motion heatmap said
92.3% of the control's pixels never moved and the churn was all on the figures.
But stencilling the figures back to the plate recovered only 1.6 points of
silk-survival (89.4 -> 91.0). Both cannot be the whole story.

Candidate explanations, and how this script tells them apart:
  A. the figures are redrawn but stay INSIDE the painting's tonal band -- a
     different old man is still ink on silk -- so silk-survival never counted
     them as lost, and the metric is blind to this failure.
  B. a small UNIFORM tone shift over the whole frame pushes borderline pixels
     out of the band everywhere, with per-pixel motion too small to look hot.

A shows up as: most absolute change inside the mask, but tiny out-of-band change
there. B shows up as: a nonzero median shift in S/V measured OUTSIDE the mask.
"""
import subprocess, sys, json
import numpy as np
import cv2
from PIL import Image

clip, maskdir = sys.argv[1], sys.argv[2]
W, H = 720, 1280

meta = json.load(open(f'{maskdir}/layers.json'))
m = np.zeros((H, W), np.float32)
for pl in meta['planeList']:
    mi = np.array(Image.open(f"{maskdir}/masks/{pl['n']:03d}.png").convert('L'), np.float32) / 255.0
    ox, oy = pl['offset']; mh, mw = mi.shape
    m[oy:oy + mh, ox:ox + mw] = np.maximum(m[oy:oy + mh, ox:ox + mw], mi)
inside = m > 0.5
outside = ~inside

raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', clip, '-f', 'rawvideo',
                      '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
f0, fN = f[0].astype(np.float32), f[-1].astype(np.float32)

d = np.abs(fN - f0).mean(-1)
tot = d.sum()

hsv0 = cv2.cvtColor(f[0], cv2.COLOR_RGB2HSV).astype(np.float32)
hsvN = cv2.cvtColor(f[-1], cv2.COLOR_RGB2HSV).astype(np.float32)
s0, v0 = hsv0[..., 1] / 255, hsv0[..., 2] / 255
sN, vN = hsvN[..., 1] / 255, hsvN[..., 2] / 255
lo, hi, vlo = np.percentile(s0, 5), np.percentile(s0, 95), np.percentile(v0, 5)
in0 = (s0 >= lo) & (s0 <= hi) & (v0 >= vlo)
inN = (sN >= lo) & (sN <= hi) & (vN >= vlo)
left = in0 & ~inN                                   # pixels that FELL OUT of the band

print(json.dumps({
    'clip': clip,
    'maskPct': round(float(inside.mean()) * 100, 2),
    'A_absChange': {
        'insideMaskShareOfTotal': round(float(d[inside].sum() / tot) * 100, 1),
        'outsideMaskShareOfTotal': round(float(d[outside].sum() / tot) * 100, 1),
        'meanInside': round(float(d[inside].mean()), 2),
        'meanOutside': round(float(d[outside].mean()), 2),
    },
    'A_bandLoss': {
        'pixelsLeftBandPct': round(float(left.mean()) * 100, 2),
        'shareOfLossInsideMask': round(float(left[inside].sum() / max(left.sum(), 1)) * 100, 1),
        'maskWouldBeIfProportional': round(float(inside.mean()) * 100, 1),
    },
    'B_globalShift_outsideMaskOnly': {
        'medianDeltaS': round(float(np.median(sN[outside] - s0[outside])), 4),
        'medianDeltaV': round(float(np.median(vN[outside] - v0[outside])), 4),
        'p90AbsDeltaV': round(float(np.percentile(np.abs(vN[outside] - v0[outside]), 90)), 4),
    },
}, indent=2))
