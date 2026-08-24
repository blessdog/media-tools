#!/usr/bin/env python3
"""Author the subtle focus shots, with a fov that CANNOT show a cream bar.

One job. It writes paths; it does not render, join, or judge them.

THE BAR IS ARITHMETIC, NOT TASTE. render-parallax's scale equals fov exactly
(measured 2026-08-24: a stated 0.96 produced 0.9607 screen px per plate px), so
the visible window is width/fov plate px wide. At fov ~1 that is the WHOLE plate
width, so any focus point off centre runs off the edge and the frame fills with
background. Measured on the first cut: 400 px of cream on the left of
focus-water, 624 px on the right of focus-trees -- a fifth to a third of the
frame, against PLAN.md's benchmark of "no black frame or cream bar".

So the fov floor is derived from the focus point:

    fov >= width  / (2 * min(cx, W - cx))        # horizontal
    fov >= height / (2 * min(cy, H - cy))        # vertical

taking the larger, plus a safety margin. A subject near the plate edge therefore
FORCES a tight shot -- which is honest: there is no wider framing of it that
contains only painting.

AND A CEILING, because magnification is not free. The plate is the master
downsampled by k (2.34), so a fov above k means the frame is being upscaled past
the painting's own resolution. Any shot that needs more than that is refused
rather than rendered soft.

usage:
  author-shots.py [--duration 9] [--z 0.11]
"""
import argparse, json, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
J = "jobs/wang-meng"

# Focus points are PLANE CENTRES in normalised plate coordinates, chosen for a
# depth sandwich -- something in front and something behind -- and each carries
# living patches, because the camera moves toward motion.
SHOTS = [
    dict(id="focus-water", x=0.282, y=0.834,
         note="the water at the foot of the scroll (depth 16); foreground rock at 18 in front"),
    dict(id="focus-ge", x=0.338, y=0.477,
         note="Ge Hong on the trestle bridge (depth 14); knoll and bank-path in front, cliff walls at 9 behind"),
    dict(id="focus-slope", x=0.621, y=0.515,
         note="the right hillside and its trees (depth 15); the great-trees knoll at 17 in front"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=9.0)
    ap.add_argument("--z", type=float, default=0.11,
                    help="peak camZ; 0.11 is light-parallax-is-011-and-continuous")
    ap.add_argument("--safety", type=float, default=1.08)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    a = ap.parse_args()

    plate = json.load(open(f"{REPO}/{J}/journey/z1/layers-pinned/layers.json"))
    W, H = plate["size"]
    k = json.load(open(f"{REPO}/{J}/journey/world.json"))["k"]

    for s in SHOTS:
        cx, cy = s["x"] * W, s["y"] * H
        need = max(a.width / (2 * min(cx, W - cx)), a.height / (2 * min(cy, H - cy)))
        fov0 = round(need * a.safety, 4)
        # the fov creeps 2% per key; the LAST key is the tightest, so it is the
        # one that has to clear the resolution ceiling.
        fov_last = fov0 * 1.04
        if fov_last > k:
            raise SystemExit(
                f"REFUSING {s['id']}: needs fov {fov_last:.2f} to avoid a cream bar, "
                f"but the plate is the master downsampled {k}x, so anything above "
                f"{k} is upscaled past the painting's own resolution. Move the "
                f"focus point inward or cut this shot.")

        keys = []
        for i, (t, f) in enumerate([(0.0, 0.0), (a.duration / 2, 0.55), (a.duration, 1.0)]):
            keys.append({
                "t": round(t, 2),
                # a HOLD: the subject stays put and depth does the work
                "x": round(s["x"] + 0.004 * (i - 1), 4),
                "y": round(s["y"] - 0.003 * (i - 1), 4),
                "fov": round(fov0 * (1 + 0.02 * i), 4),
                # z ramped CONTINUOUSLY, never spiked, or it reads as a zoom
                "z": round(a.z * f, 4),
                # a dead axis is a defect check-camera-plan flags; 0.08 is the
                # ceiling light-parallax-is-011-and-continuous sets
                "ry": round(0.06 * f, 4),
                "rx": round(-0.03 * f, 4),
            })
        p = {"fps": 24, "duration": a.duration,
             "_note": f"SUBTLE SHOT. Focus: {s['note']}. fov floor {need:.3f} "
                      f"derived from the focus point so no cream bar is possible; "
                      f"z ramps 0->{a.z} continuously; keys are POSES "
                      f"{a.duration/2:.1f}s apart.",
             "keys": keys}
        fn = f"{REPO}/{J}/film/paths/shot-{s['id']}.json"
        json.dump(p, open(fn, "w"), indent=1)
        print(f"  {s['id']:14s} fov floor {need:6.3f} -> {fov0:6.3f}..{fov_last:6.3f} "
              f"(ceiling {k})   {os.path.relpath(fn, REPO)}")


if __name__ == "__main__":
    main()
