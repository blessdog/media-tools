#!/usr/bin/env python3
"""Static-vs-living A/B for one authored water body, at plate resolution.

The control is the same crop held still for the same number of frames, so the
only difference between the two halves is the cycle. Also reports the LOOP SEAM
(mean abs diff between the last drawing and the first): a cycle that pops at the
wrap is not a cycle.

  ab-cycle.py --zone z3w --region w-midstream-pool [--seconds 6] [--out X.mp4]
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
JOB = HERE.parent
ap = argparse.ArgumentParser()
ap.add_argument("--zone", required=True)
ap.add_argument("--region", required=True)
ap.add_argument("--seconds", type=float, default=6.0)
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--out", default=None)
a = ap.parse_args()

wd = JOB / "journey" / a.zone / "living-work" / a.region
cyc = json.loads((wd / "drawings" / "cycle.json").read_text())
draw = [Image.open(wd / "drawings" / f"dr-{i:03d}.png").convert("RGB")
        for i in range(cyc["drawings"])]
base = Image.open(wd / "plate.png").convert("RGB")
W, H = base.size
arr = [np.array(d, np.int16) for d in draw]
seam = float(np.abs(arr[-1] - arr[0]).mean())
step = float(np.mean([np.abs(arr[i + 1] - arr[i]).mean() for i in range(len(arr) - 1)]))

frames = wd / "ab"
frames.mkdir(exist_ok=True)
n = int(a.seconds * a.fps)
for i in range(n):
    ti = (i // cyc["on"]) % cyc["drawings"]
    sheet = Image.new("RGB", (W * 2 + 16, H + 28), (245, 243, 236))
    sheet.paste(base, (0, 28))
    sheet.paste(draw[ti], (W + 16, 28))
    d = ImageDraw.Draw(sheet)
    d.text((6, 8), "STATIC (control)", fill=(30, 30, 30))
    d.text((W + 22, 8), f"LIVING  {a.region}", fill=(160, 20, 20))
    sheet.save(frames / f"{i:05d}.png")

out = a.out or str(JOB / "living" / f"AB-{a.zone}-{a.region}.mp4")
subprocess.run(["ffmpeg", "-y", "-framerate", str(a.fps), "-i",
                str(frames / "%05d.png"), "-c:v", "libx264", "-crf", "16",
                "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                out], check=True, capture_output=True)
print(json.dumps({"out": out, "drawings": cyc["drawings"], "on": cyc["on"],
                  "loopSeam": round(seam, 4), "meanStep": round(step, 4),
                  "seamOverStep": round(seam / max(step, 1e-6), 3)}, indent=1))
