#!/usr/bin/env python3
"""Re-key a living layer from a FINE plane stack onto the COARSE stack that
merge-planes.py built from it.

One job. It does not build cycles, cut regions, or render.

WHY IT IS NEEDED. render-parallax's --living is keyed by PLANE NAME
(render-parallax.py:360 drops any name the stack does not have). merge-planes
gives the merged planes new names, so a coarse stack silently loses every patch
and renders a still painting under a moving camera -- which is the MOTION BEFORE
CAMERA law's exact failure, arriving as a warning nobody reads.

THE ARITHMETIC. A patch's box is relative to its plane's layer image, whose
origin is that plane's offset. When plane P is merged into plane M, the same
pixels now live at a different origin, so every box shifts by
(offset(P) - offset(M)). merged layers.json records `members`, which is what
makes this a remap and not a rebuild.

usage:
  remap-living.py --living living/living-z1.json --fine journey/z1/layers-pinned
                  --coarse journey/z1/layers-pinned-coarse4 --out living/living-z1-coarse4.json
"""
import argparse, json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--living", required=True)
    ap.add_argument("--fine", required=True, help="the stack the living layer was built against")
    ap.add_argument("--coarse", required=True, help="a stack from merge-planes.py")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    living = json.load(open(a.living))
    fine = {p["name"]: p for p in json.load(open(f"{a.fine}/layers.json"))["planeList"]
            if p.get("layer")}
    coarse = [p for p in json.load(open(f"{a.coarse}/layers.json"))["planeList"]
              if p.get("layer")]

    owner = {}
    for m in coarse:
        if "members" not in m:
            raise SystemExit(f"REFUSING: {m['name']} has no `members` — not a merge-planes stack")
        for name in m["members"]:
            owner[name] = m

    out, moved, dropped = {}, 0, []
    for pname, entry in living.items():
        m = owner.get(pname)
        if m is None:
            dropped.append(pname)
            continue
        f = fine.get(pname)
        if f is None:
            dropped.append(pname)
            continue
        dx = f["offset"][0] - m["offset"][0]
        dy = f["offset"][1] - m["offset"][1]
        bucket = out.setdefault(m["name"], {"patches": []})
        for patch in entry["patches"]:
            q = dict(patch)
            q["box"] = [patch["box"][0] + dx, patch["box"][1] + dy]
            q["fromPlane"] = pname
            bucket["patches"].append(q)
            moved += 1

    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({
        "out": a.out,
        "planesBefore": len(living), "planesAfter": len(out),
        "patchesRemapped": moved,
        "droppedPlanes": dropped,
    }, indent=1))
    if dropped:
        raise SystemExit(f"REFUSING to pass silently: {len(dropped)} plane(s) had no owner")


if __name__ == "__main__":
    main()
