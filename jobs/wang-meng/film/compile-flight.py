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
route = None  # loaded after args
FPS = None

ap = argparse.ArgumentParser()
ap.add_argument("--route", default="route.json")
ap.add_argument("--out", default="FULL-SCROLL-FLIGHT.mp4")
ap.add_argument("--legs-only", action="store_true")
ap.add_argument("--assemble-only", action="store_true")
ap.add_argument("--leg", help="render just this zone's leg")
ap.add_argument("--allow-dead-zones", action="store_true",
                help="render legs whose zone has NO living cycles (see the gate below). "
                     "Only for a deliberate camera-only probe Ryan is not being shown.")
args = ap.parse_args()

route = json.loads((HERE / args.route).read_text())
FPS = route["fps"]
TAG = Path(args.route).stem.replace("route", "").strip("-") or ""
SUF = f"-{TAG}" if TAG else ""
legs = route["legs"]

# -- THE LIVING GATE (2026-08-20) -------------------------------------------
# Ryan, after five days of being shown camera moves over still ink:
#   "Bring it to life. That is number one. Quit pushing that off... you still
#    keep putting it off and showing me the same fucking zigzag Ken Burns
#    left, right, camera pan. I don't know how to drill that into your skull."
#
# He is right, and the failure is structural: parallax is easy and cheap, and
# motion is slow authoring work, so every session drifts to the camera and
# calls it progress. Only z1 has ever had living cycles. Every waterfall,
# cascade, stream and pine grove above it is a STILL IMAGE being flown past.
#
# So this is a gate, not a note -- prose laws are read, gates are executed.
# A leg whose zone has no living cycles will not render. If you find yourself
# reaching for --allow-dead-zones to get a pretty flight out the door, THAT
# IS THE CORNER BEING CUT. Go build the cycles (living/build-plane-cycles.py,
# tools/animate-strokes.py) for that zone first.
dead = [l["zone"] for l in legs if not l.get("living")]
if dead and not args.allow_dead_zones:
    sys.exit(
        "LIVING GATE: these zones have no living cycles, so their legs would be\n"
        f"  a camera move over a still painting: {', '.join(dead)}\n"
        "That is the exact thing Ryan has rejected for five days running.\n"
        "Build the water/foliage cycles for those zones, add a 'living' key to\n"
        "their legs, and render again. Override only for a probe he will not\n"
        "be shown: --allow-dead-zones")

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
        (HERE / f"paths/leg{SUF}-{z}.json").write_text(json.dumps(pj, indent=1))
        cmd = ["python3", str(REPO / "tools/render-parallax.py"),
               "--layers", str((HERE / leg["layers"]).resolve()),
               "--path", str(HERE / f"paths/leg{SUF}-{z}.json"),
               "--out", str(HERE / f"frames/leg{SUF}-{z}"),
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
                        "-i", str(HERE / f"frames/leg{SUF}-{z}/%05d.png"),
                        "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p",
                        str(HERE / f"leg{SUF}-{z}.mp4")],
                       check=True, capture_output=True)

# -- assemble: chained xfades + call at full volume ---------------------------
if not args.legs_only and not args.leg:
    inputs, filters = [], []
    for i, leg in enumerate(legs):
        inputs += ["-i", str(HERE / f"leg{SUF}-{leg['zone']}.mp4")]
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
    cmd = ["ffmpeg", "-y", *inputs]
    if route.get("audio"):
        cmd += ["-i", str((HERE / route["audio"]).resolve())]
    cmd += ["-filter_complex", fc, "-map", prev]
    if route.get("audio"):
        cmd += ["-map", f"{len(legs)}:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p",
            str(HERE / args.out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"assembly failed:\n{r.stderr[-800:]}")
    print(json.dumps({"out": args.out,
                      "legs": [l["zone"] for l in legs],
                      "handoffs": [h["at"] for h in route["handoffs"]]}))
