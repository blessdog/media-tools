#!/usr/bin/env python3
"""stations-slow.json -> route JSON, with pacing as LAW rather than taste.

Why this exists (Ryan, 2026-08-20): "a painting is not something you race
through... it's about the journey." Hand-timed keys made me guess durations,
and I guessed fast -- the 42s cut ran 306 apparent px/s through the gorge
against ~250 in the opening he liked. Here the durations are DERIVED: every
move takes as long as its distance, zoom and dolly demand at the capped
rates, so the film's length is an OUTPUT of the painting, not an input from
a soundtrack.

The station idiom, per Ryan's own description ("zoom out back out at a scene
and then scroll slowly and push into it"):

    arrive WIDE -> hold -> slow scroll (still wide) -> PUSH to detail
                -> hold -> retreat back out to WIDE (rest)

Zone handoffs happen during a bridge hold at a wide REST state (z=0, no
rotation) that both legs carry with identical keys -- which is exactly the
handoff law compile-flight.py enforces, satisfied by construction.

Edge safety: every state is clamped inside its zone rect for its own fov
(and inside BOTH rects at a zone boundary), with extra margin wherever the
camera is rotated, since rotation shifts the frame.

usage: build-route.py [--stations stations-slow.json] [--out route-slow.json]
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
K = 2.34            # master px per plate px
OUT_W, OUT_H = 1920, 1080
ROT_MARGIN = 220    # master px of slack when the camera is turned

ap = argparse.ArgumentParser()
ap.add_argument("--stations", default="stations-slow.json")
ap.add_argument("--out", default="route-slow.json")
args = ap.parse_args()

spec = json.loads((HERE / args.stations).read_text())
P = spec["pacing"]
stations = spec["stations"]

# per-zone extras: only z1 has living cycles and relief maps built so far
EXTRAS = {"z1": {"living": "../living/living-gust.json",
                 "relief": "../journey/z1/relief.json"}}

# The frame must also stay inside the PAINTED area. Measured off the master 2026-08-20: the great collector seal spans
# x2550-3700 / y100-1000, the inscription x4200-6300 / y80-1550. One flat
# ceiling either crops calligraphy into prominence (banned) or amputates the
# peaks the film ends on, so the ceiling is per-station: full width below
# y1600, and a station may declare its own "safe" rect to climb higher
# through the gap LEFT of the inscription.
CONTENT = spec.get("contentRect", [0, 1600, 6586, 15923])

rects = {}
for st in stations:
    z = st["zone"]
    if z not in rects:
        rects[z] = json.loads(
            (HERE / f"../journey/{z}/plate.json").resolve().read_text())["masterBox"]


def clamp(state, zones, safe=None):
    """Put a camera state inside every named zone's rect AND the painted-area
    rect, raising fov if the window cannot fit at all. Returns a new state."""
    s = dict(state)
    safe = safe or CONTENT
    boxes = []
    for z in zones:
        r = rects[z]
        boxes.append([max(r[0], safe[0]), max(r[1], safe[1]),
                      min(r[2], safe[2]), min(r[3], safe[3])])
    rotated = any(abs(s.get(r, 0.0)) > 1e-9 for r in ("rx", "ry", "rz"))
    m = ROT_MARGIN if rotated else 0
    for x0, y0, x1, y1 in boxes:
        # smallest fov whose half-window still fits the rect (plus margin)
        fov_min_x = OUT_W / 2 * K / max((x1 - x0) / 2 - m, 1)
        fov_min_y = OUT_H / 2 * K / max((y1 - y0) / 2 - m, 1)
        s["fov"] = max(s["fov"], fov_min_x, fov_min_y)
    for x0, y0, x1, y1 in boxes:
        hw = OUT_W / 2 * K / s["fov"] + m
        hh = OUT_H / 2 * K / s["fov"] + m
        s["mx"] = min(max(s["mx"], x0 + hw), x1 - hw)
        s["my"] = min(max(s["my"], y0 + hh), y1 - hh)
    s["mx"], s["my"] = round(s["mx"]), round(s["my"])
    s["fov"] = round(s["fov"], 4)
    return s


def duration(a, b):
    """How long this move MUST take so nothing outruns the caps."""
    d_master = math.hypot(b["mx"] - a["mx"], b["my"] - a["my"])
    avg_fov = (a["fov"] + b["fov"]) / 2
    t_trans = (d_master * avg_fov / K) / P["speedCapPxPerSec"]
    t_zoom = abs(math.log(b["fov"] / a["fov"])) / P["zoomRatePerSec"]
    t_dolly = abs(b.get("z", 0.0) - a.get("z", 0.0)) / P["dollyRatePerSec"]
    return round(max(t_trans, t_zoom, t_dolly, P["minMove"]), 2)


def state(src, **over):
    s = {"mx": src["mx"], "my": src["my"],
         "fov": src.get("fov", over.get("fov", 1.0)),
         "z": src.get("z", 0.0)}
    for r in ("rx", "ry", "rz"):
        if r in src:
            s[r] = src[r]
    s.update(over)
    return s


# ---- expand stations into a single timeline of (t, zone, state) -------------
timeline = []
t = 0.0
prev = None
for i, st in enumerate(stations):
    z = st["zone"]
    nxt = stations[i + 1] if i + 1 < len(stations) else None
    boundary = nxt is not None and nxt["zone"] != z
    share = [z, nxt["zone"]] if boundary else [z]

    safe = st.get("safe")
    wide = clamp(state(st["wide"], z=0.0), [z], safe)
    rest = clamp(state(st["wide"], z=0.0), share, safe)  # legal in both at a seam
    detail = clamp(state(st["detail"]), [z], safe)

    if prev is None:
        timeline.append((0.0, z, wide))
    else:
        t += duration(prev, wide)
        timeline.append((t, z, wide))
    t += P["holdWide"]
    timeline.append((t, z, wide))

    if st.get("scroll"):
        scr = clamp(state(st["scroll"], fov=wide["fov"], z=0.0), [z], safe)
        t += duration(wide, scr)
        timeline.append((t, z, scr))
        push_from = scr
    else:
        push_from = wide

    t += duration(push_from, detail)
    timeline.append((t, z, detail))
    t += P["holdDetail"]
    timeline.append((t, z, detail))

    if nxt is None:
        prev = detail          # the last station ENDS on its move, no retreat
        continue
    t += duration(detail, rest)
    timeline.append((t, z, rest))
    if boundary:
        t += P["bridgeHold"]
        timeline.append((t, z, rest))
    prev = rest

total = round(t, 2)

# ---- cut the timeline into per-zone legs, overlapping at the bridge holds ---
legs, i = [], 0
while i < len(timeline):
    z = timeline[i][1]
    j = i
    while j + 1 < len(timeline) and timeline[j + 1][1] == z:
        j += 1
    keys = [{"t": round(tt, 3), **s} for tt, _, s in timeline[i:j + 1]]
    # Carry the PRECEDING zone's bridge-hold pair backwards so this leg spans
    # the crossfade. Only backwards: those two keys were clamped against both
    # rects. Carrying the NEXT station's wide keys forward instead would hand
    # a leg a window legal only in the other zone -- measured 2026-08-20, the
    # z1 leg rendering a z3w-wide frame 1688 px above z1's rect, paper fill
    # across the top of the frame.
    if i > 0:
        keys = [{"t": round(timeline[i - 2][0], 3), **timeline[i - 2][2]},
                {"t": round(timeline[i - 1][0], 3), **timeline[i - 1][2]}] + keys
    leg = {"zone": z, "in": keys[0]["t"], "out": keys[-1]["t"],
           "layers": f"../journey/{z}/layers-filled",
           "geometry": f"../journey/{z}/geometry.json"}
    leg.update(EXTRAS.get(z, {}))
    leg["keys"] = keys
    legs.append(leg)
    i = j + 1

handoffs = []
for a, b in zip(legs, legs[1:]):
    mid = (b["in"] + a["out"]) / 2
    handoffs.append({"at": round(mid, 3), "dur": P["crossfade"],
                     "note": f"{a['zone']}->{b['zone']} at a wide rest hold"})

route = {
 "_note": spec["_note"] + " GENERATED by build-route.py from stations-slow.json "
          "-- edit the stations, not this file.",
 "fps": 24, "audio": None, "legs": legs, "handoffs": handoffs,
}
(HERE / args.out).write_text(json.dumps(route, indent=1))

# ---- pace report: prove nothing outruns the cap ----------------------------
print(f"{'segment':38s} {'dur':>6s} {'px/s':>7s} {'zoom/s':>7s}")
worst = 0.0
for (t0, _, a), (t1, _, b) in zip(timeline, timeline[1:]):
    dt = t1 - t0
    if dt <= 0:
        continue
    d = math.hypot(b["mx"] - a["mx"], b["my"] - a["my"]) * ((a["fov"] + b["fov"]) / 2) / K
    sp = d / dt
    zr = abs(math.log(b["fov"] / a["fov"])) / dt
    worst = max(worst, sp)
    flag = "  <-- OVER CAP" if sp > P["speedCapPxPerSec"] + 1 else ""
    print(f"  t={t0:6.1f}->{t1:6.1f}  {' ':10s} {dt:6.2f} {sp:7.1f} {zr:7.3f}{flag}")
print(json.dumps({"out": args.out, "duration": total,
                  "minutes": round(total / 60, 2), "frames": int(total * 24),
                  "stations": len(stations), "legs": [l["zone"] for l in legs],
                  "worstApparentPxPerSec": round(worst, 1),
                  "capPxPerSec": P["speedCapPxPerSec"],
                  "renderHours": round(total * 24 * 0.35 / 3600, 2)}, indent=1))
