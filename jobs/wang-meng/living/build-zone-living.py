#!/usr/bin/env python3
"""Build LIVING PATCH CYCLES for a zone world's planes.

Why this exists (Ryan, 2026-08-20, after five days of camera moves over still
ink): only z1 ever had living cycles. z3w-z6w -- every waterfall, cascade and
stream above the bridge -- were STILL IMAGES being flown past. `film/
compile-flight.py` now refuses to render those legs (the LIVING GATE), so the
zones need cycles before the film can be built again.

The shape of the problem is different from z1 and that is why this is a new
tool rather than build-plane-cycles.py. In z1 the water WAS a plane, so the
cycle could be a full-plane texture swap. In the upper zones the water is
0.2-1.2% of a plate-sized plane it shares with a whole cliff wall, and it is
split across several planes at once (w-midstream is 98% on left-cliff-wall and
24% on upper-stream-rocks, because the rocks sit in front of it). So:

  1. region masks come from the NATIVE masks already audited in living/native
     (seals sealed, the porter's basket weave excluded) -- downscaled by k into
     plate space rather than re-cut, so the audit carries over.
  2. every plane holding >= --min-frac of a region gets its own cycle, cut from
     that plane's OWN filled texture, masked by region AND the plane's alpha.
     Whichever plane ends up in front, the water it shows is moving.
  3. the cycle is stored as a PATCH (region bbox + pad) with the plane's alpha
     baked in, and render-parallax --living pastes it onto the plane texture.
     A full-plane cycle here would be ~40MB a drawing for a 220x415 window.

Motion params are the class winners in regions.json, in 720-space -- and that
is the right space, because a zone plate is master/2.34 which is the scale the
cel water was proven at (STATE 2026-08-19 night, scale law 3).

  --stage masks     region -> plate-space masks + a tinted evidence overlay
  --stage cycle     animate every (region, plane) pair  [--region ID --plane N]
  --stage register  write living/living-<zone>.json for compile-flight
  --stage audit     what-moved heat map -> living/evidence-living-<zone>.png
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).parent          # jobs/wang-meng/living
JOB = HERE.parent                     # jobs/wang-meng
ROOT = JOB.parents[1]                 # media-tools

ap = argparse.ArgumentParser()
ap.add_argument("--zone", required=True)
ap.add_argument("--stage", required=True,
                choices=["masks", "cycle", "register", "audit"])
ap.add_argument("--region", default=None, help="restrict to one region id")
ap.add_argument("--plane", default=None, help="restrict to one plane name")
ap.add_argument("--classes", default="wave,fall",
                help="region classes to build (default: the water ones)")
ap.add_argument("--min-frac", type=float, default=0.02,
                help="skip a (region, plane) pair holding less of the region "
                     "than this -- a few hundred stray px is a mask feather, "
                     "not water this plane owns")
ap.add_argument("--min-px", type=int, default=500)
ap.add_argument("--pad", type=int, default=64,
                help="px of context around the region bbox in the patch, so "
                     "the displacement field and its feather have room to die "
                     "out inside the patch instead of at its edge")
ap.add_argument("--drawings", type=int, default=36)
a = ap.parse_args()

Z = JOB / "journey" / a.zone
plate_meta = json.loads((Z / "plate.json").read_text())
X0, Y0, X1, Y1 = plate_meta["masterBox"]
K = plate_meta["masterPxPerRegionPx"]
PW, PH = plate_meta["size"]
LAY = Z / "layers-filled"
layers = json.loads((LAY / "layers.json").read_text())
REG = json.loads((HERE / "regions.json").read_text())
CLASSES = REG["classes"]                     # SSOT for the motion parameters
POLYS = json.loads((HERE / "water-polys.json").read_text())
WANT = set(a.classes.split(","))
MASKD = Z / "living-masks"
WORK = Z / "living-work"
OUT = Z / "living"


def to_plate(pts):
    return [((mx - X0) / K, (my - Y0) / K) for mx, my in pts]


def regions_here():
    """Authored polygons whose plate-space footprint lands inside this zone."""
    out = []
    for r in POLYS["polys"]:
        if r["class"] not in WANT:
            continue
        if a.region and r["id"] != a.region:
            continue
        xs = [x for x, _ in to_plate(r["points"])]
        ys = [y for _, y in to_plate(r["points"])]
        if min(xs) >= PW or max(xs) <= 0 or min(ys) >= PH or max(ys) <= 0:
            continue
        out.append(r)
    return out


def plate_mask(rid):
    """Region mask in full-plate space, uint8 0/255."""
    return np.array(Image.open(MASKD / f"{rid}.png").convert("L"))


# ---------------------------------------------------------------- masks -----
if a.stage == "masks":
    from PIL import ImageDraw
    MASKD.mkdir(parents=True, exist_ok=True)
    plate = Image.open(Z / "plate.png").convert("RGB")
    over = plate.copy()
    index = {}
    for r in regions_here():
        m = Image.new("L", (PW, PH), 0)
        d = ImageDraw.Draw(m)
        d.polygon(to_plate(r["points"]), fill=255)
        for ex in POLYS.get("excludes", []):
            if ex["forId"] == r["id"]:
                d.polygon(to_plate(ex["points"]), fill=0)
        canvas = np.array(m)
        if not canvas.any():
            continue
        Image.fromarray(canvas).save(MASKD / f"{r['id']}.png")
        ys, xs = np.nonzero(canvas)
        cov = int((canvas > 128).sum())
        index[r["id"]] = {"class": r["class"], "px": cov,
                          "pctOfPlate": round(100 * cov / (PW * PH), 3),
                          "plateBox": [int(xs.min()), int(ys.min()),
                                       int(xs.max()) + 1, int(ys.max()) + 1]}
        print(f"{r['id']:20s} {r['class']:5s} {cov:8d}px "
              f"({index[r['id']]['pctOfPlate']}% of plate)", file=sys.stderr)
        tint = Image.new("RGB", plate.size,
                         (30, 90, 200) if r["class"] in ("wave", "fall") else (200, 90, 30))
        over = Image.composite(Image.blend(over, tint, 0.5), over,
                               Image.fromarray(canvas))
    (MASKD / "index.json").write_text(json.dumps(index, indent=1))
    s_ = 1400 / max(over.size)
    over.resize((int(over.width * s_), int(over.height * s_))).save(
        HERE / f"evidence-masks-{a.zone}.png")
    print(json.dumps({"zone": a.zone, "regions": index}, indent=1))

# ---------------------------------------------------------------- cycle -----
if a.stage == "cycle":
    OUT.mkdir(parents=True, exist_ok=True)
    plate = Image.open(Z / "plate.png").convert("RGB")

    # WHO OWNS A PIXEL. layers.json is sorted farthest-first, so the plane that
    # is actually SEEN at a pixel is the LAST one in paint order with alpha
    # there. This matters more than it sounds: a plane's filled texture is only
    # real painting where nothing nearer covers it -- everywhere else it is
    # disocclusion fill, and over the midstream pool that fill is smeared
    # streaks where the ripple arcs used to be (evidence:
    # living/_chk-texture-source.png, master | plate | left-cliff-wall).
    # Animating the fill would move garbage. So each water pixel is animated by
    # exactly one plane: the one that shows it.
    order = sorted(layers["planeList"], key=lambda q: q["depth"])
    alphas, vis = {}, {}
    for q in order:
        tex = Image.open(LAY / q["layer"]).convert("RGBA")
        A = np.zeros((PH, PW), bool)
        ox, oy = q["offset"]
        al = np.array(tex.split()[3]) > 128
        h_, w_ = al.shape
        A[oy:oy + h_, ox:ox + w_] = al[:PH - oy, :PW - ox]
        alphas[q["name"]] = A
    covered = np.zeros((PH, PW), bool)
    for q in reversed(order):                       # nearest first
        vis[q["name"]] = alphas[q["name"]] & ~covered
        covered |= alphas[q["name"]]

    built = []
    for r in regions_here():
        rm = plate_mask(r["id"]) > 128
        tot = int(rm.sum())
        cls = dict(CLASSES[r["class"]])
        ys, xs = np.nonzero(rm)
        cx0, cy0 = int(max(0, xs.min() - a.pad)), int(max(0, ys.min() - a.pad))
        cx1, cy1 = int(min(PW, xs.max() + 1 + a.pad)), int(min(PH, ys.max() + 1 + a.pad))

        # ONE animation per water body, cut from the plate, so the displacement
        # field is continuous across the plane seams that cross it.
        wd = WORK / r["id"]
        (wd / "mask" / "masks").mkdir(parents=True, exist_ok=True)
        plate.crop((cx0, cy0, cx1, cy1)).save(wd / "plate.png")
        Image.fromarray((rm[cy0:cy1, cx0:cx1] * 255).astype(np.uint8)).save(
            wd / "mask" / "masks" / "001.png")
        (wd / "mask" / "layers.json").write_text(json.dumps({
            "tool": "build-zone-living", "size": [cx1 - cx0, cy1 - cy0],
            "planeList": [{"n": 1, "name": r["id"], "offset": [0, 0]}]}))
        cmd = ["python3", str(ROOT / "tools/animate-strokes.py"),
               "--image", str(wd / "plate.png"), "--masks", str(wd / "mask"),
               "--out", str(wd / "preview.mp4"),
               "--out-frames", str(wd / "drawings"),
               "--frames", str(a.drawings * cls.get("on", 2)),
               "--on", str(cls.get("on", 2)),
               "--field", cls["field"], "--mode", cls["mode"], "--keep", cls["keep"]]
        for flag in ("wobble", "drift", "wavelength", "angle", "stiffness",
                     "scale", "boil", "max-thick"):
            key = flag.replace("-", "_") if flag == "max-thick" else flag
            if key in cls:
                cmd += [f"--{flag}", str(cls[key])]
        print(f"=== {r['id']} ({r['class']}): {tot}px, crop "
              f"{cx1-cx0}x{cy1-cy0} at {cx0},{cy0}", file=sys.stderr)
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if res.returncode != 0:
            sys.exit(f"{r['id']}: animate-strokes failed\n{res.stderr[-900:]}")
        cyc = json.loads((wd / "drawings" / "cycle.json").read_text())
        draw = [np.array(Image.open(wd / "drawings" / f"dr-{i:03d}.png").convert("RGB"))
                for i in range(cyc["drawings"])]
        base = np.array(plate.crop((cx0, cy0, cx1, cy1)), np.int16)
        moved = np.zeros(base.shape[:2], np.uint8)
        for d in draw:
            moved = np.maximum(moved, np.abs(d.astype(np.int16) - base).max(-1).astype(np.uint8))
        Image.fromarray(moved).save(wd / "moved.png")

        for q in order:
            if a.plane and q["name"] != a.plane:
                continue
            own = rm & vis[q["name"]]
            n = int(own.sum())
            if n < a.min_px or n < tot * a.min_frac:
                continue
            oy_, ox_ = q["offset"][1], q["offset"][0]
            tex = Image.open(LAY / q["layer"]).convert("RGBA")
            w_, h_ = tex.size
            oys, oxs = np.nonzero(own)
            # patch box in PLANE-LOCAL coords, clipped to the plane and to the
            # animated crop (a drawing only exists inside the crop)
            bx0 = int(max(0, max(oxs.min() - a.pad, cx0) - ox_))
            by0 = int(max(0, max(oys.min() - a.pad, cy0) - oy_))
            bx1 = int(min(w_, min(oxs.max() + 1 + a.pad, cx1) - ox_))
            by1 = int(min(h_, min(oys.max() + 1 + a.pad, cy1) - oy_))
            if bx1 <= bx0 or by1 <= by0:
                continue
            gx0, gy0 = bx0 + ox_, by0 + oy_          # same box in plate coords
            gx1, gy1 = bx1 + ox_, by1 + oy_
            texa = np.array(tex.crop((bx0, by0, bx1, by1)))
            sel = own[gy0:gy1, gx0:gx1]
            od = OUT / f"{q['name']}__{r['id']}"
            od.mkdir(parents=True, exist_ok=True)
            for i, d in enumerate(draw):
                out = texa.copy()
                dd = d[gy0 - cy0:gy1 - cy0, gx0 - cx0:gx1 - cx0]
                out[..., :3][sel] = dd[sel]
                Image.fromarray(out).save(od / f"{i:03d}.png")
            mv = int((moved[gy0 - cy0:gy1 - cy0, gx0 - cx0:gx1 - cx0][sel] > 6).sum())
            built.append({"plane": q["name"], "region": r["id"], "dir": str(od),
                          "box": [bx0, by0], "n": cyc["drawings"], "on": cyc["on"],
                          "ownPx": n, "movedPx": mv})
            print(f"    {q['name']:26s} owns {n:7d}px ({100*n/tot:5.1f}%), "
                  f"patch {bx1-bx0}x{by1-by0} at {bx0},{by0}, moved {mv}px",
                  file=sys.stderr)
    manifest = OUT / "built.json"
    prev = json.loads(manifest.read_text()) if manifest.exists() else []
    keep = [b for b in prev
            if not any(b["plane"] == n["plane"] and b["region"] == n["region"]
                       for n in built)]
    manifest.write_text(json.dumps(keep + built, indent=1))
    print(json.dumps(built, indent=1))

# ------------------------------------------------------------- register -----
if a.stage == "register":
    built = json.loads((OUT / "built.json").read_text())
    living = {}
    for b in built:
        living.setdefault(b["plane"], {"patches": []})["patches"].append(
            {"dir": b["dir"], "box": b["box"], "n": b["n"], "on": b["on"]})
    out = HERE / f"living-{a.zone}.json"
    out.write_text(json.dumps(living, indent=1))
    print(json.dumps({"out": str(out), "planes": sorted(living),
                      "patches": sum(len(v["patches"]) for v in living.values())},
                     indent=1))

# ---------------------------------------------------------------- audit -----
if a.stage == "audit":
    built = json.loads((OUT / "built.json").read_text())
    plate = Image.open(Z / "plate.png").convert("RGB")
    heat = np.zeros((PH, PW), np.uint8)
    for rid in sorted({b["region"] for b in built}):
        m = np.array(Image.open(WORK / rid / "moved.png"))
        idx = json.loads((MASKD / "index.json").read_text())[rid]
        ys, xs = np.nonzero(np.array(Image.open(MASKD / f"{rid}.png")) > 128)
        gx = int(max(0, xs.min() - a.pad))
        gy = int(max(0, ys.min() - a.pad))
        hh, ww = m.shape
        gx1, gy1 = min(PW, gx + ww), min(PH, gy + hh)
        if gx1 <= gx or gy1 <= gy:
            continue
        heat[gy:gy1, gx:gx1] = np.maximum(heat[gy:gy1, gx:gx1],
                                          m[:gy1 - gy, :gx1 - gx])
    red = np.array(plate).astype(np.float32)
    w = np.clip(heat.astype(np.float32) / 40.0, 0, 1)[..., None]
    red = red * (1 - w) + np.array([255, 40, 40], np.float32) * w
    ev = Image.fromarray(red.astype(np.uint8))
    s = 1400 / max(ev.size)
    ev.resize((int(ev.width * s), int(ev.height * s))).save(
        HERE / f"evidence-living-{a.zone}.png")
    print(json.dumps({"zone": a.zone, "movedPx": int((heat > 6).sum()),
                      "pctOfPlate": round(100 * (heat > 6).sum() / (PW * PH), 3),
                      "peak": int(heat.max()),
                      "evidence": f"living/evidence-living-{a.zone}.png"}, indent=1))
