#!/usr/bin/env python3
"""Turn catalogued leaf masses into executable foliage regions.

    catalogue-to-polys.py --tiles catalogue/tiles-z1lower/tiles.json \
                          --catalogue "catalogue/z1lower-t*.json" [--apply]

One job. It converts labels into polygons. It does not cut, animate, or render,
and it does not decide what a leaf is -- a person already did that.

WHY. Coverage was 8 hand-authored foliage regions for the whole scroll, and
measured on z1 only 6.9% of leaf ink ever moved. Ryan, 2026-08-24: "it appears
that only ~10% or less of foliage is actually animated at all... we can do
better." The catalogue already holds every leaf mass as a labelled box; the only
reason they were not regions is that nobody converted them.

THE BOXES ARE A FENCE, NOT A MASK. Several are flagged in their own notes as
SEARCH REGIONS -- leaves veiled in front of ochre boulders, where half the box is
rock. That is safe here only because classes.foliage.leafMask gates the cut with
the SAM-refined mask; without it these polygons would animate stone.

DEDUP MATTERS. The tiles overlap (t002/t003 and t006/t007 share 77% of their
area), so the same tree is catalogued twice under different ids. Boxes whose
master-px IoU exceeds --iou are merged, or the same canopy gets two sets of cards
hinging against each other.
"""
import argparse, glob, json, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--catalogue", required=True, help="glob of tNNN.json label files")
    ap.add_argument("--prefix", default="cat")
    ap.add_argument("--iou", type=float, default=0.45)
    ap.add_argument("--min-master-px", type=int, default=90,
                    help="skip a box smaller than this on its short side; below "
                         "~40px of ink a hinge reads as jitter (figure-motion)")
    ap.add_argument("--apply", action="store_true", help="write into living-polys.json")
    a = ap.parse_args()

    tiles = {t["file"]: t for t in json.load(open(a.tiles))["tiles"]}
    found = []
    for f in sorted(glob.glob(a.catalogue)):
        d = json.load(open(f))
        t = tiles.get(d["tile"])
        if t is None:
            raise SystemExit(f"{f}: tile {d['tile']!r} is not in {a.tiles}")
        sx0, sy0, sx1, sy1 = t["sourceBox"]
        tw, th = sx1 - sx0, sy1 - sy0
        for o in d["objects"]:
            if o.get("kind") != "tree" or not o.get("leavesVisible"):
                continue
            bx = o["box"]
            m = [sx0 + bx[0] * tw, sy0 + bx[1] * th, sx0 + bx[2] * tw, sy0 + bx[3] * th]
            if min(m[2] - m[0], m[3] - m[1]) < a.min_master_px:
                continue
            found.append({"id": f"{a.prefix}-{o['id']}", "box": [int(v) for v in m],
                          "src": os.path.basename(f), "name": o.get("name", "")})

    # TWO MERGE RULES, because one is not enough. Overlapping tiles catalogue the
    # same tree twice and the two agents do not draw the identical box, so plain
    # IoU misses them: measured on z1lower, 6 objects survived IoU 0.45 as
    # duplicate NAMES. An object with the same id in two tiles is the same
    # object -- any overlap at all is proof enough.
    kept = []
    for r in sorted(found, key=lambda r: -((r["box"][2] - r["box"][0]) * (r["box"][3] - r["box"][1]))):
        dup = False
        for k in kept:
            ov = iou(r["box"], k["box"])
            if ov > a.iou or (r["id"] == k["id"] and ov > 0.05):
                dup = True
                break
        if dup:
            continue
        kept.append(r)
    # Whatever still shares an id after that is a genuine name collision between
    # different objects; disambiguate rather than silently dropping one.
    seen = {}
    for r in kept:
        n = seen.get(r["id"], 0)
        seen[r["id"]] = n + 1
        if n:
            r["id"] = f"{r['id']}-{r['src'].split('-')[-1][:-5]}"

    polys = [{"id": r["id"], "class": "foliage",
              "points": [[r["box"][0], r["box"][1]], [r["box"][2], r["box"][1]],
                         [r["box"][2], r["box"][3]], [r["box"][0], r["box"][3]]],
              "note": f"from the catalogue ({r['src']}): {r['name']}. The box is a "
                      f"FENCE; classes.foliage.leafMask gates which ink inside it moves."}
             for r in kept]

    print(json.dumps({"catalogued": len(found), "afterDedup": len(kept),
                      "dropped": len(found) - len(kept)}, indent=1))
    for p in polys:
        print(f"  {p['id']}")

    if a.apply:
        lp = f"{REPO}/jobs/wang-meng/living/living-polys.json"
        d = json.load(open(lp))
        have = {p["id"] for p in d["polys"]}
        add = [p for p in polys if p["id"] not in have]
        d["polys"].extend(add)
        json.dump(d, open(lp, "w"), indent=1, ensure_ascii=False)
        print(f"\nadded {len(add)} polys to living-polys.json (now {len(d['polys'])})")


if __name__ == "__main__":
    main()
