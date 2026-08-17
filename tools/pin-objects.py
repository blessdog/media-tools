#!/usr/bin/env python3
"""media-tools — pin-objects: no painted object may straddle two depths. One job.

Takes a plane stack and a set of object masks, and moves pixels BETWEEN the
existing planes until every object sits wholly on one of them. It does not
segment (`segment-regions`/`segment-points`), seal gaps (`complete-planes`),
paint behind occluders (`inpaint-planes`) or render.

WHY. A plane is a rigid card, so an object lying across two of them is magnified
at two rates by any camera move and visibly shears. Measured on wang-meng: a
servant's carried qin case sat 63/37 across two planes and was cut in half by a
0.45 dolly; a second servant's head sat 93/7 with a 1.42x shear and smeared.
Sealing gaps cannot fix this — both halves are legitimately claimed — and it is
invisible to an ink-threshold lint, because a pale robe is painted but is not
ink.

NAMES AND DEPTHS SURVIVE. It re-cuts the SAME planes rather than building new
ones, so plane names, depth order and any per-plane geometry keyed on those
names keep working. Only the boundaries move.

THE MODEL THIS IMPLIES. A hanging scroll states its space by overlap and
contour, not by perspective, so the natural unit is the OBJECT, not the plane.
Note that `segment-regions` was recorded on this project as a dead end — "finds
objects, never depth planes". That is the same behaviour, and here it is exactly
the capability wanted: ask for objects, then let the existing depth field vote on
where each one belongs. The failure was in the question, not the instrument.

THE GUARD. Forcing an object whose depth is genuinely ambiguous onto one plane is
the same mistake as reassigning a giant ink component: it flattens the stack.
Anything under --min-majority is left alone and named in the report, so an
ambiguous object shows up as a decision to make rather than as a silent merge.

usage:
  pin-objects.py --layers DIR --objects DIR --out DIR [--min-majority F]

  --layers DIR       the plane stack to re-cut (use a sealed one)
  --objects DIR      a segment-regions output: regions.json + masks/*.png
  --out DIR          the pinned stack
  --min-majority F   leave an object alone if no plane holds this fraction of it
                     (default 0.5)
  --min-area N       ignore object masks under N px (default 300)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
UNCLAIMED = -1


def main() -> int:
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--layers", required=True)
    ap.add_argument("--objects", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-majority", type=float, default=0.5)
    ap.add_argument("--min-area", type=int, default=300)
    a = ap.parse_args()

    lay, obj, out = Path(a.layers), Path(a.objects), Path(a.out)
    meta = json.loads((lay / "layers.json").read_text())
    W, H = meta["size"]
    src = Path(meta["image"])
    if not src.exists():
        print(f"layers.json names {src}, missing from here. Run from the repo "
              f"root.", file=sys.stderr)
        return 1
    (out / "layers").mkdir(parents=True, exist_ok=True)

    planes = sorted([p for p in meta["planeList"] if p.get("layer")],
                    key=lambda p: p["depth"])
    own = np.full((H, W), UNCLAIMED, np.int32)
    alphas = []
    for i, p in enumerate(planes):
        im = np.asarray(Image.open(lay / p["layer"]).convert("RGBA"))
        ox, oy = p["offset"]
        h, w = im.shape[:2]
        A = np.zeros((H, W), np.uint8)
        A[oy:oy + h, ox:ox + w] = im[..., 3]
        alphas.append(A)
        own[A > 128] = i

    rj = obj / "regions.json"
    if not rj.exists():
        print(f"no regions.json in {obj} — masks alone are not enough, their "
              f"OFFSETS live in the manifest", file=sys.stderr)
        return 1
    regions = json.loads(rj.read_text())["regionList"]
    rw, rh = json.loads(rj.read_text()).get("workSize", [W, H])
    if [rw, rh] != [W, H]:
        print(f"regions were cut at {rw}x{rh} but the stack is {W}x{H} — "
              f"refusing rather than scaling masks silently", file=sys.stderr)
        return 1

    moved, skipped, px_moved = [], [], 0
    for r in regions:
        mp = obj / r["mask"]
        # Masks are CROPPED tiles carrying their own offset, not full frames.
        # Resizing one to the frame lands it somewhere plausible and wrong.
        tile = np.asarray(Image.open(mp).convert("L")) > 127
        ox, oy = r["offset"]
        m = np.zeros((H, W), bool)
        th, tw = tile.shape
        m[oy:oy + th, ox:ox + tw] = tile
        n = int(m.sum())
        if n < a.min_area:
            continue
        d = own[m]
        d = d[d >= 0]
        if not len(d):
            continue
        counts = np.bincount(d, minlength=len(planes))
        maj = int(counts.argmax())
        frac = float(counts[maj]) / n
        if frac < a.min_majority:
            skipped.append((str(r["id"]), n, round(frac, 3),
                            planes[maj]["name"], int((counts > 0).sum())))
            continue
        if frac < 1.0:
            px_moved += n - int(counts[maj])
            moved.append((str(r["id"]), n, round(frac, 3), planes[maj]["name"],
                          int((counts > 0).sum())))
        own[m] = maj

    img = np.asarray(Image.open(src).convert("RGBA"))
    arr = np.array(img)
    new_list = []
    for i, p in enumerate(planes):
        m = own == i
        if not m.any():
            print(f"  {p['name']}: pinned away entirely, dropped", file=sys.stderr)
            continue
        ys, xs = np.nonzero(m)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        tile = arr[y0:y1, x0:x1].copy()
        tile[..., 3] = m[y0:y1, x0:x1].astype(np.uint8) * 255
        name = Path(p["layer"]).name
        Image.fromarray(tile).save(out / "layers" / name)
        q = dict(p)
        q["layer"] = f"layers/{name}"
        q["offset"] = [x0, y0]
        new_list.append(q)

    for nm, n, f, dest, k in sorted(moved, key=lambda r: -r[1])[:12]:
        print(f"  object {nm}  {n:6}px  was {f*100:5.1f}% on {dest:24} "
              f"(spanned {k} planes) -> pinned", file=sys.stderr)
    for nm, n, f, dest, k in skipped:
        print(f"  object {nm}  {n:6}px  AMBIGUOUS, best {f*100:.1f}% on {dest} "
              f"across {k} planes — LEFT ALONE, decide it by hand",
              file=sys.stderr)

    nm2 = dict(meta)
    nm2["planeList"] = new_list
    nm2["tool"] = "pin-objects"
    nm2["pinnedFrom"] = str(lay)
    nm2["objects"] = str(obj)
    nm2["feather"] = 0
    nm2["note"] = ("object boundaries now define plane boundaries; every object "
                   "sits wholly on one depth. Hard alpha on purpose — a feather "
                   "leaves a partial-transparency ring at every boundary that "
                   "inpaint-planes cannot fill and a dolly turns into an outline.")
    (out / "layers.json").write_text(json.dumps(nm2, indent=1))

    print(json.dumps({
        "tool": "pin-objects", "layers": str(lay), "objects": str(obj),
        "out": str(out), "planes": len(new_list),
        "objectsPinned": len(moved), "objectsAmbiguous": len(skipped),
        "pixelsMoved": px_moved,
        "ambiguous": [s[0] for s in skipped],
        "next": "probe-planes, then inpaint-planes, then render",
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
