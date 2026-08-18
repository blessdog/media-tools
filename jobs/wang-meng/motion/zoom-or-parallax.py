#!/usr/bin/env python3
"""Is a forward-push clip a pure ZOOM, or does it have real parallax?

A pure zoom means the last frame is exactly the first frame, centre-cropped and
scaled — one global transform explains everything. Real Z-motion means near
things grow FASTER than far things, so no single scale can reconcile the two.

Method: search scale factors, centre-crop frame0 by each, resize to full, and
score against the last frame. Then compare the best global fit's residual in
the NEAR region (bottom third — bridge, foreground rock) against the FAR region
(top third — distant rocks, water). Under a pure zoom both residuals are equally
low. Under parallax the near band fits worse, because it moved more than the
global scale accounts for.
"""
import sys
import numpy as np
from PIL import Image

def load(p):
    return np.asarray(Image.open(p).convert("L"), dtype=np.float32) / 255.0

def crop_scale(img, s):
    H, W = img.shape
    ch, cw = int(H / s), int(W / s)
    y0, x0 = (H - ch) // 2, (W - cw) // 2
    sub = Image.fromarray((img[y0:y0 + ch, x0:x0 + cw] * 255).astype(np.uint8))
    return np.asarray(sub.resize((W, H), Image.BICUBIC), dtype=np.float32) / 255.0

if __name__ == "__main__":
    a, b = load(sys.argv[1]), load(sys.argv[2])
    H, W = a.shape

    best = None
    for s in np.arange(1.00, 1.61, 0.01):
        r = float(np.abs(crop_scale(a, s) - b).mean())
        if best is None or r < best[1]:
            best = (float(s), r)
    s, resid = best
    print(f"best global scale : {s:.2f}x   mean abs residual {resid:.4f}")

    warped = crop_scale(a, s)
    d = np.abs(warped - b)
    far  = float(d[: H // 3].mean())          # top third  — distant
    mid  = float(d[H // 3 : 2 * H // 3].mean())
    near = float(d[2 * H // 3 :].mean())      # bottom third — foreground
    print(f"residual by depth band  far {far:.4f} | mid {mid:.4f} | near {near:.4f}")
    print(f"near/far ratio     : {near / far:.2f}")
    print()
    if near / far > 1.35:
        print("=> NEAR band fits the global zoom notably worse than FAR.")
        print("   Consistent with real parallax: foreground moved more than one scale explains.")
    else:
        print("=> Both bands fit the same single scale about equally well.")
        print("   Consistent with a PURE ZOOM — i.e. Ken Burns, rendered the expensive way.")
