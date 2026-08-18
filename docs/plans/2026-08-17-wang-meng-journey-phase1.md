# Wang Meng Journey — Phase 1 (World + Z1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **HUMAN-GATED:** Tasks 3, 4 and 6 contain steps only Pissjug can do (click pass, visual verdicts). A subagent must STOP at those steps and report back; never fake or skip a verdict.

**Goal:** `world.json` + the Z1 (river+bridge) zone world planed at full camera footprint, journey spline through stations 1–4, and a watchable Z1 flythrough that passes all controls.

**Architecture:** Phase 1 of `docs/specs/2026-08-17-wang-meng-journey-design.md` (approach B: 散点透視 zone worlds). Everything speaks master pixels; the zone is cut from the 6586×15923 master at k=2.34 with recorded provenance; depth is authored by clicked points, never estimated; the camera path is authored once in master coords and mapped into the zone.

**Tech Stack:** Python 3 (PIL, numpy, cv2), SAM via `segment-points.py` (mps), Flux Fill via `inpaint-planes.py --method flux` (Replicate), `render-parallax.py`, ffmpeg. No new dependencies.

## Global Constraints

- Tool contract (CLAUDE.md): one job per tool; explicit I/O by flags; `--help` is the contract — READ IT before calling any tool; JSON on stdout, progress on stderr; composition lives in job scripts.
- Depth is never estimated on this material (measured failure: 48.9% R² vs row on the painting). Authored depths only.
- No generated territory. Models fill only occlusion bands behind planes. Frame-zero control: 0 px changed at rest, every stack transform.
- Every visual claim is a rendered file `open`ed on Pissjug's screen. His eyes are the verdict; never declare a render good unread.
- All paths inside JSON sidecars are relative to the JSON file's own directory.
- Working scale k=2.34 master px per rendered px; output 720×1280 vertical.
- Commit or push only at the commit steps written here; small commits, search-bait subjects.
- Master: `corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png` (gitignored data; never committed).
- Job root for this phase: `jobs/wang-meng/journey/`.

---

### Task 1: `crop-region --rect` mode

Cut an arbitrary master rect at scale k, not just a growth of an existing crop.json. Same tool, same sidecar shape, new addressing mode.

**Files:**
- Modify: `tools/crop-region.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `crop-region.py --master P --rect x0,y0,x1,y1 --k 2.34 --out R.png` → `R.png` + `R.json` sidecar with `masterBox [x0,y0,x1,y1]`, `masterPxPerRegionPx k`, `size [w,h]`. Task 3 cuts the Z1 plate with this; Task 5's `map-path.py` reads the sidecar.

- [ ] **Step 1: Make `--crop` optional and add `--rect`/`--k`**

In `tools/crop-region.py`, replace the argparse block (lines 41–47) with:

```python
p = argparse.ArgumentParser()
p.add_argument('--master', required=True)
p.add_argument('--crop', help='crop.json from locate-crop (grow mode)')
p.add_argument('--rect', help='x0,y0,x1,y1 in MASTER px (rect mode)')
p.add_argument('--k', type=float, help='master px per region px (rect mode)')
p.add_argument('--out', required=True)
for side in ('left', 'right', 'up', 'down'):
    p.add_argument(f'--{side}', type=int, default=0, help=f'shot px of painting to add {side}')
a = p.parse_args()

if bool(a.rect) == bool(a.crop):
    raise SystemExit('exactly one of --crop (grow mode) or --rect + --k (rect mode)')
if a.rect and not a.k:
    raise SystemExit('--rect needs --k (master px per region px)')
```

Then replace the transform block (lines 49–57) with:

```python
if a.crop:
    meta = json.load(open(a.crop))
    C = meta['crop']
    k = C['masterPxPerShotPx']
    SW, SH = meta['shotSize']
    mx0 = C['x'] - a.left * k
    my0 = C['y'] - a.up * k
    mx1 = C['x'] + C['w'] + a.right * k
    my1 = C['y'] + C['h'] + a.down * k
else:
    k = a.k
    mx0, my0, mx1, my1 = (float(v) for v in a.rect.split(','))
    SW = SH = None
```

And make the sidecar's shot fields conditional — replace lines 69–75 with:

```python
side = {'tool': 'crop-region', 'out': a.out, 'size': [w, h],
        'master': a.master, 'masterBox': [int(mx0), int(my0), int(round(mx1)), int(round(my1))],
        'masterPxPerRegionPx': k}
if SW is not None:
    side.update({'shotOffset': [a.left, a.up],
                 'shotWindowInRegion': [a.left, a.up, a.left + SW, a.up + SH],
                 'note': 'add shotOffset to any mask cut against the original shot; pass it to '
                         'clean-plate / walk-figure as --mask-offset'})
```

Update the docstring usage block to show both modes (keep the WHY prose; add one rect-mode example line: `crop-region.py --master scroll.png --rect 0,9596,4613,15923 --k 2.34 --out z1/plate.png`).

- [ ] **Step 2: Verify rect mode against a PIL reference crop**

```bash
cd /Users/SSDrive/projects/media-tools
python3 tools/crop-region.py --master "corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png" \
  --rect 1000,2000,3340,4340 --k 2.34 --out /tmp/rect-test.png
python3 - <<'PY'
import json
from PIL import Image
import numpy as np
Image.MAX_IMAGE_PIXELS = None
s = json.load(open('/tmp/rect-test.json'))
assert s['masterBox'] == [1000, 2000, 3340, 4340], s['masterBox']
assert s['size'] == [1000, 1000], s['size']          # 2340/2.34
m = Image.open("corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png").convert('RGB')
ref = np.asarray(m.crop((1000, 2000, 3340, 4340)).resize((1000, 1000), Image.LANCZOS))
got = np.asarray(Image.open('/tmp/rect-test.png').convert('RGB'))
print('max diff vs reference:', int(np.abs(ref.astype(int) - got.astype(int)).max()))
assert np.array_equal(ref, got)
print('OK')
PY
```

Expected: `masterBox`/`size` asserts pass, `max diff 0`, `OK`.

- [ ] **Step 3: Verify grow mode still works (no regression)**

```bash
python3 tools/crop-region.py --master "corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png" \
  --crop jobs/wang-meng/motion/pan/crop.json --out /tmp/grow-test.png --right 50
python3 -c "import json; s=json.load(open('/tmp/grow-test.json')); assert s['shotOffset']==[0,0] and 'shotWindowInRegion' in s; print('grow mode OK', s['size'])"
```

Expected: `grow mode OK [770, 1280]` (720+50 wide).

- [ ] **Step 4: Verify the mutual-exclusion errors**

```bash
python3 tools/crop-region.py --master x.png --out y.png 2>&1 | grep -q 'exactly one' && echo err1 OK
python3 tools/crop-region.py --master x.png --rect 0,0,10,10 --out y.png 2>&1 | grep -q 'needs --k' && echo err2 OK
```

Expected: `err1 OK`, `err2 OK`.

- [ ] **Step 5: Commit**

```bash
git add tools/crop-region.py
git commit -m "crop-region: --rect mode — cut any master rect at k, provenance sidecar kept"
```

---

### Task 2: `world.json`, the Z1 camera-world rect, and the approval overlay

The spec's zone rects are content boxes. A zone WORLD must contain every camera frame: route-leg bbox dilated by frame half-extent plus disocclusion reach. Formalize that rule in a small job script, compute Z1's rect, update the spec, and put the overlay on Pissjug's screen.

**Files:**
- Create: `jobs/wang-meng/journey/world.json`
- Create: `jobs/wang-meng/journey/stations.json`
- Create: `jobs/wang-meng/journey/zone-rect.py`
- Modify: `docs/specs/2026-08-17-wang-meng-journey-design.md` (Z1 row of the zone table)

**Interfaces:**
- Consumes: master size 6586×15923, k=2.34, spec station coords.
- Produces: `world.json` `{master, masterSize, k, frame:[720,1280]}` (master path relative to world.json's dir); `stations.json` `{"stations":[{"id":1,"name":"river entry","mx":3186,"my":15342}, ...]}`; `zone-rect.py --stations F --ids 1-4 --out-rect` printing `x0,y0,x1,y1`. Task 3 cuts that rect; Task 5 reads `world.json` and `stations.json`.

- [ ] **Step 1: Write `world.json` and `stations.json`**

`jobs/wang-meng/journey/world.json`:

```json
{
  "master": "../../../corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png",
  "masterSize": [6586, 15923],
  "k": 2.34,
  "frame": [720, 1280],
  "note": "k = master px per rendered px, proven on the pilot shot. All journey coordinates are master px."
}
```

`jobs/wang-meng/journey/stations.json` (draft coords from the spec, `"draft": true` until Pissjug corrects them on the plate in Task 5):

```json
{
  "draft": true,
  "stations": [
    {"id": 1,  "name": "river entry",        "mx": 3186, "my": 15342},
    {"id": 2,  "name": "ox party, bank",     "mx": 3186, "my": 13059},
    {"id": 3,  "name": "bridge, Ge + deer",  "mx": 1593, "my": 12528},
    {"id": 4,  "name": "porters climb",      "mx": 849,  "my": 11679},
    {"id": 5,  "name": "rapids, left bank",  "mx": 956,  "my": 10511},
    {"id": 6,  "name": "fenced cliff path",  "mx": 531,  "my": 6795},
    {"id": 7,  "name": "gorge traverse",     "mx": 2655, "my": 7326},
    {"id": 8,  "name": "under the waterfall","mx": 4141, "my": 5733},
    {"id": 9,  "name": "the compound",       "mx": 1805, "my": 4724},
    {"id": 10, "name": "mist release",       "mx": 3186, "my": 2761},
    {"id": 11, "name": "summit, far blue",   "mx": 3504, "my": 1380}
  ]
}
```

- [ ] **Step 2: Write `jobs/wang-meng/journey/zone-rect.py`**

```python
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
```

- [ ] **Step 3: Run it for stations 1–4 and check the numbers**

```bash
cd /Users/SSDrive/projects/media-tools
python3 jobs/wang-meng/journey/zone-rect.py --world jobs/wang-meng/journey/world.json \
  --stations jobs/wang-meng/journey/stations.json --ids 1-4
```

Expected: rect ≈ `[0, 9596, 4613, 15923]`, regionSize ≈ `[1971, 2704]` (±2 px from rounding). Sanity: regionSize height 2704 > frame 1280 + 2·250 travel slack; a 5.3 MP plate.

- [ ] **Step 4: Draw the Z1 rect + stations 1–4 on the scroll overview, open it**

```bash
python3 - <<'PY'
import json
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
v = Image.open("jobs/wang-meng/motion/pan/scroll-full.png").convert("RGB")
W, H = v.size
sx, sy = W / 6586, H / 15923
d = ImageDraw.Draw(v, "RGBA")
rect = [0, 9596, 4613, 15923]            # paste the actual Step-3 output
d.rectangle([rect[0]*sx, rect[1]*sy, rect[2]*sx, rect[3]*sy],
            outline=(60,120,220,255), width=4, fill=(60,120,220,26))
for s in json.load(open("jobs/wang-meng/journey/stations.json"))["stations"][:4]:
    x, y = s["mx"]*sx, s["my"]*sy
    d.ellipse([x-6, y-6, x+6, y+6], fill=(210,40,40))
    d.text((x+9, y-7), f'{s["id"]} {s["name"]}', fill=(255,255,255))
v.save("jobs/wang-meng/journey/z1-rect-overlay.png")
PY
open jobs/wang-meng/journey/z1-rect-overlay.png
```

**STOP — Pissjug's verdict on the overlay.** Does the Z1 world hold the whole river/bridge chapter with margin? Adjust rect on his correction and re-open.

- [ ] **Step 5: Update the spec's Z1 row with the approved rect**

In `docs/specs/2026-08-17-wang-meng-journey-design.md`, change the Z1 table row's rect to the approved numbers and add after the table: `Z1 rect finalized <date> by the camera-world rule: route-leg bbox dilated by frame/2 + 250 region px reach (zone-rect.py). Later zones get the same treatment at their turn.`

- [ ] **Step 6: Commit**

```bash
git add jobs/wang-meng/journey/zone-rect.py docs/specs/2026-08-17-wang-meng-journey-design.md
git commit -m "wang-meng journey phase1: camera-world rect rule (zone-rect.py), Z1 rect approved"
```

Note: `jobs/` is gitignored except scripts — check `git status`; if `zone-rect.py` is ignored, `git add -f` it (it is composition code, not data).

---

### Task 3: Cut the Z1 plate and run Pissjug's click pass

**Files:**
- Create: `jobs/wang-meng/journey/z1/plate.png` (+ `plate.json` sidecar, via crop-region)
- Create: `jobs/wang-meng/journey/z1/pick.html` (copy), `jobs/wang-meng/journey/z1/proxy.jpg`
- Create: `jobs/wang-meng/journey/z1/points.json` (PISSJUG'S OUTPUT)

**Interfaces:**
- Consumes: Task 1's `--rect` mode; Task 2's approved rect.
- Produces: `z1/plate.png` at region size ≈1971×2704 with `plate.json` (`masterBox`, `masterPxPerRegionPx`); `z1/points.json` in pick.html's format (normalized x,y ∈ 0..1 + depth + name per point) for Task 4.

- [ ] **Step 1: Cut the plate**

```bash
cd /Users/SSDrive/projects/media-tools
mkdir -p jobs/wang-meng/journey/z1
python3 tools/crop-region.py \
  --master "corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png" \
  --rect 0,9596,4613,15923 --k 2.34 --out jobs/wang-meng/journey/z1/plate.png
```

(Use the Task-2-approved rect if it changed.) Expected sidecar: `masterBox [0,9596,4613,15923]`, `size ≈ [1971, 2704]`.

- [ ] **Step 2: Stage the picker**

```bash
cp jobs/wang-meng/pick.html jobs/wang-meng/journey/z1/pick.html
python3 - <<'PY'
from PIL import Image
im = Image.open("jobs/wang-meng/journey/z1/plate.png")
im.resize((im.width//2, im.height//2), Image.LANCZOS).save(
    "jobs/wang-meng/journey/z1/proxy.jpg", quality=90)
PY
open jobs/wang-meng/journey/z1/pick.html
```

(pick.html loads `proxy.jpg` beside it; points are stored normalized, so the half-size proxy lands correctly on the full plate.)

- [ ] **Step 3: STOP — Pissjug clicks the planes**

His pass, ~15 points expected from the pilot's Z1 content: water, near rocks, far rocks/riverbank, bridge, Ge+deer, ox party, walking servants, the two great trees (right), left-bank porters, resting group, cliff wall left, cliff wall right, mid rocks, foreground ledge, bank path. Pilot depth ordering carries over as reference (far-cliff 0 → servant 9). He pastes/saves the JSON to `jobs/wang-meng/journey/z1/points.json`. Do not proceed without it.

---

### Task 4: Z1 stack — segment, seal, pin, fill; controls at every step

**Files:**
- Create: `jobs/wang-meng/journey/z1/build.sh` (the job script, one line per step)
- Create: `jobs/wang-meng/journey/z1/layers-cut/`, `layers-sealed/`, `layers-pinned/`, `layers-filled/` (stack dirs), `objects/`

**Interfaces:**
- Consumes: `z1/plate.png`, `z1/points.json`.
- Produces: `z1/layers-filled/` — the render-ready stack (layers.json + layers/*.png, plane names from points.json). Task 5/6 render from it.

- [ ] **Step 1: Read the four contracts**

Run `--help` on `segment-points.py`, `complete-planes.py`, `pin-objects.py`, `inpaint-planes.py` and reconcile the flags below against them before running anything. The pilot chain (from `jobs/wang-meng/motion/pan/layers-flux/layers.json`) was: segment-points → complete-planes (sealedFrom) → pin-objects (pinnedFrom, with an `objects/` dir from segment-regions) → inpaint-planes `--behind 100 --method flux`.

- [ ] **Step 2: Write and run `build.sh` step by step (not all at once)**

```bash
#!/bin/zsh
# Z1 stack build — run a line, verify, then the next. Test before batch.
set -euo pipefail
cd "$(dirname "$0")/../../../.."   # repo root
Z=jobs/wang-meng/journey/z1

python3 tools/segment-points.py --image $Z/plate.png --points $Z/points.json \
  --out $Z/layers-cut
open $Z/layers-cut/overlay.png          # VERDICT: Pissjug approves masks

python3 tools/probe-planes.py --layers $Z/layers-cut          # lint: unclaimed %, straddlers

python3 tools/segment-regions.py --image $Z/plate.png --out $Z/objects   # object masks for pinning

python3 tools/complete-planes.py --layers $Z/layers-cut --out $Z/layers-sealed
python3 tools/pin-objects.py --layers $Z/layers-sealed --objects $Z/objects --out $Z/layers-pinned
python3 tools/probe-planes.py --layers $Z/layers-pinned       # lint again: straddlers must be gone

python3 tools/inpaint-planes.py --layers $Z/layers-pinned --out $Z/layers-filled \
  --behind 100 --method flux
```

Adjust flags to what `--help` actually says (Step 1). Expected costs: SAM ~1 min on mps; flux fill ~2 min + ~$1–2.

- [ ] **Step 3: The overlay verdict — STOP for Pissjug**

After segment-points, `open` the overlay. He approves or re-clicks points; iterate until approved. Only then seal/pin/fill.

- [ ] **Step 4: Frame-zero control on the filled stack**

```bash
python3 - <<'PY'
import json
import numpy as np
from PIL import Image
from pathlib import Path

def flat(laydir):
    d = Path(laydir)
    m = json.loads((d/"layers.json").read_text())
    base = np.asarray(Image.open(m["image"]).convert("RGB")).copy()
    for p in sorted([q for q in m["planeList"] if q.get("layer")], key=lambda q: q["depth"]):
        im = np.asarray(Image.open(d/p["layer"]).convert("RGBA"))
        ox, oy = p["offset"]; h, w = im.shape[:2]
        a = im[..., 3:4].astype(float)/255
        reg = base[oy:oy+h, ox:ox+w]
        base[oy:oy+h, ox:ox+w] = (im[..., :3]*a + reg*(1-a)).astype(np.uint8)
    return base

Z = "jobs/wang-meng/journey/z1/"
plate = np.asarray(Image.open(Z+"plate.png").convert("RGB")).astype(int)
filled = flat(Z+"layers-filled").astype(int)
d = np.abs(plate - filled).max(2)
print("frame-zero control: px changed", int((d > 0).sum()), "max", int(d.max()))
assert (d > 0).sum() == 0, "the fill painted at rest — STOP, do not render"
print("CONTROL PASSES")
PY
```

Expected: `px changed 0`, `CONTROL PASSES`. (cv2 lives in system python3, not the venv — same as the pilot.)

- [ ] **Step 5: Commit the job script**

```bash
git add -f jobs/wang-meng/journey/z1/build.sh
git commit -m "wang-meng journey phase1: Z1 stack build script (segment/seal/pin/flux-fill + controls)"
```

---

### Task 5: `map-path.py` and the stations 1–4 world path

**Files:**
- Create: `tools/map-path.py`
- Create: `jobs/wang-meng/journey/path-world.json`
- Create: `jobs/wang-meng/journey/z1/path-z1.json` (generated)

**Interfaces:**
- Consumes: `world.json` (k, frame), region sidecar `z1/plate.json` (masterBox, masterPxPerRegionPx), region `layers.json` size.
- Produces: `map-path.py --world-path P --region-sidecar S --out O` → render-parallax path JSON (`{fps, keys:[{t,x,y,z,fov}]}` with x,y normalized 0..1 on the REGION). World-path knot format: `{"t": sec, "mx": masterX, "my": masterY, "z": dolly, "fov": 1.0}`.

- [ ] **Step 1: Write `tools/map-path.py`**

```python
#!/usr/bin/env python3
"""media-tools — map-path: a world-coordinate camera path → one region's local
path. One job. It converts coordinates; it does not render, slice by time, or
author anything.

WHY. The journey is authored ONCE in master pixels (the coordinate SSOT —
docs/specs/2026-08-17-wang-meng-journey-design.md). render-parallax wants x,y
normalized on ITS stack's canvas. Doing that mapping by hand per zone is how
the crop-provenance bug family breeds; this tool owns the arithmetic.

usage:
  map-path.py --world-path PATH --region-sidecar PATH --out PATH

  --world-path F      {"fps": 24, "keys": [{"t":0,"mx":3186,"my":15342,
                       "z":0.0,"fov":1.0}, ...]}  mx,my in MASTER px
  --region-sidecar F  crop-region sidecar: masterBox + masterPxPerRegionPx
  --out F             render-parallax path JSON, x,y normalized on the region

Knots landing outside the region are an ERROR, not a warning: a frame centred
outside the world is a hole by construction. Fix the rect or the path.
"""
import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--world-path", required=True)
    ap.add_argument("--region-sidecar", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    wp = json.loads(Path(a.world_path).read_text())
    side = json.loads(Path(a.region_sidecar).read_text())
    x0, y0, x1, y1 = side["masterBox"]
    k = side["masterPxPerRegionPx"]
    RW, RH = side["size"]

    keys, bad = [], []
    for kn in wp["keys"]:
        rx = (kn["mx"] - x0) / k / RW
        ry = (kn["my"] - y0) / k / RH
        if not (0.0 <= rx <= 1.0 and 0.0 <= ry <= 1.0):
            bad.append({"t": kn["t"], "rx": round(rx, 3), "ry": round(ry, 3)})
        keys.append({"t": kn["t"], "x": rx, "y": ry,
                     "z": kn.get("z", 0.0), "fov": kn.get("fov", 1.0)})
    if bad:
        print(json.dumps({"error": "knots outside region", "bad": bad}, indent=2),
              file=sys.stderr)
        return 1

    out = {kk: v for kk, v in wp.items() if kk != "keys"}
    out["keys"] = keys
    out["mappedFrom"] = str(a.world_path)
    out["region"] = str(a.region_sidecar)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({"tool": "map-path", "out": a.out, "keys": len(keys),
                      "region": side["masterBox"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify with a synthetic round-trip**

```bash
python3 - <<'PY'
import json, subprocess, sys
json.dump({"masterBox":[100,200,2440,4880],"masterPxPerRegionPx":2.34,"size":[1000,2000]},
          open("/tmp/side.json","w"))
json.dump({"fps":24,"keys":[{"t":0,"mx":100,"my":200},{"t":5,"mx":2440,"my":4880,"z":0.3}]},
          open("/tmp/wp.json","w"))
r = subprocess.run([sys.executable,"tools/map-path.py","--world-path","/tmp/wp.json",
                   "--region-sidecar","/tmp/side.json","--out","/tmp/lp.json"],
                  capture_output=True, text=True)
assert r.returncode == 0, r.stderr
lp = json.load(open("/tmp/lp.json"))
assert lp["keys"][0]["x"] == 0.0 and lp["keys"][0]["y"] == 0.0
assert lp["keys"][1]["x"] == 1.0 and lp["keys"][1]["y"] == 1.0 and lp["keys"][1]["z"] == 0.3
json.dump({"fps":24,"keys":[{"t":0,"mx":99,"my":200}]}, open("/tmp/wp2.json","w"))
r2 = subprocess.run([sys.executable,"tools/map-path.py","--world-path","/tmp/wp2.json",
                    "--region-sidecar","/tmp/side.json","--out","/tmp/lp2.json"],
                   capture_output=True, text=True)
assert r2.returncode == 1 and "outside region" in r2.stderr
print("map-path OK")
PY
```

Expected: `map-path OK`.

- [ ] **Step 3: Author `path-world.json` for stations 1–4**

Draft (speeds drone-slow; z-pushes at stations; t values give ~55 s for the chapter — the path length sets duration, not a target):

```json
{
  "fps": 24,
  "keys": [
    {"t": 0,  "mx": 3186, "my": 15342, "z": 0.00, "fov": 1.0},
    {"t": 12, "mx": 3186, "my": 13800, "z": 0.10, "fov": 1.0},
    {"t": 20, "mx": 3186, "my": 13059, "z": 0.18, "fov": 1.0},
    {"t": 30, "mx": 2300, "my": 12700, "z": 0.22, "fov": 1.0},
    {"t": 38, "mx": 1593, "my": 12528, "z": 0.30, "fov": 1.0},
    {"t": 48, "mx": 1100, "my": 12000, "z": 0.26, "fov": 1.0},
    {"t": 55, "mx": 849,  "my": 11679, "z": 0.30, "fov": 1.0}
  ]
}
```

Then draw it on the plate for Pissjug's correction:

```bash
python3 - <<'PY'
import json
from PIL import Image, ImageDraw
Z = "jobs/wang-meng/journey/z1/"
side = json.load(open(Z+"plate.json"))
x0, y0, _, _ = side["masterBox"]; k = side["masterPxPerRegionPx"]
im = Image.open(Z+"plate.png").convert("RGB")
im.thumbnail((900, 1400))
s = im.width / side["size"][0]
d = ImageDraw.Draw(im)
pts = [((kn["mx"]-x0)/k*s, (kn["my"]-y0)/k*s)
       for kn in json.load(open("jobs/wang-meng/journey/path-world.json"))["keys"]]
d.line(pts, fill=(210,40,40), width=4)
for p in pts: d.ellipse([p[0]-5,p[1]-5,p[0]+5,p[1]+5], fill=(210,40,40))
im.save(Z+"path-overlay.png")
PY
open jobs/wang-meng/journey/z1/path-overlay.png
```

**STOP — Pissjug corrects the path and stations 1–4 coords on the overlay** (this also retires `stations.json`'s `"draft": true` for ids 1–4). Iterate until approved.

- [ ] **Step 4: Map it**

```bash
python3 tools/map-path.py --world-path jobs/wang-meng/journey/path-world.json \
  --region-sidecar jobs/wang-meng/journey/z1/plate.json \
  --out jobs/wang-meng/journey/z1/path-z1.json
```

Expected: exit 0, 7 keys, no outside-region errors.

- [ ] **Step 5: Commit**

```bash
git add tools/map-path.py
git add -f jobs/wang-meng/journey/path-world.json jobs/wang-meng/journey/world.json jobs/wang-meng/journey/stations.json
git commit -m "map-path: world-coordinate camera path to region-local (journey SSOT); stations + Z1 path draft"
```

---

### Task 6: Z1 geometry, flythrough render, and the watchable verdict

**Files:**
- Create: `jobs/wang-meng/journey/z1/geometry.json`
- Create: `jobs/wang-meng/journey/z1/frames/`, `jobs/wang-meng/journey/z1/Z1-FLYTHROUGH.mp4`

**Interfaces:**
- Consumes: `z1/layers-filled`, `z1/path-z1.json`.
- Produces: the phase-1 deliverable video. Phase 2 consumes the stack + world path unchanged.

- [ ] **Step 1: Author `geometry.json` — Z1's 平遠 eye**

Tilts keyed by the plane names Pissjug's points.json used (units: dz per source px; from render-parallax's contract, 0.00004 over 3000 px ≈ 0.12 depth). Starting values — water and ground pitch away gently, uprights stay billboards:

```json
{
  "water":           {"tiltX": 0.00005},
  "riverbank-far":   {"tiltX": 0.00004},
  "foreground-ledge":{"tiltX": 0.00005},
  "bank-path":       {"tiltX": 0.00004},
  "cliff-wall-left": {"tiltY": 0.00003},
  "cliff-wall-right":{"tiltY": -0.00003}
}
```

Reconcile names against `layers-filled/layers.json` before rendering; a tilt keyed to a name that doesn't exist silently does nothing.

- [ ] **Step 2: Stills first — the three-frame look**

```bash
python3 tools/render-parallax.py --layers jobs/wang-meng/journey/z1/layers-filled \
  --out jobs/wang-meng/journey/z1/stills --path jobs/wang-meng/journey/z1/path-z1.json \
  --geometry jobs/wang-meng/journey/z1/geometry.json --plane-fit --z-step 0.15 \
  --width 720 --height 1280 --fps 24 --stills
open jobs/wang-meng/journey/z1/stills/*.png
```

**STOP — Pissjug judges first/middle/last.** Check: frame zero is the painting exactly; no holes; parallax reads as travel, not zoom. Fix geometry/path and repeat. Cheap loop — full render only after stills pass.

- [ ] **Step 3: Full render + encode + watch**

```bash
python3 tools/render-parallax.py --layers jobs/wang-meng/journey/z1/layers-filled \
  --out jobs/wang-meng/journey/z1/frames --path jobs/wang-meng/journey/z1/path-z1.json \
  --geometry jobs/wang-meng/journey/z1/geometry.json --plane-fit --z-step 0.15 \
  --width 720 --height 1280 --fps 24
ffmpeg -y -r 24 -i jobs/wang-meng/journey/z1/frames/%05d.png -c:v libx264 -crf 16 \
  -pix_fmt yuv420p jobs/wang-meng/journey/z1/Z1-FLYTHROUGH.mp4
open jobs/wang-meng/journey/z1/Z1-FLYTHROUGH.mp4
```

Expected: ~1320 frames, ~6 min render at the pilot's 0.26 s/frame.

- [ ] **Step 4: STOP — the phase gate**

Phase 1 is DONE only when Pissjug calls the flythrough watchable. His verdict, his words, recorded in the commit message.

- [ ] **Step 5: Commit the phase**

```bash
git add -f jobs/wang-meng/journey/z1/geometry.json jobs/wang-meng/journey/z1/path-z1.json
git commit -m "wang-meng journey phase1 DONE: Z1 river+bridge flythrough watchable (verdict: <his words>)"
```

---

## Self-review notes

- Spec coverage: world.json (Task 2), Z1 re-planed at full footprint (Tasks 2–4), journey spline stations 1–4 (Task 5), watchable flythrough + controls (Tasks 4, 6). Handoff gate is phase 2, correctly out of scope.
- The Z1 rect supersedes the spec's draft row — Task 2 Step 5 writes that back so the spec stays SSOT.
- Type consistency: `masterBox`/`masterPxPerRegionPx`/`size` (crop-region sidecar) are the exact names map-path.py reads; world-path knots use `mx`/`my` everywhere.
- Human gates: Task 2 Step 4, Task 3 Step 3, Task 4 Steps 3–4, Task 5 Step 3, Task 6 Steps 2/4. Subagents stop and report at each.
