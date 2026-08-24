"""Outline, never fill (Ryan, 2026-08-24: the solid magenta 'looks like a
toddler went around with a pink marker'). And crop to the WORST case -- the
regions where flux invented actual brushwork, not the ones that are merely
large and blank."""
import sys, json
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

T = sys.argv[1]
real = np.asarray(Image.open(f"{T}/f-real/00335.png").convert("RGB"))
g = np.asarray(Image.open(f"{T}/f-real/00335.png").convert("L")).astype(np.float32)
inv = np.asarray(Image.open(f"{T}/f-marker/00335.png").convert("L")) > 127
H, W = inv.shape
bg = cv2.medianBlur(g.astype(np.uint8), 31).astype(np.float32)
ink = (bg - g) > 12

k = np.ones((3, 3), np.uint8)
m8 = inv.astype(np.uint8)
edge = (cv2.dilate(m8, k, 1, None, 2) - cv2.erode(m8, k, 1, None, 1)) > 0

def draw(img, text, size=26):
    im = Image.fromarray(img.copy()); d = ImageDraw.Draw(im)
    try: f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
    except OSError: f = ImageFont.load_default()
    d.rectangle([0, 0, d.textlength(text, font=f) + 24, size + 18], fill=(0, 0, 0))
    d.text((12, 8), text, font=f, fill=(255, 255, 255))
    return np.asarray(im)

n, lab, stats, cent = cv2.connectedComponentsWithStats(m8, 8)
inked = ink & inv
score = [(int(np.count_nonzero(inked & (lab == i))), i) for i in range(1, n) if stats[i, 4] > 3000]
score.sort(reverse=True)

TILE, chosen = 470, []
for s, i in score:
    cx, cy = cent[i]
    x0 = int(np.clip(cx - TILE // 2, 0, W - TILE)); y0 = int(np.clip(cy - TILE // 2, 0, H - TILE))
    if any(abs(x0 - a) < TILE * 0.8 and abs(y0 - b) < TILE * 0.8 for a, b in [(c[0], c[1]) for c in chosen]):
        continue
    chosen.append((x0, y0, s))
    if len(chosen) == 4: break

tiles = []
for x0, y0, s in chosen:
    t = real[y0:y0 + TILE, x0:x0 + TILE].copy()
    t[edge[y0:y0 + TILE, x0:x0 + TILE]] = (255, 0, 200)
    tiles.append(draw(t, f"{s:,} px of INVENTED INK — 1:1", 22))

out = real.copy(); out[edge] = (255, 0, 200)
top = draw(out, "DEEPEST DOLLY camZ 0.70 — outlines ring INVENTED material: 14.7% of frame, of which 1.85% carries ink", 27)
row = np.hstack(tiles)
if row.shape[1] < top.shape[1]:
    row = np.hstack([row, np.full((row.shape[0], top.shape[1] - row.shape[1], 3), 20, np.uint8)])
row = row[:, :top.shape[1]]
cap = draw(np.full((44, top.shape[1], 3), 20, np.uint8),
           "the four worst regions at 1:1 — ink density inside 12.6% vs 10.75% in the painting right beside it", 24)
Image.fromarray(np.vstack([top, cap, row])).save(
    "jobs/wang-meng/evidence/2026-08-24-invented-material-outlined.png")
print(json.dumps({"tiles": [(int(a), int(b), int(c)) for a, b, c in chosen]}))
