#!/usr/bin/env python3
"""Refuse to call a render finished while the painting has holes in it.

One job. It does not judge composition, motion, or fill quality -- it answers
one question: is there a region of flat background colour ENCLOSED BY PAINTING?

WHY IT EXISTS. On 2026-08-24 a reel went in front of Ryan with two cream holes
of 200x277 and 140x91 px punched through the middle of the frame, present at
REST, and his entire reply was "trash". Both came from glue written the same
hour (a patch-offset error, and render-parallax pasting a patch without a mask
so its transparent border overwrote the plane's alpha). Neither was subtle and
neither was looked for, because the render had been checked by reading numbers
about invented ink rather than by asking whether the picture was intact.

A hole is not a taste question and does not need a human: it is flat fill with
painting all around it. That makes it exactly the thing a check should own.

WHAT IS NOT A HOLE. The plate is 1971x2704 fitted into a 16:9 frame, so the left
and right margins are legitimately empty. Only regions whose bounding box is
clear of both margins are counted, which is why --margin exists.

Per checks-start-in-observation this REPORTS and exits 0; --strict arms it.

usage:
  check-holes.py --frames DIR [--every N] [--min-px 2000] [--strict]
  check-holes.py --video FILE [--every N]   # N frames apart, throughout
"""
import argparse, glob, json, os, subprocess, sys, tempfile
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def bars_in(path):
    """A CREAM BAR is a frame-edge column that is entirely background. It is not
    a hole -- nothing encloses it -- but it is the same defect class and
    PLAN.md's benchmark bans it by name, so it is measured here rather than in a
    second tool nobody runs."""
    im = np.asarray(Image.open(path).convert("RGB")).astype(int)
    col = (np.abs(im - np.array([214, 203, 176])).max(2) < 2).all(0)
    if not (~col).any():
        return im.shape[1], im.shape[1]
    return int(np.argmax(~col)), int(np.argmax(~col[::-1]))


def holes_in(path, min_px, margin):
    im = np.asarray(Image.open(path).convert("RGB"))
    g = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(np.float32)
    # A fill region is PERFECTLY flat -- painted silk never is, because the
    # weave carries noise. 9px window, variance under half a level.
    mu = cv2.blur(g, (9, 9))
    var = cv2.blur(g * g, (9, 9)) - mu * mu
    flat = (var < 0.5).astype(np.uint8)
    H, W = flat.shape
    n, lab, stats, _ = cv2.connectedComponentsWithStats(flat, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < min_px:
            continue
        if x <= margin or x + w >= W - margin:
            continue                      # touches a legitimate letterbox margin
        out.append({"px": int(a), "box": [int(x), int(y), int(w), int(h)]})
    return sorted(out, key=lambda r: -r["px"]), H * W


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", help="a directory of rendered PNGs")
    ap.add_argument("--video", help="an mp4; sampled every --every frames throughout")
    ap.add_argument("--every", type=int, default=24,
                    help="check every Nth frame (a frames dir), or the equivalent "
                         "interval in a video. 24 = about one per second")
    ap.add_argument("--min-px", type=int, default=2000)
    ap.add_argument("--margin", type=int, default=310,
                    help="px of frame edge that may legitimately be empty")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    tmp = None
    if a.video:
        tmp = tempfile.mkdtemp()
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout.strip())
        # SAMPLE THE WHOLE THING, NOT THREE FRAMES. This path used to pull first,
        # middle and last, which cannot see a defect that appears partway through
        # a leg -- and that is the shape of the defects it exists to catch: a
        # patch offset only bites at certain camZ, so it opens and closes inside
        # a shot. On the 193s THE-RISE that sampled 3 of 4,631 frames, a 0.06%
        # look reported as a verdict. --every is seconds-between-samples here.
        step = max(0.25, float(a.every) / 24.0)
        stamps = [i * step for i in range(int(dur / step) + 1)]
        stamps[-1] = min(stamps[-1], max(0.0, dur - 0.1))
        # one decode pass, not one ffmpeg invocation per stamp
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.video,
                        "-vf", f"fps=1/{step}", f"{tmp}/s%05d.png"], check=True)
        files = sorted(glob.glob(f"{tmp}/s*.png"))
    else:
        files = sorted(glob.glob(f"{a.frames}/*.png"))[::max(1, a.every)]

    worst, report, worst_bar = 0, [], 0
    for f in files:
        L, R = bars_in(f)
        worst_bar = max(worst_bar, L, R)
        hs, total = holes_in(f, a.min_px, a.margin)
        if hs:
            worst = max(worst, hs[0]["px"])
            report.append({"frame": os.path.basename(f), "holes": len(hs),
                           "px": sum(h["px"] for h in hs),
                           "pct": round(100.0 * sum(h["px"] for h in hs) / total, 3),
                           "largest": hs[0]})

    print(json.dumps({
        "checked": len(files),
        "framesWithHoles": len(report),
        "largestHolePx": worst,
        "widestCreamBarPx": worst_bar,
        "verdict": ("HOLES" if report else
                    "CREAM BAR" if worst_bar > 8 else "intact"),
        "detail": report[:10],
    }, indent=1))
    if (report or worst_bar > 8) and a.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
