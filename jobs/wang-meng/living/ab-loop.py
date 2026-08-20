#!/usr/bin/env python3
"""Side-by-side A/B of two cycles over the SAME crop, played through the wrap.

The wrap is the whole point, so the clip runs at least two full cycles and a
label counts them down -- a pop at the loop is a thing you see once per cycle
and never in a single pass.

  ab-loop.py --crop x0,y0,x1,y1 --a LABEL:DIR --b LABEL:DIR --out X.mp4
"""
import argparse, json, subprocess, shutil
from pathlib import Path
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
ap = argparse.ArgumentParser()
ap.add_argument("--crop", required=True)
ap.add_argument("--a", required=True)
ap.add_argument("--b", required=True)
ap.add_argument("--cycles", type=float, default=2.0)
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--out", required=True)
ap.add_argument("--work", default=None)
a = ap.parse_args()

x0, y0, x1, y1 = (int(v) for v in a.crop.split(","))
def load(spec):
    label, d = spec.split(":", 1)
    d = Path(d)
    cyc = json.loads((d / "cycle.json").read_text())
    fr = [Image.open(d / f"dr-{i:03d}.png").convert("RGB").crop((x0, y0, x1, y1))
          for i in range(cyc["drawings"])]
    return label, fr, cyc["on"]

(la, fa, ona), (lb, fb, onb) = load(a.a), load(a.b)
W, H = fa[0].size
work = Path(a.work or (Path(a.out).parent / "_abloop"))
if work.exists():
    shutil.rmtree(work)
work.mkdir(parents=True)

n = int(a.cycles * max(len(fa) * ona, len(fb) * onb))
for i in range(n):
    sheet = Image.new("RGB", (W * 2 + 16, H + 30), (246, 244, 238))
    sheet.paste(fa[(i // ona) % len(fa)], (0, 30))
    sheet.paste(fb[(i // onb) % len(fb)], (W + 16, 30))
    d = ImageDraw.Draw(sheet)
    d.text((6, 9), la, fill=(176, 42, 42))
    d.text((W + 22, 9), lb, fill=(26, 106, 62))
    cyc_no = i // (len(fa) * ona) + 1
    d.text((W * 2 - 78, 9), f"cycle {cyc_no}", fill=(120, 118, 112))
    sheet.save(work / f"{i:05d}.png")

subprocess.run(["ffmpeg", "-y", "-framerate", str(a.fps), "-i",
                str(work / "%05d.png"), "-c:v", "libx264", "-crf", "16",
                "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                a.out], check=True, capture_output=True)
shutil.rmtree(work)
print(json.dumps({"out": a.out, "frames": n, "crop": [x0, y0, x1, y1]}))
