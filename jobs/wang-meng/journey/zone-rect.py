#!/usr/bin/env python3
"""zone-rect: route-leg stations -> the camera-world rect that contains them.

A zone rect must hold every FRAME, not just every station: dilate the leg's
bounding box by half the output frame plus disocclusion reach, in master px,
then clamp to the master. Reach 250 region px covers the measured envelope
(wander 0.5 needs 150 px) with slack for z-pushes.

usage: zone-rect.py --world world.json --stations stations.json --ids 1-4
"""
import argparse, json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--world", required=True)
ap.add_argument("--stations", required=True)
ap.add_argument("--ids", required=True, help="e.g. 1-4")
ap.add_argument("--reach", type=int, default=250, help="region px of slack")
a = ap.parse_args()

w = json.loads(Path(a.world).read_text())
k, (FW, FH) = w["k"], w["frame"]
MW, MH = w["masterSize"]
lo, hi = (int(v) for v in a.ids.split("-"))
pts = [s for s in json.loads(Path(a.stations).read_text())["stations"]
       if lo <= s["id"] <= hi]
xs, ys = [s["mx"] for s in pts], [s["my"] for s in pts]
dx = (FW / 2 + a.reach) * k
dy = (FH / 2 + a.reach) * k
rect = [max(0, round(min(xs) - dx)), max(0, round(min(ys) - dy)),
        min(MW, round(max(xs) + dx)), min(MH, round(max(ys) + dy))]
size = [round((rect[2] - rect[0]) / k), round((rect[3] - rect[1]) / k)]
print(json.dumps({"ids": a.ids, "rect": rect, "regionSize": size,
                  "stations": [s["name"] for s in pts]}, indent=2))
