#!/usr/bin/env python3
"""Build NATIVE-resolution water/fall cycles for every water region.

The art-history film explores the whole 105MP scroll at master 1:1, so
each water region gets its cycle computed on a native crop, not the
k=2.34 zone plate. Consumer: render-living (tiles pasted at the region
box; cycles held on twos via the "on" field).

Stages (run masks first, LOOK at the contact sheet, then cycle):
  --stage masks            crop + liubai mask + overlay per region, contact sheet
  --stage cycle --id ID    animate one region (test-before-batch: one, verify, then rest)
  --stage register         write "cycle" entries into regions.json for built regions

Masks are cut by MATERIAL (mask-bare-ground: bright low-variance silk;
proven on this scroll 2026-08-14 — SAM can't segment an absence).
"""
import argparse, json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).parent            # living/
JOB = HERE.parent                       # jobs/wang-meng
ROOT = JOB.parent.parent                # media-tools
R = json.loads((HERE / "regions.json").read_text())
MASTER = ROOT / R["master"]
WATER = [r for r in R["regions"] if r["class"] in ("wave", "fall")]

ap = argparse.ArgumentParser()
ap.add_argument("--stage", required=True, choices=["masks", "cycle", "register"])
ap.add_argument("--id", default=None)
ap.add_argument("--busy", type=float, default=0.055)
ap.add_argument("--min-area", type=int, default=200,
                help="masks stage: drop silk islands smaller than this — "
                     "kills the speckle gaps inside stippled canopies")
ap.add_argument("--angle", type=float, default=None, help="override flow angle for --stage cycle")
a = ap.parse_args()

if a.stage == "masks":
    tiles = []
    for r in [q for q in WATER if not a.id or q["id"] == a.id]:
        x0, y0, x1, y1 = r["box"]
        d = HERE / "native" / r["id"]
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "plate.png").exists():
            Image.open(MASTER).convert("RGB").crop((x0, y0, x1, y1)).save(d / "plate.png")
        lj = d / "mask" / "layers.json"
        if lj.exists():
            lj.unlink()
        w, h = x1 - x0, y1 - y0
        subprocess.run(["python3", str(ROOT / "tools/mask-bare-ground.py"),
                        "--image", str(d / "plate.png"), "--box", f"0,0,{w},{h}",
                        "--name", r["id"], "--busy", str(a.busy),
                        "--min-area", str(a.min_area),
                        "--out", str(d / "mask")], check=True, cwd=ROOT,
                       capture_output=True)
        cov = json.loads(lj.read_text())["planeList"][0]["coveragePctOfBox"]
        plate = Image.open(d / "plate.png").convert("RGB")
        m = Image.open(d / "mask" / "masks" / "001.png").convert("L")
        tint = Image.new("RGB", plate.size, (30, 90, 200))
        over = Image.composite(Image.blend(plate, tint, 0.45), plate, m)
        over.save(d / "mask-overlay.png")
        s = 420 / max(over.size)
        tiles.append((r["id"], cov, over.resize((int(over.width * s), int(over.height * s)))))
        print(f"{r['id']}: {w}x{h}  water {cov}% of box", file=sys.stderr)
    if a.id:                       # single re-cut: overlay is the evidence,
        sys.exit(0)                # don't clobber the 7-region contact sheet
    cols = 4
    cw = max(t[2].width for t in tiles) + 16
    ch = max(t[2].height for t in tiles) + 40
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * ch), (248, 246, 240))
    dr = ImageDraw.Draw(sheet)
    for i, (rid, cov, im) in enumerate(tiles):
        cx, cy = (i % cols) * cw + 8, (i // cols) * ch + 30
        sheet.paste(im, (cx, cy))
        dr.text((cx, cy - 22), f"{rid}  ({cov}% water)", fill=(30, 28, 24))
    sheet.save(HERE / "evidence-native-water-masks.png")
    print(json.dumps({"regions": len(tiles),
                      "sheet": "living/evidence-native-water-masks.png"}))

elif a.stage == "cycle":
    r = next(q for q in WATER if q["id"] == a.id)
    cls = R["classes"][r["class"]]
    d = HERE / "native" / r["id"]
    angle = a.angle if a.angle is not None else cls.get("angle", 8)
    cmd = ["python3", str(ROOT / "tools/animate-strokes.py"),
           "--image", str(d / "plate.png"), "--masks", str(d / "mask"),
           "--field", cls["field"], "--mode", cls["mode"], "--keep", cls["keep"],
           "--on", str(cls["on"]), "--wobble", str(cls["wobble"]),
           "--drift", str(cls["drift"]), "--wavelength", str(cls["wavelength"]),
           "--angle", str(angle), "--frames", "72",
           "--out", str(d / "preview.mp4"), "--out-frames", str(d / "cycle")]
    out = subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True, text=True)
    j = json.loads(out.stdout)
    print(json.dumps({k: j[k] for k in ("uniqueDrawings", "on", "inkPctOfRegion",
                                        "roundTripMeanErr", "roundTripP99Err",
                                        "peakDisplacementPx")} | {"id": r["id"],
                                        "angle": angle}, indent=1))

elif a.stage == "register":
    n = 0
    for r in R["regions"]:
        cj = HERE / "native" / r["id"] / "cycle" / "cycle.json"
        if r["class"] in ("wave", "fall") and cj.exists():
            c = json.loads(cj.read_text())
            r["cycle"] = {"dir": f"native/{r['id']}/cycle", "pattern": "dr-%03d.png",
                          "box": r["box"], "n": c["drawings"], "on": c["on"]}
            n += 1
    (HERE / "regions.json").write_text(json.dumps(R, indent=1))
    print(json.dumps({"registered": n}))
