#!/usr/bin/env python3
"""media-tools — render-living: a camera window over the living master → frames.

One job. It composites per-region animation cycles onto the master painting
inside a moving window and writes frames. It does not cut masks, animate
strokes, add parallax, grade, or encode video (ffmpeg's job).

THE LIVING LAYER IS DATA, NOT BAKED FRAMES. A 105-megapixel scroll times N
frames is absurd to store; instead each region carries a small cycle (a
folder of tiles) and this tool pastes only the cycles intersecting the
window, per frame, in master space at native resolution — then resamples
the window to the output frame. Cost is O(window), not O(painting).

Camera path JSON: the SAME schema as render-parallax (keys of t,x,y,fov,
smoothstep between keys). x,y are the WINDOW CENTER normalised on the
master. This engine is 2D — Ken Burns grammar — so `z` is ignored (warned
once); zoom is `fov`: the window is (width*k*fov, height*k*fov) master px,
fov 1.0 at --k 1.0 meaning native pixels.

Regions JSON: see jobs/wang-meng/living/regions.json. A region animates
only when it has "cycle": {"dir": <frames dir, %05d.png>, "box":
[x0,y0,x1,y1 master px], "n": <frame count>, "on": <hold, default 1>}.
Tiles are resized to the box if recorded at another scale. Cycle frame
index = (output frame // on) mod n — "on": 2 plays a 36-drawing cycle
on twos, the cel idiom animate-strokes authors.

usage:
  render-living.py --master IMG --regions REGIONS.json --path PATH.json \
                   --out DIR [--width 1920] [--height 1080] [--fps 24] \
                   [--duration S] [--k 1.0] [--stills] [--preview N]

JSON on stdout. Progress on stderr.
"""
import argparse, json, sys
from pathlib import Path
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def smoothstep(a, b, t):
    t = t * t * (3 - 2 * t)
    return a + (b - a) * t


def sample(keys, t):
    if t <= keys[0]["t"]:
        return keys[0]
    if t >= keys[-1]["t"]:
        return keys[-1]
    for k0, k1 in zip(keys, keys[1:]):
        if k0["t"] <= t <= k1["t"]:
            u = (t - k0["t"]) / (k1["t"] - k0["t"])
            return {f: smoothstep(k0.get(f, 0.0), k1.get(f, 1.0 if f == "fov" else 0.0), u)
                    for f in ("x", "y", "fov")}
    return keys[-1]


ap = argparse.ArgumentParser()
ap.add_argument("--master", required=True)
ap.add_argument("--regions", required=True)
ap.add_argument("--path", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--width", type=int, default=1920)
ap.add_argument("--height", type=int, default=1080)
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--duration", type=float, default=None)
ap.add_argument("--k", type=float, default=1.0, help="master px per output px at fov 1.0")
ap.add_argument("--stills", action="store_true", help="first/middle/last only")
ap.add_argument("--preview", type=int, default=1, help="render every Nth frame")
a = ap.parse_args()

master = Image.open(a.master).convert("RGB")
MW, MH = master.size
R = json.loads(Path(a.regions).read_text())
P = json.loads(Path(a.path).read_text())
keys = P["keys"]
if any("z" in k and k["z"] for k in keys):
    print("note: z in path is ignored — render-living is 2D; zoom is fov", file=sys.stderr)
fps = P.get("fps", a.fps)
duration = a.duration or P.get("duration", 12)
n_frames = round(duration * fps)

cycles = []
for r in R["regions"]:
    c = r.get("cycle")
    if not c:
        continue
    d = Path(a.regions).parent / c["dir"] if not Path(c["dir"]).is_absolute() else Path(c["dir"])
    x0, y0, x1, y1 = c["box"]
    cycles.append({"id": r["id"], "dir": d, "n": c["n"], "on": c.get("on", 1),
                   "pattern": c.get("pattern", "%05d.png"),
                   "box": (x0, y0, x1, y1)})
print(f"living regions with cycles: {[c['id'] for c in cycles]}", file=sys.stderr)

out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)

todo = range(0, n_frames, a.preview)
if a.stills:
    todo = [0, n_frames // 2, n_frames - 1]

tile_cache = {}
for i in todo:
    t = i / fps
    cam = sample(keys, t)
    ww = a.width * a.k * cam.get("fov", 1.0)
    wh = a.height * a.k * cam.get("fov", 1.0)
    cx, cy = cam["x"] * MW, cam["y"] * MH
    x0 = min(max(0.0, cx - ww / 2), MW - ww)
    y0 = min(max(0.0, cy - wh / 2), MH - wh)
    ix0, iy0 = int(round(x0)), int(round(y0))
    iw, ih = int(round(ww)), int(round(wh))
    win = master.crop((ix0, iy0, ix0 + iw, iy0 + ih))
    for c in cycles:
        bx0, by0, bx1, by1 = c["box"]
        if bx1 <= ix0 or bx0 >= ix0 + iw or by1 <= iy0 or by0 >= iy0 + ih:
            continue
        fi = (i // c["on"]) % c["n"]   # cycles authored on twos hold each drawing
        key = (c["id"], fi)
        if key not in tile_cache:
            tile = Image.open(c["dir"] / (c["pattern"] % fi)).convert("RGB")
            if tile.size != (bx1 - bx0, by1 - by0):
                tile = tile.resize((bx1 - bx0, by1 - by0), Image.Resampling.LANCZOS)
            tile_cache.clear()  # hold one frame's tiles at a time; masters are big
            tile_cache[key] = tile
        win.paste(tile_cache[key], (bx0 - ix0, by0 - iy0))
    if win.size != (a.width, a.height):
        win = win.resize((a.width, a.height), Image.Resampling.LANCZOS)
    win.save(out / f"{i:05d}.png")
    if i % (10 * a.preview) == 0:
        print(f"  {i}/{n_frames}  t={t:.2f}s", file=sys.stderr)

print(json.dumps({"tool": "render-living", "out": str(out), "frames": len(list(todo)),
                  "size": [a.width, a.height], "fps": fps, "duration": duration,
                  "cycles": [c["id"] for c in cycles]}))
