#!/usr/bin/env python3
"""Build living PLANE TEXTURE cycles for render-parallax --living.

For each target plane: crop every animate-strokes drawing (full-plate,
lossless PNG) at the plane's box in the FILLED stack, keep the plane's own
alpha. The plane's ink moves; its footprint and depth do not. Output:
living/plane-cycles/<plane>/%03d.png + living.json (the --living map).
"""
import json
import sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
Z1 = HERE.parent / "journey" / "z1"

# The two wave cycles are the -v2 rebuild: the pre-fix wave field carried 1.7
# turns of cross-chop phase per cycle, so the loop popped at the wrap (measured
# seam/max-step 1.34 on water, 1.61 on upper-stream). The sway cycles never had
# it -- pine 0.81, pine-gust 0.05, fan 0.85 -- which is why only these two are
# rebuilt. See living/seam.py.
TARGETS = {
    "water": "water-drawings-v2",
    "upper-stream-water": "upperstream-drawings-v2",
    "pine-over-bridge": "pine-drawings",
}
ONLY = set(sys.argv[1:])

meta = json.loads((Z1 / "layers-filled" / "layers.json").read_text())
lj = HERE / "living.json"
living = json.loads(lj.read_text()) if lj.exists() else {}
for p in meta["planeList"]:
    name = p["name"]
    if name not in TARGETS or (ONLY and name not in ONLY):
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

lj.write_text(json.dumps(living, indent=1))
print("living map -> living/living.json")
