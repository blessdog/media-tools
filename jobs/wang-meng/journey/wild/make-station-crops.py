#!/usr/bin/env python3
"""v2 (station-anchored): cut a 1280x720 anchor crop from the REAL scroll at
each segment's starting station. Segment SN starts at station N (S1 already
exists from the pilot). 2560x1440 window centered on the station dot, clamped
to the scroll, scaled to 1280x720 — same recipe as the S1 anchor."""
import json, subprocess, pathlib

root = pathlib.Path(__file__).resolve()
wild = root.parent
job = wild.parent.parent          # jobs/wang-meng
repo = job.parent.parent          # media-tools
scroll = repo / "corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png"
W, H = 6586, 15923
CW, CH = 2560, 1440

stations = {s["id"]: s for s in json.load(open(job / "journey/stations.json"))["stations"]}

for seg_n in range(2, 11):                      # S2..S10 start at station 2..10
    st = stations[seg_n]
    x0 = min(max(st["mx"] - CW // 2, 0), W - CW)
    y0 = min(max(st["my"] - CH // 2, 0), H - CH)
    out = wild / f"S{seg_n}" / "input-station.png"
    out.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(scroll),
                    "-vf", f"crop={CW}:{CH}:{x0}:{y0},scale=1280:720",
                    str(out)], check=True)
    print(f"S{seg_n}  station {seg_n} ({st['name']})  crop @ {x0},{y0}  -> {out.relative_to(repo)}")
