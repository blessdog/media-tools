#!/usr/bin/env python3
"""Build living PLANE TEXTURE cycles for render-parallax --living.

For each target plane: crop every animate-strokes drawing (full-plate,
lossless PNG) at the plane's box in the FILLED stack, keep the plane's own
alpha. The plane's ink moves; its footprint and depth do not. Output:
living/plane-cycles/<plane>/%03d.png + living.json (the --living map).
"""
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
Z1 = HERE.parent / "journey" / "z1"

TARGETS = {
    "water": "water-drawings",
    "upper-stream-water": "upperstream-drawings",
    "pine-over-bridge": "pine-drawings",
}

meta = json.loads((Z1 / "layers-filled" / "layers.json").read_text())
living = {}
for p in meta["planeList"]:
    name = p["name"]
    if name not in TARGETS:
        continue
    tex = Image.open(Z1 / "layers-filled" / p["layer"]).convert("RGBA")
    ox, oy = p["offset"]
    w, h = tex.size
    alpha = tex.split()[3]
    src = HERE / "plane-cycles" / TARGETS[name]
    cyc = json.loads((src / "cycle.json").read_text())
    outd = HERE / "plane-cycles" / name
    outd.mkdir(parents=True, exist_ok=True)
    for i in range(cyc["drawings"]):
        d = Image.open(src / f"dr-{i:03d}.png").convert("RGBA")
        crop = d.crop((ox, oy, ox + w, oy + h))
        crop.putalpha(alpha)
        crop.save(outd / f"{i:03d}.png")
    living[name] = {"dir": str(outd), "n": cyc["drawings"], "on": cyc["on"]}
    print(f"{name}: {cyc['drawings']} textures at {w}x{h}")

(HERE / "living.json").write_text(json.dumps(living, indent=1))
print("living map -> living/living.json")
