#!/usr/bin/env python3
"""Motion heatmaps for the native water cycles: WHAT moves, region by region.

For each built cycle: max |drawing - plate| across the loop, painted red
over the dimmed plate -> native/<id>/motion-heat.png, plus one contact
sheet (evidence-native-water-motion.png). The check this exists for:
only DRAWN WATER may move — never rocks, banks, trestles, or the
collectors' seals sitting on the water silk.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).parent
R = json.loads((HERE / "regions.json").read_text())
tiles = []
for r in R["regions"]:
    d = HERE / "native" / r["id"]
    cj = d / "cycle" / "cycle.json"
    if not cj.exists():
        continue
    n = json.loads(cj.read_text())["drawings"]
    plate = np.array(Image.open(d / "plate.png").convert("L"), np.float32)
    mx = np.zeros_like(plate)
    for i in range(n):
        dr = np.array(Image.open(d / "cycle" / f"dr-{i:03d}.png").convert("L"), np.float32)
        mx = np.maximum(mx, np.abs(dr - plate))
    rgb = np.stack([plate * 0.5] * 3, -1)
    rgb[..., 0] = np.clip(rgb[..., 0] + np.clip(mx * 3, 0, 255), 0, 255)
    im = Image.fromarray(rgb.astype(np.uint8))
    im.save(d / "motion-heat.png")
    s = 430 / max(im.size)
    tiles.append((r["id"], float(mx.mean()), im.resize((int(im.width * s), int(im.height * s)))))
    print(f"{r['id']}: mean dev {mx.mean():.2f}  max {mx.max():.0f}")

cols = 4
cw = max(t[2].width for t in tiles) + 16
ch = max(t[2].height for t in tiles) + 40
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cw, rows * ch), (20, 18, 16))
dr = ImageDraw.Draw(sheet)
for i, (rid, mean, im) in enumerate(tiles):
    cx, cy = (i % cols) * cw + 8, (i // cols) * ch + 30
    sheet.paste(im, (cx, cy))
    dr.text((cx, cy - 22), f"{rid}  (mean dev {mean:.2f})", fill=(240, 236, 228))
sheet.save(HERE / "evidence-native-water-motion.png")
print(json.dumps({"regions": len(tiles), "sheet": "living/evidence-native-water-motion.png"}))
