#!/usr/bin/env python3
"""stage-zone: cut a zone's plate and remap the global labelled dots into it.

Generalizes z2/remap-points.py (same transform: master-normalised dots ->
plate-normalised, window/k). One zone per call; rect comes from
zone-rect.py (camera-world rule). The picker clone and top-up remain the
human step at each zone's turn.

usage: stage-zone.py --zone z3 --rect x0,y0,x1,y1
"""
import argparse, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent          # journey/
JOB = HERE.parent                     # jobs/wang-meng
ROOT = JOB.parent.parent              # media-tools
MASTER = ROOT / "corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png"
MW, MH, K = 6586, 15923, 2.34
WASH_FLAGS = {"bank-ledge-below-bridge", "porter-ledge"}

ap = argparse.ArgumentParser()
ap.add_argument("--zone", required=True)
ap.add_argument("--rect", required=True)
a = ap.parse_args()
x0, y0, x1, y1 = (int(v) for v in a.rect.split(","))
zd = HERE / a.zone
zd.mkdir(exist_ok=True)

subprocess.run(["python3", str(ROOT / "tools/crop-region.py"), "--master", str(MASTER),
                "--rect", a.rect, "--k", str(K), "--out", str(zd / "plate.png")],
               check=True, cwd=ROOT, capture_output=True)

g = json.loads((JOB / "points.json").read_text())
pts = []
for p in g["points"]:
    mx, my = p["x"] * MW, p["y"] * MH
    if not (x0 <= mx <= x1 and y0 <= my <= y1):
        continue
    pts.append({"id": p["id"], "x": round((mx - x0) / (x1 - x0), 5),
                "y": round((my - y0) / (y1 - y0), 5), "depth": p["depth"],
                "window": round(p["window"] / K), "name": p["name"],
                "why": p.get("why", "")})
out = {"image": f"jobs/wang-meng/journey/{a.zone}/plate.png",
       "note": (f"{a.zone} subset of the global labelled dots, remapped "
                f"master->plate (rect {a.rect}, camera-world rule). depth 0 = "
                "farthest. DRAFT: windows=global/k, untested vs SAM; wash-"
                "flagged dots seal by proximity. Top-up pass in pick.html "
                "before segmenting."),
       "points": sorted(pts, key=lambda q: -q["depth"])}
(zd / "points.json").write_text(json.dumps(out, indent=1))

plate = Image.open(zd / "plate.png").convert("RGB")
W, H = plate.size
d = ImageDraw.Draw(plate)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
except OSError:
    font = ImageFont.load_default()
depths = [p["depth"] for p in pts] or [0]
dmin, dmax = min(depths), max(depths)
for p in out["points"]:
    cx, cy = p["x"] * W, p["y"] * H
    t = (p["depth"] - dmin) / max(1, dmax - dmin)
    col = (int(60 + 195 * t), int(90 + 40 * (1 - t)), int(220 - 170 * t))
    ring = (255, 80, 80) if p["name"] in WASH_FLAGS else (0, 0, 0)
    d.ellipse([cx - 19, cy - 19, cx + 19, cy + 19], fill=ring)
    d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=col)
    label = f'{p["id"]} {p["name"]} d{p["depth"]}'
    tw = d.textlength(label, font=font)
    tx = cx - 22 - tw if cx + 22 + tw > W else cx + 22
    d.text((tx, cy - 14), label, fill=(255, 255, 240), font=font,
           stroke_width=2, stroke_fill=(0, 0, 0))
plate.save(zd / "points-overlay.png")
print(json.dumps({"zone": a.zone, "plate": [W, H], "dots": len(pts)}))
