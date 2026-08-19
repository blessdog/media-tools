#!/usr/bin/env python3
"""z2/remap-points: global labelled dots -> Z2 plate points.json + overlay.

Same move that built Z1's zone points (STATE.md 2026-08-17): select the
master-normalised dots inside the zone rect, renormalise onto the plate,
window divided by k (master px -> plate px, hand-tightened later during
SAM verification). Dots over continuous wash are kept but flagged in the
note — Z1 measured that wash has no contour for SAM (bank-ledge,
porter-ledge dropped there); the sealing pass claims their territory.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
JOB = HERE.parent.parent          # jobs/wang-meng
MW, MH = 6586, 15923
K = 2.34
RECT = (0, 8428, 2383, 13762)     # zone-rect.py --ids 4-5, camera-world rule

WASH_FLAGS = {"bank-ledge-below-bridge", "porter-ledge"}  # Z1's measured SAM failures

g = json.loads((JOB / "points.json").read_text())
x0, y0, x1, y1 = RECT
pts = []
for p in g["points"]:
    mx, my = p["x"] * MW, p["y"] * MH
    if not (x0 <= mx <= x1 and y0 <= my <= y1):
        continue
    pts.append({
        "id": p["id"],
        "x": round((mx - x0) / (x1 - x0), 5),
        "y": round((my - y0) / (y1 - y0), 5),
        "depth": p["depth"],
        "window": round(p["window"] / K),
        "name": p["name"],
        "why": p.get("why", ""),
    })

out = {
    "image": "jobs/wang-meng/journey/z2/plate.png",
    "note": ("Z2 subset of the labelled global dots, remapped master->plate "
             "(rect 0,8428,2383,13762 = camera-world rule on stations 4-5). "
             "depth 0 = farthest. DRAFT: windows are global/k, untested against "
             "SAM. Wash-flagged dots (bank-ledge-below-bridge, porter-ledge) "
             "kept for depth intent but expected to seal by proximity, not "
             "segment — Z1 measured wash has no contour. Upper band y<0.30 "
             "(approach to the rapids corridor) is thin — top-up pass in "
             "pick.html before segmenting."),
    "points": sorted(pts, key=lambda q: -q["depth"]),
}
(HERE / "points.json").write_text(json.dumps(out, indent=1))

# ---- overlay for Ryan's eyes: numbered dots, warm(near) -> cool(far) ----
plate = Image.open(HERE / "plate.png").convert("RGB")
W, H = plate.size
d = ImageDraw.Draw(plate)
depths = [p["depth"] for p in pts]
dmin, dmax = min(depths), max(depths)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
except OSError:
    font = ImageFont.load_default()
for p in out["points"]:
    cx, cy = p["x"] * W, p["y"] * H
    t = (p["depth"] - dmin) / max(1, dmax - dmin)   # 1 = nearest
    col = (int(60 + 195 * t), int(90 + 40 * (1 - t)), int(220 - 170 * t))
    r = 16
    ring = (255, 80, 80) if p["name"] in WASH_FLAGS else (0, 0, 0)
    d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=ring)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    label = f'{p["id"]} {p["name"]} d{p["depth"]}'
    tw = d.textlength(label, font=font)
    tx = cx - r - 6 - tw if cx + r + 6 + tw > W else cx + r + 6
    d.text((tx, cy - 14), label, fill=(255, 255, 240), font=font,
           stroke_width=2, stroke_fill=(0, 0, 0))
plate.save(HERE / "points-overlay.png")
print(json.dumps({"points": len(pts), "overlay": "points-overlay.png",
                  "washFlagged": sorted(WASH_FLAGS & {p['name'] for p in pts})}, indent=1))
