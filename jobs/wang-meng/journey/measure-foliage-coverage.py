#!/usr/bin/env python3
"""How much of a zone's LEAF is actually animated?

One job. It does not cut cards, animate anything, or judge the motion -- it
answers one number: of the leaf-coloured painting on this plate, what fraction
lies under an animated foliage card?

WHY. Ryan, 2026-08-24: "it appears that only ~10% or less of foliage is actually
animated at all... you are still applying changes to only a small portion of the
canvas." Coverage was never measured, only felt, and a coverage claim that is
felt is exactly the kind that survives for weeks.

WHAT COUNTS AS LEAF. The same rule the cutter uses, so the two cannot disagree
-- leaf-is-colour-rock-is-graphite. Colour lives in the mid-tone WASH under the
strokes, never in the strokes: green = Lab a at least --leaf-da below the silk's
median a; orange = hue <= 28 deg at saturation >= 0.34; both restricted to
mid-tone pixels so neither bare silk nor black stroke can qualify.

WHAT COUNTS AS LEAF, PRECISELY. The wash mask alone is not the answer: dilated,
it covers 60% of the z1 plate, because a wash is broad and the strokes on it are
not. The painted LEAF is ink ON that wash -- ink being a pixel darker than its
own 31px local median by more than 12 levels, the same definition
measure-invented.py uses. That is the denominator.

WHAT COUNTS AS ANIMATED. Not the patch rectangle -- that over-states, since a
patch is a crop and most of a crop holds still. A pixel is animated if it
ACTUALLY CHANGES across the cycle's drawings. That is exact, needs no
assumptions about how the cards were cut, and cannot flatter the result.

usage:
  measure-foliage-coverage.py --zone z1 [--living living/living-z1.json]
"""
import argparse, json, os, glob
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
J = "jobs/wang-meng"


def leaf_mask(rgb, leaf_da=2.5, ink_offset=0.06, leaf_grow=5):
    v = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    ground = float(np.median(v))
    mid = (v >= ground - ink_offset) & (v < ground + 0.15)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    hsvf = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hue, sat = hsvf[..., 0] * 2, hsvf[..., 1] / 255
    silk_a = float(np.median(lab[..., 1][mid])) if mid.any() else 128.0
    green = (lab[..., 1] <= silk_a - leaf_da) & mid
    orange = (hue <= 28) & (sat >= 0.34) & mid
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * leaf_grow + 1,) * 2)
    return cv2.dilate((green | orange).astype(np.uint8), k) > 0, silk_a, int(green.sum()), int(orange.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", default="z1")
    ap.add_argument("--living", default=None)
    ap.add_argument("--leaf-da", type=float, default=2.5)
    a = ap.parse_args()

    Z = f"{REPO}/{J}/journey/{a.zone}"
    plate = np.asarray(Image.open(f"{Z}/plate.png").convert("RGB"))
    H, W = plate.shape[:2]
    leaf, silk_a, g, o = leaf_mask(plate, a.leaf_da)

    living_path = a.living or f"{REPO}/{J}/living/living-{a.zone}.json"
    living = json.load(open(living_path))
    fine = {p["name"]: p for p in
            json.load(open(f"{Z}/layers-filled/layers.json"))["planeList"] if p.get("layer")}

    v = cv2.cvtColor(plate, cv2.COLOR_RGB2GRAY)
    bg = cv2.medianBlur(v, 31).astype(np.float32)
    ink = (bg - v.astype(np.float32)) > 12
    leaf = leaf & ink                       # painted leaf = ink on leaf wash

    animated = np.zeros((H, W), bool)
    regions = {}
    for pname, entry in living.items():
        P = fine.get(pname)
        if P is None:
            continue
        ox, oy = P["offset"]
        for q in entry.get("patches", []):
            rid = os.path.basename(q["dir"]).split("__")[-1]
            cyc = f"{REPO}/{J}/living/cycles/{rid}/cycle.json"
            klass = None
            if os.path.exists(cyc):
                klass = json.load(open(cyc)).get("tool")
            d0 = sorted(glob.glob(f"{q['dir']}/*.png"))
            if len(d0) < 2:
                continue
            # WHICH PIXELS ACTUALLY MOVE. Compare every drawing against the
            # first; a pixel that never differs by more than 6 levels is still,
            # whatever rectangle it sits inside.
            base = np.asarray(Image.open(d0[0]).convert("RGB")).astype(np.int16)
            moves = np.zeros(base.shape[:2], bool)
            for f in d0[1:]:
                cur = np.asarray(Image.open(f).convert("RGB")).astype(np.int16)
                if cur.shape != base.shape:
                    continue
                moves |= np.abs(cur - base).max(2) > 6
            h, w = moves.shape
            x0, y0 = ox + q["box"][0], oy + q["box"][1]
            sx0, sy0 = max(0, x0), max(0, y0)
            sx1, sy1 = min(W, x0 + w), min(H, y0 + h)
            if sx1 <= sx0 or sy1 <= sy0:
                continue
            sub = moves[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0]
            regions.setdefault(rid, {"px": 0, "tool": klass})
            cell = np.zeros((H, W), bool)
            cell[sy0:sy1, sx0:sx1] = sub
            animated |= cell
            regions[rid]["px"] += int((cell & leaf).sum())

    tot = int(leaf.sum())
    cov = int((leaf & animated).sum())
    print(json.dumps({
        "zone": a.zone, "plate": [W, H],
        "silkA": round(silk_a, 1), "greenWashPx": g, "orangeWashPx": o,
        "leafInkPx": tot, "leafInkPctOfPlate": round(100.0 * tot / (W * H), 2),
        "movingPx": int(animated.sum()),
        "leafInkThatMovesPx": cov,
        "foliageCoveragePct": round(100.0 * cov / tot, 1) if tot else 0.0,
        "regions": {k: v["px"] for k, v in sorted(regions.items(), key=lambda r: -r[1]["px"])},
    }, indent=1))


if __name__ == "__main__":
    main()
