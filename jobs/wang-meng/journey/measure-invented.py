#!/usr/bin/env python3
"""Measure how much of a dolly frame is INVENTED rather than painted, for one
fill stack, and draw the sheet that lets a human judge it.

One job. It does not choose a fill method, render the film, or decide whether
the trade is acceptable -- that verdict is Ryan's, with the picture in front of
him (a-deep-dolly-reveals-invented-material).

WHY THIS IS A FILE AND NOT A SESSION. The 2026-08-24 version of this ran as
three loose scripts driven by hand, the marker stack lived in a scratchpad, and
the render command was never written down -- so the measurement could not be
repeated against a second fill method, which is the only thing it is for. Worse,
sheet-invented.py carried "14.7%", "1.85%" and "12.6% vs 10.75%" as string
literals in its captions, so running it on a different stack would have drawn
the FIRST stack's numbers over the SECOND stack's picture. Every number on the
sheet now comes from the array it describes.

THE MEASUREMENT. invented = alpha(filled) AND NOT alpha(pinned), per plane,
aligned by each plane's own offset. That marker stack is rendered through the
identical camera, so a pixel is invented on screen iff the marker frame is white
there. Ink = darker than its own 31px local median by more than 12 levels.

THE NULL. Whole-frame ink density is unfair -- Ge Hong's flat robe and the empty
river drag it down. The honest control is a 36px collar of REAL painting
immediately around each invented region: same neighbourhood, same subject,
differing only in who painted it.

usage:
  measure-invented.py --zone z1 --filled layers-filled --label flux
                      [--path film/paths/ab-ge-corrected.json] [--frame 335]
"""
import argparse, json, os, shutil, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
J = "jobs/wang-meng"


def sh(cmd):
    print("  $ " + " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, cwd=REPO, check=True)


def build_marker(zone, filled_dir, out, pinned_dir="layers-pinned"):
    """WHITE = invented, BLACK = the painter's own ink. Alpha is copied through
    unchanged so the marker stack projects with exactly the same geometry."""
    Z = f"{REPO}/{J}/journey/{zone}"
    filled = json.load(open(f"{Z}/{filled_dir}/layers.json"))
    pinned = json.load(open(f"{Z}/{pinned_dir}/layers.json"))
    pin_by = {p["name"]: p for p in pinned["planeList"] if p.get("layer")}
    tot_inv = tot_paint = 0
    for p in filled["planeList"]:
        if not p.get("layer"):
            continue
        fim = Image.open(f"{Z}/{filled_dir}/{p['layer']}").convert("RGBA")
        fa = np.asarray(fim.split()[3]) > 0
        keep = np.zeros_like(fa)
        q = pin_by.get(p["name"])
        if q is not None:
            pa = np.asarray(Image.open(f"{Z}/{pinned_dir}/{q['layer']}")
                            .convert("RGBA").split()[3]) > 0
            dx = q["offset"][0] - p["offset"][0]
            dy = q["offset"][1] - p["offset"][1]
            h, w = pa.shape
            y0, x0 = max(0, dy), max(0, dx)
            y1 = min(fa.shape[0], dy + h)
            x1 = min(fa.shape[1], dx + w)
            if y1 > y0 and x1 > x0:
                keep[y0:y1, x0:x1] = pa[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
        inv = fa & ~keep
        tot_inv += int(inv.sum())
        tot_paint += int((fa & keep).sum())
        rgb = np.zeros(fa.shape + (3,), np.uint8)
        rgb[inv] = 255
        os.makedirs(os.path.dirname(f"{out}/{p['layer']}"), exist_ok=True)
        Image.fromarray(np.dstack([rgb, np.asarray(fim.split()[3])]),
                        "RGBA").save(f"{out}/{p['layer']}")
    json.dump(filled, open(f"{out}/layers.json", "w"), indent=1)
    return {"inventedPx": tot_inv, "paintedPx": tot_paint,
            "stackPctInvented": round(100.0 * tot_inv / (tot_inv + tot_paint), 2)}


def render(zone, layers, path, out, fill):
    sh(["python3", "tools/render-parallax.py",
        "--layers", layers, "--path", path, "--out", out,
        "--width", "1920", "--height", "1080", "--fps", "24",
        "--z-step", "0.30", "--plane-fit", "--no-base",
        "--geometry", f"{J}/journey/{zone}/geometry.json",
        "--fill", fill])


def label(img, text, size=26):
    im = Image.fromarray(img.copy())
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
    except OSError:
        f = ImageFont.load_default()
    d.rectangle([0, 0, d.textlength(text, font=f) + 24, size + 18], fill=(0, 0, 0))
    d.text((12, 8), text, font=f, fill=(255, 255, 255))
    return np.asarray(im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default="z1")
    ap.add_argument("--filled", default="layers-filled",
                    help="the fill stack to score, relative to journey/<zone>/")
    ap.add_argument("--label", required=True, help="what made this fill, e.g. flux / shiftmap")
    ap.add_argument("--path", default=f"{J}/film/paths/ab-ge-corrected.json")
    ap.add_argument("--frame", type=int, default=335, help="the deepest frame of the dolly")
    ap.add_argument("--pinned", default="layers-pinned",
                    help="the PRE-FILL stack this fill was made from")
    ap.add_argument("--work", default=None)
    a = ap.parse_args()

    work = a.work or f"{REPO}/{J}/journey/{a.zone}/measure-work/{a.label}"
    os.makedirs(work, exist_ok=True)
    marker_stack = f"{work}/marker-stack"
    shutil.rmtree(marker_stack, ignore_errors=True)
    os.makedirs(marker_stack)

    stack = build_marker(a.zone, a.filled, marker_stack, a.pinned)
    print(json.dumps(stack), file=sys.stderr)

    real_dir, mark_dir = f"{work}/f-real", f"{work}/f-marker"
    render(a.zone, f"{J}/journey/{a.zone}/{a.filled}", a.path, real_dir, "paper")
    # BLACK, so that background the camera has simply not covered can never be
    # counted as invented material.
    render(a.zone, os.path.relpath(marker_stack, REPO), a.path, mark_dir, "black")

    fn = f"{a.frame:05d}.png"
    real = np.asarray(Image.open(f"{real_dir}/{fn}").convert("RGB"))
    g = np.asarray(Image.open(f"{real_dir}/{fn}").convert("L")).astype(np.float32)
    inv = np.asarray(Image.open(f"{mark_dir}/{fn}").convert("L")) > 127
    H, W = inv.shape
    bg = cv2.medianBlur(g.astype(np.uint8), 31).astype(np.float32)
    ink = (bg - g) > 12

    k = np.ones((3, 3), np.uint8)
    m8 = inv.astype(np.uint8)
    edge = (cv2.dilate(m8, k, 1, None, 2) - cv2.erode(m8, k, 1, None, 1)) > 0
    ring = (cv2.dilate(m8, k, iterations=12) > 0) & ~inv

    m = {
        "label": a.label, "zone": a.zone, "filled": a.filled, "frame": a.frame,
        "stack": stack,
        "framePctInvented": round(100.0 * inv.mean(), 2),
        "framePctInventedInk": round(100.0 * (ink & inv).sum() / inv.size, 2),
        "framePctInventedBlank": round(100.0 * (inv & ~ink).sum() / inv.size, 2),
        "inkDensityInvented": round(100.0 * ink[inv].mean(), 2),
        "inkDensityAdjacentPainted": round(100.0 * ink[ring].mean(), 2),
        "ringPx": int(ring.sum()),
    }
    m["overInkPct"] = round(100.0 * (m["inkDensityInvented"]
                                     / m["inkDensityAdjacentPainted"] - 1.0), 1)

    # THE FOUR WORST REGIONS, ranked by invented INK, not by area -- a large
    # blank fill is not what anyone is worried about.
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m8, 8)
    inked = ink & inv
    score = sorted(((int(np.count_nonzero(inked & (lab == i))), i)
                    for i in range(1, n) if stats[i, 4] > 3000), reverse=True)
    TILE, chosen = 470, []
    for s, i in score:
        cx, cy = cent[i]
        x0 = int(np.clip(cx - TILE // 2, 0, W - TILE))
        y0 = int(np.clip(cy - TILE // 2, 0, H - TILE))
        if any(abs(x0 - b) < TILE * 0.8 and abs(y0 - c) < TILE * 0.8
               for b, c, _ in chosen):
            continue
        chosen.append((x0, y0, s))
        if len(chosen) == 4:
            break

    tiles = []
    for x0, y0, s in chosen:
        t = real[y0:y0 + TILE, x0:x0 + TILE].copy()
        t[edge[y0:y0 + TILE, x0:x0 + TILE]] = (255, 0, 200)
        tiles.append(label(t, f"{s:,} px of INVENTED INK — 1:1", 22))

    out = real.copy()
    out[edge] = (255, 0, 200)
    top = label(out, f"{a.label.upper()} FILL · deepest dolly · outlines ring INVENTED material: "
                     f"{m['framePctInvented']}% of frame, of which "
                     f"{m['framePctInventedInk']}% carries ink", 27)
    row = np.hstack(tiles) if tiles else np.full((44, W, 3), 20, np.uint8)
    if row.shape[1] < top.shape[1]:
        row = np.hstack([row, np.full((row.shape[0], top.shape[1] - row.shape[1], 3), 20, np.uint8)])
    row = row[:, :top.shape[1]]
    cap = label(np.full((44, top.shape[1], 3), 20, np.uint8),
                f"the worst regions at 1:1 — ink density inside {m['inkDensityInvented']}% "
                f"vs {m['inkDensityAdjacentPainted']}% in the painting right beside it "
                f"({m['overInkPct']:+}%)", 24)
    sheet = f"{REPO}/{J}/evidence/2026-08-24-invented-{a.label}.png"
    Image.fromarray(np.vstack([top, cap, row])).save(sheet)

    clip = f"{REPO}/{J}/evidence/2026-08-24-dolly-{a.label}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24",
                    "-i", f"{real_dir}/%05d.png", "-c:v", "libx264", "-crf", "16",
                    "-pix_fmt", "yuv420p", clip], check=True)

    m["sheet"], m["clip"] = os.path.relpath(sheet, REPO), os.path.relpath(clip, REPO)
    json.dump(m, open(f"{REPO}/{J}/evidence/2026-08-24-invented-{a.label}.json", "w"), indent=1)
    print(json.dumps(m, indent=1))


if __name__ == "__main__":
    main()
