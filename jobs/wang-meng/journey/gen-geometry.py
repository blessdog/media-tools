#!/usr/bin/env python3
"""Author a zone's geometry.json from plane names, using Z1's proven role
values (STATE: 平遠 roles from the pilot). Rules, not estimates:
walls -> tiltX -8e-05 + tiltY away from their side; water/rapids/stream ->
tiltX -0.00026; ledges/banks/paths (grounds) -> tiltX -0.00022; rock masses
-> tiltX -0.00012; bridges, pines, figures, crowns -> BILLBOARD (never tilt
what a figure rides; z1 note). usage: gen-geometry.py z2"""
import json
import sys
from pathlib import Path

z = sys.argv[1]
d = Path(__file__).parent / z
meta = json.loads((d / "layers-cut" / "layers.json").read_text())
W = meta["size"][0]
geo = {"_note": f"{z} geometry by role from z1 proven values (gen-geometry.py)"}
for p in meta["planeList"]:
    if not p.get("layer"):
        continue
    n = p["name"]
    cx = (p["bbox"][0] + p["bbox"][2]) / 2 / W
    if "wall" in n or "cliff" in n:
        # side from the NAME first (physical identity), plate position second
        side = -1 if n.startswith("left") or "-left" in n else \
               1 if n.startswith("right") or "-right" in n else \
               (1 if cx > 0.5 else -1)
        geo[n] = {"tiltX": -8e-05, "tiltY": round(0.0002 * side, 6)}
    elif "rock" in n or "boulder" in n or "outcrop" in n:
        geo[n] = {"tiltX": -0.00012}
    elif any(k in n for k in ("water", "rapids", "stream", "falls")):
        geo[n] = {"tiltX": -0.00026}
    elif any(k in n for k in ("ledge", "bank", "path", "shore")):
        geo[n] = {"tiltX": -0.00022}
    # bridges, pines, trees, figures, crowns: billboard -- no entry
(d / "geometry.json").write_text(json.dumps(geo, indent=1))
print(json.dumps(geo, indent=1))
