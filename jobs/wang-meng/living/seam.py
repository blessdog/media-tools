#!/usr/bin/env python3
"""Loop-seam metric for any animate-strokes drawings dir.

A cycle that pops at the wrap is not a cycle. Compare the wrap step
(last drawing -> first) against the mean ordinary step; ~1.0 is closed,
>1.2 pops. Reads only the region that actually changes, so a full-plate
drawing set does not need the whole plate in RAM at once.

  seam.py --dir living/plane-cycles/water-drawings [--pattern dr-%03d.png]
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
ap.add_argument("--pattern", default=None)
ap.add_argument("--box", default=None, help="x0,y0,x1,y1 to restrict the read")
a = ap.parse_args()

d = Path(a.dir)
cyc = {}
if (d / "cycle.json").exists():
    cyc = json.loads((d / "cycle.json").read_text())
pat = a.pattern or ("dr-%03d.png" if list(d.glob("dr-*.png")) else "%03d.png")
files = [d / (pat % i) for i in range(cyc.get("drawings", 10_000))]
files = [f for f in files if f.exists()]
if len(files) < 2:
    files = sorted(p for p in d.glob("*.png"))
if len(files) < 2:
    sys.exit(f"no drawings in {d}")

box = tuple(int(v) for v in a.box.split(",")) if a.box else None
def rd(f):
    im = Image.open(f).convert("L")
    if box:
        im = im.crop(box)
    return np.asarray(im, np.int16)

prev = first = rd(files[0])
steps = []
for f in files[1:]:
    cur = rd(f)
    steps.append(float(np.abs(cur - prev).mean()))
    prev = cur
seam = float(np.abs(prev - first).mean())
mean_step = float(np.mean(steps))
print(json.dumps({"dir": str(d), "drawings": len(files),
                  "loopSeam": round(seam, 4),
                  "meanStep": round(mean_step, 4),
                  "maxStep": round(max(steps), 4),
                  "seamOverMean": round(seam / max(mean_step, 1e-9), 3),
                  "seamOverMax": round(seam / max(max(steps), 1e-9), 3)}, indent=1))
