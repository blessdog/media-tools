#!/usr/bin/env python3
"""Put two fill methods on the SAME crop, at 1:1, so the difference is a
judgement a human can make rather than two numbers.

One job. measure-invented.py scores one stack and picks ITS OWN worst regions,
which means two runs crop different places and cannot be compared by eye. This
takes the worst regions of the UNION and cuts both frames at identical
coordinates.

usage:
  pair-invented.py --zone z1 --a flux --b shiftmap [--frame 335]
"""
import argparse, json, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
J = "jobs/wang-meng"


def load(zone, tag, frame):
    d = f"{REPO}/{J}/journey/{zone}/measure-work/{tag}"
    fn = f"{frame:05d}.png"
    real = np.asarray(Image.open(f"{d}/f-real/{fn}").convert("RGB"))
    g = np.asarray(Image.open(f"{d}/f-real/{fn}").convert("L")).astype(np.float32)
    inv = np.asarray(Image.open(f"{d}/f-marker/{fn}").convert("L")) > 127
    bg = cv2.medianBlur(g.astype(np.uint8), 31).astype(np.float32)
    return real, inv, (bg - g) > 12


def label(img, text, size=24):
    im = Image.fromarray(img.copy())
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
    except OSError:
        f = ImageFont.load_default()
    d.rectangle([0, 0, d.textlength(text, font=f) + 24, size + 16], fill=(0, 0, 0))
    d.text((12, 6), text, font=f, fill=(255, 255, 255))
    return np.asarray(im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default="z1")
    ap.add_argument("--a", default="flux")
    ap.add_argument("--b", default="shiftmap")
    ap.add_argument("--frame", type=int, default=335)
    ap.add_argument("--tiles", type=int, default=3)
    a = ap.parse_args()

    ra, ia, ka = load(a.zone, a.a, a.frame)
    rb, ib, kb = load(a.zone, a.b, a.frame)
    H, W = ia.shape
    k = np.ones((3, 3), np.uint8)

    def outline(m):
        m8 = m.astype(np.uint8)
        return (cv2.dilate(m8, k, iterations=2) - cv2.erode(m8, k, iterations=1)) > 0

    ea, eb = outline(ia), outline(ib)
    # Rank on the UNION so a region either method invented is a candidate, and
    # score by invented INK in EITHER -- the worst case for the pair.
    union = (ia | ib).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(union, 8)
    bad = (ka & ia) | (kb & ib)
    score = sorted(((int(np.count_nonzero(bad & (lab == i))), i)
                    for i in range(1, n) if stats[i, 4] > 3000), reverse=True)

    TILE, chosen = 470, []
    for s, i in score:
        cx, cy = cent[i]
        x0 = int(np.clip(cx - TILE // 2, 0, W - TILE))
        y0 = int(np.clip(cy - TILE // 2, 0, H - TILE))
        if any(abs(x0 - p) < TILE * 0.8 and abs(y0 - q) < TILE * 0.8 for p, q in chosen):
            continue
        chosen.append((x0, y0))
        if len(chosen) == a.tiles:
            break

    def strip(real, edge, ink, inv, tag):
        tiles = []
        for x0, y0 in chosen:
            t = real[y0:y0 + TILE, x0:x0 + TILE].copy()
            t[edge[y0:y0 + TILE, x0:x0 + TILE]] = (255, 0, 200)
            sub_i = inv[y0:y0 + TILE, x0:x0 + TILE]
            sub_k = ink[y0:y0 + TILE, x0:x0 + TILE]
            dens = 100.0 * sub_k[sub_i].mean() if sub_i.any() else 0.0
            tiles.append(label(t, f"{tag} — ink in fill {dens:.1f}%", 22))
        return np.hstack(tiles)

    A = strip(ra, ea, ka, ia, a.a.upper())
    B = strip(rb, eb, kb, ib, a.b.upper())
    ma = json.load(open(f"{REPO}/{J}/evidence/2026-08-24-invented-{a.a}.json"))
    mb = json.load(open(f"{REPO}/{J}/evidence/2026-08-24-invented-{a.b}.json"))

    head = label(np.full((52, A.shape[1], 3), 20, np.uint8),
                 "SAME CROPS, SAME CAMERA, DEEPEST DOLLY — magenta rings what the fill invented", 26)
    capA = label(np.full((46, A.shape[1], 3), 20, np.uint8),
                 f"{a.a.upper()}: invented ink {ma['framePctInventedInk']}% of frame · "
                 f"density {ma['inkDensityInvented']}% vs {ma['inkDensityAdjacentPainted']}% beside it "
                 f"({ma['overInkPct']:+}%)", 23)
    capB = label(np.full((46, A.shape[1], 3), 20, np.uint8),
                 f"{a.b.upper()}: invented ink {mb['framePctInventedInk']}% of frame · "
                 f"density {mb['inkDensityInvented']}% vs {mb['inkDensityAdjacentPainted']}% beside it "
                 f"({mb['overInkPct']:+}%)", 23)

    out = f"{REPO}/{J}/evidence/2026-08-24-fill-AB-{a.a}-vs-{a.b}.png"
    Image.fromarray(np.vstack([head, capA, A, capB, B])).save(out)
    print(json.dumps({"sheet": os.path.relpath(out, REPO),
                      "crops": [[int(x), int(y)] for x, y in chosen]}))


if __name__ == "__main__":
    main()
