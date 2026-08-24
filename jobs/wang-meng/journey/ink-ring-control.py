"""The whole-frame comparison is unfair: the painted population includes Ge
Hong's robe and the empty river, both nearly flat, which drags its ink density
down. The honest null is the painted material IMMEDIATELY ADJACENT to each
invented region -- same neighbourhood, same subject, differing only in who
painted it."""
import sys, json
import numpy as np, cv2
from PIL import Image

T = sys.argv[1]
g = np.asarray(Image.open(f"{T}/f-real/00335.png").convert("L")).astype(np.float32)
inv = np.asarray(Image.open(f"{T}/f-marker/00335.png").convert("L")) > 127
bg = cv2.medianBlur(g.astype(np.uint8), 31).astype(np.float32)
ink = (bg - g) > 12

k = np.ones((3, 3), np.uint8)
m8 = inv.astype(np.uint8)
ring = (cv2.dilate(m8, k, iterations=12) > 0) & ~inv     # ~36px collar of real painting

print(json.dumps({
    "inkDensityInvented": round(100.0 * ink[inv].mean(), 2),
    "inkDensityAdjacentPainted": round(100.0 * ink[ring].mean(), 2),
    "ringPx": int(ring.sum()),
    "framePctInventedInk": round(100.0 * (ink & inv).sum() / inv.size, 2),
    "framePctInventedBlank": round(100.0 * (inv & ~ink).sum() / inv.size, 2),
}, indent=1))
