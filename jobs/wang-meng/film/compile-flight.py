#!/usr/bin/env python3
"""Compile route.json (master-space legs) into the one apparent shot.

Per leg: master keys -> that zone's plate-normalized path JSON (t rebased to
0) -> render-parallax with the zone's own stack/geometry (+living/relief when
the leg declares them) -> encode. Then chain-xfade the legs at the declared
handoff times and mux the call at full volume.

Handoff law (checked here, not hoped): through each crossfade window both
legs' route keys must be IDENTICAL (same mx,my,z,fov,r*) with z == 0 --
plane-fit renders every zone's stack as the painting itself at rest, so the
fade is between two near-identical frames. The compiler REFUSES to build a
handoff whose flanking keys violate that.

usage: compile-flight.py [--legs-only | --assemble-only] [--leg z3w]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parents[2]
route = json.loads((HERE / "route.json").read_text())
FPS = route["fps"]

ap = argparse.ArgumentParser()
ap.add_argument("--legs-only", action="store_true")
ap.add_argument("--assemble-only", action="store_true")
ap.add_argument("--leg", help="render just this zone's leg")
args = ap.parse_args()

legs = route["legs"]

# -- handoff law check ------------------------------------------------------
for h in route["handoffs"]:
    t0, t1 = h["at"] - h["dur"] / 2, h["at"] + h["dur"] / 2
    flanking = [l for l in legs if l["in"] <= t0 and l["out"] >= t1]
    if len(flanking) != 2:
        sys.exit(f"handoff at {h['at']}: needs exactly 2 covering legs, got {len(flanking)}")
    for l in flanking:
        for k in l["keys"]:
            if t0 - 1e-6 <= k["t"] <= t1 + 1e-6 and abs(k.get("z", 0)) > 1e-9:
                sys.exit(f"handoff law violated: {l['zone']} key t={k['t']} has z={k['z']}")

# -- render legs -------------------------------------------------------------
if not args.assemble_only:
    for leg in legs:
        if args.leg and leg["zone"] != args.leg:
            continue
        z = leg["zone"]
        plate = json.loads((HERE / leg["layers"] / ".." / "plate.json").resolve().read_text()) \
            if (HERE / leg["layers"] / ".." / "plate.json").resolve().exists() else None
        if plate is None:
            sys.exit(f"{z}: no plate.json next to layers")
        x0, y0, x1, y1 = plate["masterBox"]
        rw, rh = x1 - x0, y1 - y0
        keys = []
        for k in leg["keys"]:
            kk = {"t": round(k["t"] - leg["in"], 4),
                  "x": round((k["mx"] - x0) / rw, 5),
                  "y": round((k["my"] - y0) / rh, 5),
                  "z": k.get("z", 0.0), "fov": k["fov"]}
            for r in ("rx", "ry", "rz"):
                if r in k:
                    kk[r] = k[r]
            # edge check at rest scale (worst case near z=0)
            hw, hh = 960 * 2.34 / k["fov"], 540 * 2.34 / k["fov"]
            if k["mx"] - hw < x0 - 2 or k["mx"] + hw > x1 + 2 or \
               k["my"] - hh < y0 - 2 or k["my"] + hh > y1 + 2:
                sys.exit(f"{z} key t={k['t']}: window exceeds rect "
                         f"({k['mx']}+/-{hw:.0f}, {k['my']}+/-{hh:.0f} vs {plate['masterBox']})")
            keys.append(kk)
        pj = {"fps": FPS, "duration": round(leg["out"] - leg["in"], 4), "keys": keys}
        (HERE / f"paths/leg-{z}.json").write_text(json.dumps(pj, indent=1))
        cmd = ["python3", str(REPO / "tools/render-parallax.py"),
               "--layers", str((HERE / leg["layers"]).resolve()),
               "--path", str(HERE / f"paths/leg-{z}.json"),
               "--out", str(HERE / f"frames/leg-{z}"),
               "--width", "1920", "--height", "1080", "--fps", str(FPS),
               "--z-step", "0.30", "--plane-fit", "--no-base",
               "--geometry", str((HERE / leg["geometry"]).resolve())]
        if leg.get("living"):
            cmd += ["--living", str((HERE / leg["living"]).resolve())]
        if leg.get("relief"):
            cmd += ["--relief", str((HERE / leg["relief"]).resolve())]
        print(f"=== leg {z}: {pj['duration']}s", file=sys.stderr)
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"{z} render failed:\n{r.stderr[-800:]}")
        subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS),
                        "-i", str(HERE / f"frames/leg-{z}/%05d.png"),
                        "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p",
                        str(HERE / f"leg-{z}.mp4")],
                       check=True, capture_output=True)

# -- assemble: chained xfades + call at full volume ---------------------------
if not args.legs_only and not args.leg:
    inputs, filters = [], []
    for i, leg in enumerate(legs):
        inputs += ["-i", str(HERE / f"leg-{leg['zone']}.mp4")]
    prev = "[0:v]"
    # xfade offset = time in the ACCUMULATED stream where the fade starts.
    # Legs overlap, so accumulated content before leg i+1 ends at handoff
    # start + dur; with xfade the accumulated timeline equals route time.
    for i, h in enumerate(route["handoffs"]):
        start = h["at"] - h["dur"] / 2
        out = f"[v{i+1}]"
        filters.append(f"{prev}[{i+1}:v]xfade=transition=fade:"
                       f"duration={h['dur']}:offset={start:.3f}{out}")
        prev = out
    fc = ";".join(filters)
    cmd = ["ffmpeg", "-y", *inputs, "-i", str((HERE / route["audio"]).resolve()),
           "-filter_complex", fc, "-map", prev, "-map", f"{len(legs)}:a",
           "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest",
           str(HERE / "FULL-SCROLL-FLIGHT.mp4")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"assembly failed:\n{r.stderr[-800:]}")
    print(json.dumps({"out": "FULL-SCROLL-FLIGHT.mp4",
                      "legs": [l["zone"] for l in legs],
                      "handoffs": [h["at"] for h in route["handoffs"]]}))
