#!/usr/bin/env python3
"""Build a synthetic PURE-ZOOM reference from a clip's own first frame.

The control the eye needs. fix1 measures a 1.41x global scale over 73 frames; this
renders exactly that scale ramp as a flat Ken Burns push on frame 0 alone — no
depth, no model, one image and a crop window. Put the two side by side and any
visible divergence IS the parallax, because that is the only difference between
them by construction.
"""
import sys, os
import numpy as np
from PIL import Image

src, outdir, n_frames, end_scale = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
os.makedirs(outdir, exist_ok=True)
im = Image.open(src).convert("RGB")
W, H = im.size

for i in range(n_frames):
    # linear ramp in scale, matching how the measured global fit was taken end-to-end
    s = 1.0 + (end_scale - 1.0) * (i / (n_frames - 1))
    cw, ch = int(round(W / s)), int(round(H / s))
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    im.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS).save(
        os.path.join(outdir, f"z{i:04d}.png"))
print(f"wrote {n_frames} frames ramping 1.00x -> {end_scale:.2f}x into {outdir}")
