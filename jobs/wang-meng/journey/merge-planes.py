#!/usr/bin/env python3
"""Collapse a fine plane stack into a COARSE one by merging adjacent depths.

One job. It does not cut planes (segment-points), fill them (inpaint-planes) or
render them (render-parallax).

WHY. Every plane boundary is a disocclusion band, and every band is somewhere a
fill has to invent material. z1 has 12 planes and 33.3% of its stack is
synthesised. Merging planes that sit at adjacent depths removes their shared
boundaries outright -- the ink that was on two cards is now on one card, and
nothing has to be painted between them because nothing can slide apart.

WHAT THIS IS NOT. It is not the 3-plane stack that plan-planes-at-shot-scale
measured as flat. That one was planned at SCROLL scale and its depths were
crammed into sigma 0.098. This keeps the full depth SPAN of the fine stack and
only reduces the COUNT, so the near/far separation survives -- which is the
thing that actually produces parallax.

Groups are given as depth ranges, nearest LAST, e.g.
  --groups "9-10,11-13,14-16,17-18"

Each group's layers are composited in the fine stack's own order (farther under
nearer, which is the order planeList is already in) onto one canvas, and the
merged plane takes the MEAN depth of its members.

usage:
  merge-planes.py --layers DIR --out DIR --groups "9-10,11-13,14-16,17-18"
"""
import argparse, json, os, shutil
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def parse_groups(spec):
    out = []
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        out.append((int(lo), int(hi or lo)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--groups", required=True,
                    help='depth ranges nearest last, e.g. "9-10,11-13,14-16,17-18"')
    a = ap.parse_args()

    meta = json.load(open(f"{a.layers}/layers.json"))
    W, H = meta["size"]
    planes = [p for p in meta["planeList"] if p.get("layer")]
    groups = parse_groups(a.groups)

    shutil.rmtree(a.out, ignore_errors=True)
    os.makedirs(f"{a.out}/layers", exist_ok=True)

    covered, new_list = set(), []
    for gi, (lo, hi) in enumerate(groups, 1):
        members = [p for p in planes if lo <= p["depth"] <= hi]
        if not members:
            print(f"  group {lo}-{hi}: EMPTY, skipped")
            continue
        canvas = np.zeros((H, W, 4), np.uint8)
        for p in members:               # planeList order = far under near
            covered.add(p["name"])
            im = np.asarray(Image.open(f"{a.layers}/{p['layer']}").convert("RGBA"))
            ox, oy = p["offset"]
            h, w = im.shape[:2]
            y0, x0 = max(0, oy), max(0, ox)
            y1, x1 = min(H, oy + h), min(W, ox + w)
            if y1 <= y0 or x1 <= x0:
                continue
            src = im[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
            dst = canvas[y0:y1, x0:x1]
            m = src[..., 3] > 0
            dst[m] = src[m]             # nearer member wins where they overlap

        ys, xs = np.nonzero(canvas[..., 3])
        if ys.size == 0:
            continue
        bx0, bx1, by0, by1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        crop = canvas[by0:by1, bx0:bx1]
        name = "-".join(sorted({m["name"].split("-")[0] for m in members}))[:40] or f"g{gi}"
        name = f"merged-{gi}-{name}"
        rel = f"layers/{900 + gi}-{name}.png"
        Image.fromarray(crop, "RGBA").save(f"{a.out}/{rel}")
        new_list.append({
            "n": gi, "id": 1000 + gi, "name": name,
            "depth": round(sum(m["depth"] for m in members) / len(members), 2),
            "members": [m["name"] for m in members],
            "memberDepths": [m["depth"] for m in members],
            "bbox": [bx0, by0, bx1, by1],
            "offset": [bx0, by0],
            "areaFinal": int((crop[..., 3] > 0).sum()),
            "layer": rel,
        })
        print(f"  {name:44s} depth {new_list[-1]['depth']:5.2f}  "
              f"{len(members)} planes  {new_list[-1]['areaFinal']:8d} px")

    missed = [p["name"] for p in planes if p["name"] not in covered]
    if missed:
        raise SystemExit(f"REFUSING: these planes fell in no group: {missed}")

    out = dict(meta)
    out["planeList"] = new_list
    out["planes"] = len(new_list)
    out["mergedFrom"] = a.layers
    out["groups"] = a.groups
    out["tool"] = "merge-planes"
    json.dump(out, open(f"{a.out}/layers.json", "w"), indent=1)

    ds = [p["depth"] for p in new_list]
    fine = [p["depth"] for p in planes]
    print(json.dumps({
        "planesBefore": len(planes), "planesAfter": len(new_list),
        "depthSpanBefore": [min(fine), max(fine)], "depthSpanAfter": [min(ds), max(ds)],
        "depthSigmaBefore": round(float(np.std(fine)), 3),
        "depthSigmaAfter": round(float(np.std(ds)), 3),
    }, indent=1))


if __name__ == "__main__":
    main()
