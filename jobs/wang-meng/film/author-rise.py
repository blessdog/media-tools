#!/usr/bin/env python3
"""Author ONE leg of the continuous bottom-to-top rise. One job.

The film is a single slow rise up the scroll at full width, and the rise
PAUSES to move toward whatever is actually moving -- Ryan, 2026-08-21:
"the way people investigate things, they look from a distance and then
slowly zoom in on certain things that are interesting. Like if there's
some movement, we can slowly move toward it."  (knowledge/the-camera-
moves-toward-motion.md)

That is the whole difference from film/paths/leg-slow-*.json, which
zigzagged between identical keys and therefore always came back to the
same framing -- his complaint: "the same perspective, just floating
right above, never backing out, not really zooming in."

Approach targets come from the zone's OWN living-masks/index.json, so a
region that is not animated cannot be approached, and the rise simply
passes it. Classes marked `still` are never targets.

usage:
  author-rise.py --zone z3w --from-y 11000 --to-y 6600 [--rate 110]
                 [--pushes 2] [--out FILE]
JSON summary on stdout; the path is written to film/paths/rise-<zone>.json
"""
import argparse, json, math
from pathlib import Path

HERE = Path(__file__).parent            # film/
JOB = HERE.parent                       # jobs/wang-meng

ap = argparse.ArgumentParser()
ap.add_argument("--zone", required=True)
ap.add_argument("--from-y", type=float, required=True, help="camera CENTRE, master px, at t=0")
ap.add_argument("--to-y", type=float, required=True, help="camera CENTRE, master px, at the end")
ap.add_argument("--rate", type=float, default=80.0,
                help="master px per second of rise. Was 110 until 2026-08-24; "
                     "Ryan on the re-authored legs: 'some of the shots were "
                     "panning too fast'")
ap.add_argument("--approach", type=float, default=5.0,
                help="seconds to move in on a target, and the same to come back "
                     "out. Was 3.5, which made the approach the FASTEST move in "
                     "the leg -- it covers the most distance in the least time, "
                     "so slowing the traverse alone would not have fixed it")
ap.add_argument("--pushes", type=int, default=2, help="max approach moments in this leg")
ap.add_argument("--breathe-floor", type=float, default=0.07,
                help="camZ the breath never goes BELOW except at the leg seams. "
                     "A traverse at camZ=0 is a pan BY CONSTRUCTION -- measured "
                     "2026-08-21, collapsing all 13 plane depths onto one changed "
                     "0 of 2,073,600 px. The old breath returned to 0 every "
                     "period and 21-67%% of each leg's keys sat there, so those "
                     "stretches were Ken Burns pans with the parallax machinery "
                     "switched off. Ryan, 2026-08-24: 'if you're zoomed in at the "
                     "same crop shot the entire time it doesn't show off the "
                     "parallaxing. You got to pull out and go forward, push in "
                     "and go.'")
# 0.18 IS A CEILING, NOT A STARTING POINT. Raised to 0.45 on 2026-08-24 to
# buy parallax and it TORE THE PAINTING: at that separation the disocclusion
# behind the near cliff is wider than the fill can cover, and check-holes found
# 2 of 16 frames holed, largest 4,198px. Ryan: "whatever you did to the right
# tore the canvas, tore a huge asshole in the canvas." The flatness was never
# the peak being too low -- it was the breath RETURNING TO ZERO mid-leg.
ap.add_argument("--breathe", type=float, default=0.18,
                help="peak camZ of the breath. Depth on this painting comes from "
                     "DIFFERENTIAL SCALE, never from sliding or deforming planes "
                     "(knowledge/depth-may-resize-never-deform.md). 0.18 is "
                     "Ryan's 2026-08-21 verdict on the smooth 3-pose breathe; "
                     "a monotonic ramp wants 0.11 instead because it ends at its "
                     "peak rather than returning.")
ap.add_argument("--breathe-period", type=float, default=24.0,
                help="seconds per full breath, in and back out. Keys are POSES: "
                     "sample() eases to zero velocity at every key, so breath "
                     "keys land no closer than period/2 apart.")
ap.add_argument("--drift-fov", type=float, default=0.86,
                help="how far the WIDE framing drifts between approaches, as a "
                     "fraction of WIDE. The camera used to SIT at exactly WIDE "
                     "for 11-23s and then snap to the push and back, so the whole "
                     "film held two framings and nothing between them. Ryan, "
                     "2026-08-24: 'if you are zoomed in at the same crop shot the "
                     "entire time it doesn't show off the parallaxing. You got to "
                     "pull out and go forward, push in and go.' A wide that "
                     "breathes is also what makes the next push mean something.")
ap.add_argument("--push-fov", type=float, default=0.62,
                help="fraction of the WIDE framing visible at the closest point; "
                     "0.62 shows 62%% of the width, i.e. fov = 1/0.62")
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--skip", default="", help="comma-separated region ids already approached in an earlier leg")
ap.add_argument("--out", default=None)
a = ap.parse_args()

Z = JOB / "journey" / a.zone
meta = json.loads((Z / "plate.json").read_text())
X0, Y0, X1, Y1 = meta["masterBox"]
K = meta["masterPxPerRegionPx"]
PW, PH = meta["size"]

# render-parallax fov is a ZOOM MULTIPLIER, not a px ratio: 1.0 already frames
# the plate edge to edge and LARGER means closer (tools/render-parallax.py:104,
# fpx = fov * width). Getting this backwards renders the mount as cream bars.
WIDE = 1.0
half_m = 0.28125 * PW * K / WIDE         # half the window height, in MASTER px


def norm(mx, my):
    return ((mx - X0) / K / PW, (my - Y0) / K / PH)


def clamp_key(x, y, fov):
    """Keep the window inside the plate. A key that hangs off the edge shows
    the mount, not the painting."""
    hx = 0.5 / fov
    hy = 0.28125 * PW / (fov * PH)
    if 2 * hx >= 1.0:
        x = 0.5
    else:
        x = min(max(x, hx), 1 - hx)
    if 2 * hy >= 1.0:
        y = 0.5
    else:
        y = min(max(y, hy), 1 - hy)
    return round(x, 4), round(y, 4)


# ---- what is worth approaching in this leg -------------------------------
idx = json.loads((Z / "living-masks" / "index.json").read_text())
SKIP = {s for s in a.skip.split(",") if s}
lo, hi = min(a.from_y, a.to_y), max(a.from_y, a.to_y)
cand = []
for rid, v in idx.items():
    if v["class"] == "still":
        continue
    px0, py0, px1, py1 = v["plateBox"]
    my = Y0 + (py0 + py1) / 2 * K
    # STRICTLY inside the leg. A target the rise never reaches makes the
    # camera detour off the span and back, which is the zigzag we removed.
    if not (lo <= my <= hi):
        continue
    if rid in SKIP:
        continue
    cand.append({"id": rid, "cls": v["class"], "px": v["px"],
                 "mx": X0 + (px0 + px1) / 2 * K, "my": my,
                 "w": (px1 - px0), "h": (py1 - py0)})
cand.sort(key=lambda c: -c["px"])
targets = sorted(cand[:a.pushes], key=lambda c: -c["my"])   # bottom-first, we rise

# ---- the rise, with a pause at each target -------------------------------
span = a.from_y - a.to_y                  # positive: we are rising
keys, t = [], 0.0
x_w, y_w = clamp_key(0.5, norm(0, a.from_y)[1], WIDE)
keys.append({"t": 0.0, "x": x_w, "y": y_w, "fov": round(WIDE, 4)})

# THE WIDE IS NOT ONE NUMBER. Alternating a held WIDE with a held push gives
# the film exactly two framings; the traverse between approaches is where a
# pull-out lives, and it was flat. Each traverse now drifts OUT to
# WIDE*--drift-fov and back, so the camera is always either opening up or
# closing in and the arrival at a target is a change of direction, not a snap
# out of stillness. fov below WIDE would show the mount, so the drift is
# strictly a widening of the CLOSER end, never past the plate edge.
# THE TRAVERSE RESTS SLIGHTLY IN, SO THE PULL-OUT IS A REAL MOVE. Resting at
# WIDE means resting at the plate edge, and from there the only direction is
# closer -- which is how the film ended up alternating two framings with a snap
# between them. Rest at CRUISE instead and open to WIDE just before each
# approach, so every target arrives as OUT, then FORWARD.
CRUISE = WIDE / a.drift_fov            # a touch closer than the plate edge
prev_my = a.from_y
keys[0]["fov"] = round(CRUISE, 4)
keys[0]["x"], keys[0]["y"] = clamp_key(0.5, norm(0, a.from_y)[1], CRUISE)
for c in targets:
    leg_t = abs(prev_my - c["my"]) / a.rate
    # cruise most of the traverse, then OPEN to the plate edge for the last
    # ~2.5s before the target is reached: the pull-out that earns the push.
    if leg_t > 5.0:
        tm = t + leg_t * 0.60
        ym = norm(0, prev_my)[1] + (norm(0, c["my"])[1] - norm(0, prev_my)[1]) * 0.60
        xm, ym = clamp_key(0.5, ym, CRUISE)
        keys.append({"t": round(tm, 2), "x": xm, "y": ym, "fov": round(CRUISE, 4)})
    t += leg_t
    xw, yw = clamp_key(0.5, norm(0, c["my"])[1], WIDE)
    keys.append({"t": round(t, 2), "x": xw, "y": yw, "fov": round(WIDE, 4)})
    # notice it, then move toward it -- 3.5s in, 3s held, 3.5s back out
    fov_in = WIDE / a.push_fov      # smaller push_fov = closer
    xi, yi = clamp_key(*norm(c["mx"], c["my"]), fov_in)
    t += a.approach
    keys.append({"t": round(t, 2), "x": xi, "y": yi, "fov": round(fov_in, 4),
                 "_at": c["id"]})
    t += 3.0
    keys.append({"t": round(t, 2), "x": xi, "y": yi, "fov": round(fov_in, 4)})
    t += a.approach
    keys.append({"t": round(t, 2), "x": xw, "y": yw, "fov": round(WIDE, 4)})
    prev_my = c["my"]
    # settle back to cruise rather than parking at the plate edge
    t += 2.0
    xc, yc = clamp_key(0.5, norm(0, c["my"])[1], CRUISE)
    keys.append({"t": round(t, 2), "x": xc, "y": yc, "fov": round(CRUISE, 4)})

t += abs(prev_my - a.to_y) / a.rate
xe, ye = clamp_key(0.5, norm(0, a.to_y)[1], CRUISE)
# The closing pose. If the rise ends within 3s of the last key, MOVE that key
# rather than adding one -- a sub-3s gap stutters, because sample() eases to
# zero velocity at both ends of every segment.
_end = {"t": round(t, 2), "x": xe, "y": ye, "fov": round(CRUISE, 4)}
if keys and t - keys[-1]["t"] < 3.0:
    keys[-1] = _end
else:
    keys.append(_end)

# THE BREATH. Depth is spent CONTINUOUSLY across the leg, never as a spike:
# rise-*.json v1 held z at exactly 0.000 through every traverse and jumped to
# 0.10 only inside the approaches, which made the traverse provably flat
# (collapsing all 13 plane depths changed 0 of 2,073,600 px) and made the
# approaches read as zooms, because they were the only depth in the shot.
# See knowledge/light-parallax-is-011-and-continuous.md.
# A leg shorter than half a period would contain no extreme and therefore no
# breath at all -- z5w came out 9.2s long with z pinned at 0.000. Clamp the
# period to the leg so every leg gets at least one full breath.
PERIOD = min(a.breathe_period, max(t, 6.0))
# The seam taper. Long enough to be invisible under the 0.8s crossfade, short
# enough that it does not flatten the leg: 2.5s each end.
SEAM = min(2.5, t / 4.0)


def breath(tt):
    """A breath that never settles, tapered to 0 only at the leg's two seams.

    The old form was a raised cosine from 0 to --breathe, so it passed through
    zero depth once per period and the leg's own keys landed in those troughs.
    Now it swings between --breathe-floor and --breathe, and a separate seam
    taper brings it to 0 across the first and last SEAM seconds so consecutive
    legs still dissolve at the composition the painting actually is.
    """
    lo, hi = a.breathe_floor, a.breathe
    v = lo + (hi - lo) * 0.5 * (1 - math.cos(2 * math.pi * tt / PERIOD))
    edge = min(tt, max(t - tt, 0.0))
    if edge < SEAM:
        v *= 0.5 * (1 - math.cos(math.pi * max(edge, 0.0) / SEAM))
    return v

if a.breathe:
    half = PERIOD / 2.0
    # a pose at each breath extreme, but only where it does not crowd an
    # existing key -- keys closer than ~3s apart stutter (sample() eases to
    # zero velocity at every one).
    n_ext = int(t // half)
    for j in range(1, n_ext + 1):
        te = j * half
        if all(abs(te - k["t"]) > 3.0 for k in keys):
            u = None
            for k0, k1 in zip(keys, keys[1:]):
                if k0["t"] <= te <= k1["t"]:
                    u = (te - k0["t"]) / max(k1["t"] - k0["t"], 1e-9)
                    keys.append({"t": round(te, 2),
                                 "x": round(k0["x"] + (k1["x"] - k0["x"]) * u, 4),
                                 "y": round(k0["y"] + (k1["y"] - k0["y"]) * u, 4),
                                 "fov": round(k0["fov"] + (k1["fov"] - k0["fov"]) * u, 4)})
                    break
    keys.sort(key=lambda k: k["t"])
    for k in keys:
        k["z"] = round(breath(k["t"]), 4)
    # Every leg STARTS AND ENDS AT REST. The legs are dissolved together, so a
    # leg that ends mid-breath hands the next one a z discontinuity -- and at
    # z=0 the composition is exactly the painting, which is the right thing to
    # cut on. (knowledge/depth-may-resize-never-deform.md)
    keys[0]["z"] = 0.0
    keys[-1]["z"] = 0.0
else:
    for k in keys:
        k.setdefault("z", 0.0)

out = Path(a.out) if a.out else HERE / "paths" / f"rise-{a.zone}.json"
out.write_text(json.dumps({
    "fps": a.fps, "duration": round(t, 2),
    "_note": f"leg of the continuous rise, zone {a.zone}, master centre "
             f"{a.from_y:.0f} -> {a.to_y:.0f} at {a.rate:g}px/s. Approaches: "
             + (", ".join(c["id"] for c in targets) or "none animated in range"),
    "keys": keys}, indent=1))
print(json.dumps({"tool": "author-rise", "out": str(out), "zone": a.zone,
                  "duration": round(t, 2), "keys": len(keys),
                  "wideFov": round(WIDE, 4),
                  "approaches": [c["id"] for c in targets]}, indent=1))
