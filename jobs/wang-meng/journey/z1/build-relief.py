#!/usr/bin/env python3
"""Z1 relief maps: within-plane surface shape for render-parallax --relief.

The law stands: depth ORDER is authored (monocular scene depth is dead,
49-88% row-explained). What DAv2 is allowed to contribute here is the one
thing it is actually good at: LOCAL shape from shading, inside a single
authored card. The scene-scale component -- the exact measured failure --
is removed by construction: relief = raw depth minus a heavy gaussian of
itself, so only features smaller than the blur radius survive. A flat ramp
across the plane high-passes to zero.

Stages: composite each plane over paper tone -> DAv2 (.venv estimate-depth,
raw float) -> high-pass -> normalize to a centered 8-bit map (128 = on the
card, bright = toward camera) -> relief/<plane>.png + an evidence sheet
[crop | raw depth | relief] per plane for the eyes BEFORE anything renders.
"""

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

HERE = Path(__file__).parent
REPO = HERE.parents[3]
LAYERS = HERE / "layers-filled"
OUT = HERE / "relief"
PAPER = (214, 203, 176)

# Rock and wall surfaces only. Water/figures/bridge never take relief;
# canopy planes wait until the walls prove the mechanism. Band = full depth
# range of the map, chosen per plane because displacement sensitivity is
# camZ/(zr(zr-camZ)): the walls at zr~3.7 need ~20x the band of the
# foreground rock at zr~1.0 to move a comparable pixel count.
TARGETS = {"left-cliff-wall": 0.6, "gorge-wall-right": 0.6,
           "foreground-rock-mass": 0.08}

meta = json.loads((LAYERS / "layers.json").read_text())
planes = {p["name"]: p for p in meta["planeList"] if p.get("layer")}
OUT.mkdir(exist_ok=True)
(OUT / "_work").mkdir(exist_ok=True)

sheet_rows = []
manifest = {}
for name in TARGETS:
    p = planes[name]
    rgba = Image.open(LAYERS / p["layer"]).convert("RGBA")
    w, h = rgba.size
    flat = Image.new("RGB", (w, h), PAPER)
    flat.paste(rgba, (0, 0), rgba)
    crop_path = OUT / "_work" / f"{name}-crop.png"
    flat.save(crop_path)

    raw_path = OUT / "_work" / f"{name}-raw.npy"
    if not raw_path.exists():
        r = subprocess.run(
            [str(REPO / ".venv/bin/python"), str(REPO / "tools/estimate-depth.py"),
             "--image", str(crop_path), "--raw", str(raw_path),
             "--out", str(OUT / "_work" / f"{name}-depth.png"),
             "--max-side", str(max(w, h))],
            capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            sys.exit(1)

    raw = np.load(raw_path).astype(np.float32)
    if raw.shape != (h, w):
        raw = cv2.resize(raw, (w, h), interpolation=cv2.INTER_LINEAR)

    # High-pass: kill the scene-scale ramp (the measured failure mode).
    # The blur is MASKED-NORMALIZED (blur(raw*a)/blur(a)) so the paper
    # background never mixes into the low-pass -- an unmasked blur drags
    # the low estimate down near the card boundary and the subtraction
    # rings there, i.e. displacement exactly where edges must stay pinned.
    sigma = min(w, h) / 4.0
    alpha = np.asarray(rgba.split()[3]).astype(np.float32) / 255.0
    num = cv2.GaussianBlur(raw * alpha, (0, 0), sigma)
    den = cv2.GaussianBlur(alpha, (0, 0), sigma)
    low = num / np.maximum(den, 1e-4)
    hp = (raw - low) * alpha  # off-card = exactly on the card

    # Robust normalize: 3*std inside the alpha -> full band.
    vals = hp[alpha > 0.5]
    scale = 3.0 * vals.std() if vals.size else 1.0
    rel = np.clip(hp / max(scale, 1e-6), -1, 1)
    rel8 = np.round(rel * 127 + 128).astype(np.uint8)
    Image.fromarray(rel8, "L").save(OUT / f"{name}.png")
    manifest[name] = {"map": f"relief/{name}.png", "band": TARGETS[name],
                      "sigmaPx": round(sigma, 1), "clipStd": 3.0,
                      "size": [w, h]}

    # Evidence row: crop | raw depth | relief, height-normalized.
    th = 360
    def scaled(im):
        return im.resize((max(1, int(im.width * th / im.height)), th))
    rawv = (255 * (raw - raw.min()) / max(float(np.ptp(raw)), 1e-6)).astype(np.uint8)
    row_ims = [scaled(flat), scaled(Image.fromarray(rawv, "L").convert("RGB")),
               scaled(Image.fromarray(rel8, "L").convert("RGB"))]
    rw = sum(i.width for i in row_ims) + 20
    row = Image.new("RGB", (rw, th), (30, 30, 30))
    x = 0
    for im in row_ims:
        row.paste(im, (x, 0)); x += im.width + 10
    sheet_rows.append((name, row))
    print(f"{name}: {w}x{h} sigma={sigma:.0f}px band=+/-3std", file=sys.stderr)

sw = max(r.width for _, r in sheet_rows)
sh = sum(r.height + 26 for _, r in sheet_rows)
sheet = Image.new("RGB", (sw, sh), (30, 30, 30))
from PIL import ImageDraw
d = ImageDraw.Draw(sheet)
y = 0
for name, row in sheet_rows:
    d.text((6, y + 4), f"{name}   [crop | DAv2 raw | high-passed relief]",
           fill=(230, 220, 190))
    sheet.paste(row, (0, y + 26))
    y += row.height + 26
sheet.save(HERE / "evidence-relief-maps.png")
(HERE / "relief.json").write_text(json.dumps(manifest, indent=1))
print(json.dumps({"maps": list(manifest), "evidence": "evidence-relief-maps.png"}))
