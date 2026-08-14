#!/usr/bin/env python3
"""media-tools — segment-regions: image → non-overlapping regions. One job.

It proposes WHERE the boundaries are. It does not decide what is in front of
what — that is a depth ordering, a human judgement, and a different tool.

WHY SEGMENTATION AND NOT DEPTH (2026-08-13, proven the hard way). Monocular
depth estimation fails completely on Chinese ink painting: Depth-Anything-V2
Large on Wang Meng's 葛稚川移居圖 returned a top-to-bottom ramp with one tree cut
out of it, at 1536px AND at native resolution on a square crop. The cause is not
settings, it is domain — depth nets read linear perspective, defocus and
photographic haze, and a Yuan hanging scroll has none of them.

What it DOES have is an explicit ink contour at every single overlap. The
painter stated the occlusions rather than implying them. Segmentation keys on
exactly that, which is why it is the right instrument here and depth was not.

THE NESTING RULE. SAM returns overlapping masks at several scales — a cliff, and
the tree standing on it, and one branch of that tree. Painting them
LARGEST FIRST means every pixel ends up owned by the SMALLEST region containing
it, which in a landscape is almost always the nearer object. That turns a pile
of overlapping proposals into a clean partition, and it biases the partition the
way a depth ordering wants.

Region 0 is whatever nothing claimed.

usage:
  segment-regions.py --image IN --out DIR [flags]

  --image PATH     the picture
  --out DIR        regions.json, masks/NNN.png, overlay.png land here
  --max-side N     work resolution (default 1600). SAM runs at 1024 internally;
                   past ~2000 you get leaves and roof tiles, not depth planes.
  --tile N         tile the image into NxN native-pixel windows instead of
                   downscaling the whole thing. REQUIRED for anything much
                   bigger than ~2000px: SAM resizes its input to 1024 no matter
                   what, so a 6586x15923 scroll fed whole is seen as a 424x1024
                   thumbnail and comes back with mush. Tiling is the only way
                   to spend the resolution you have.
  --tile-overlap F fraction of overlap between tiles (default 0.4). Masks that
                   touch a tile's inner edge are DISCARDED, because a clipped
                   region is a lie about where the object ends — with 40%
                   overlap the same object is interior to a neighbouring tile
                   and gets kept there, whole. Raise it if objects are being
                   lost; it costs tiles quadratically.
  --min-area F     drop regions smaller than this fraction of the frame
                   (default 0.002). Raise it for coarser planes.
  --max-regions N  keep at most this many, largest first (default 60)
  --model ID       default facebook/sam-vit-huge
  --points N       sampling density per side (default 24; more = more regions)
  --device NAME    mps (default on Apple Silicon) | cpu

JSON on stdout. Progress on stderr.

example:
  .venv/bin/python tools/segment-regions.py \\
    --image corpus/grabs/wang-meng.png --out jobs/wang-meng/regions
"""

import argparse
import json
import sys
import time
from pathlib import Path


def main() -> int:
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-side", type=int, default=1600)
    ap.add_argument("--tile", type=int, default=0)
    ap.add_argument("--tile-overlap", type=float, default=0.4)
    ap.add_argument("--min-area", type=float, default=0.002)
    ap.add_argument("--max-regions", type=int, default=60)
    ap.add_argument("--model", default="facebook/sam-vit-huge")
    ap.add_argument("--points", type=int, default=24)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    src = Path(args.image)
    if not src.exists():
        print(f"no such image: {src}", file=sys.stderr)
        return 1
    out = Path(args.out)
    (out / "masks").mkdir(parents=True, exist_ok=True)

    import numpy as np
    import torch
    from PIL import Image, ImageDraw
    from transformers import pipeline

    Image.MAX_IMAGE_PIXELS = None
    device = args.device or ("mps" if torch.backends.mps.is_available() else "cpu")

    full = Image.open(src).convert("RGB")
    w0, h0 = full.size

    if args.tile:
        # Work at NATIVE resolution, in windows. No global downscale.
        img, w, h = full, w0, h0
    else:
        img = full
        if max(img.size) > args.max_side:
            s = args.max_side / max(img.size)
            img = img.resize((max(1, round(w0 * s)), max(1, round(h0 * s))), Image.Resampling.LANCZOS)
        w, h = img.size
    print(f"  {src.name}  {w0}x{h0} → {w}x{h}  {args.model}  device={device}", file=sys.stderr)

    t0 = time.time()
    gen = pipeline("mask-generation", model=args.model, device=device)
    t_load = time.time() - t0

    frame = w * h
    t0 = time.time()

    if args.tile:
        T = args.tile
        step = max(1, int(T * (1.0 - args.tile_overlap)))
        xs = list(range(0, max(1, w - T + step), step))
        ys = list(range(0, max(1, h - T + step), step))
        print(f"  tiling {T}px step {step}: {len(xs)}x{len(ys)} = {len(xs)*len(ys)} tiles", file=sys.stderr)
        masks, raw_count, done = [], 0, 0
        for ty in ys:
            for tx in xs:
                x1, y1 = min(tx, max(0, w - T)), min(ty, max(0, h - T))
                x2, y2 = min(x1 + T, w), min(y1 + T, h)
                crop = img.crop((x1, y1, x2, y2))
                r = gen(crop, points_per_batch=32, points_per_crop=args.points)
                raw_count += len(r["masks"])
                ch, cw = y2 - y1, x2 - x1
                for m in r["masks"]:
                    a = np.asarray(m, dtype=bool)
                    if a.sum() < args.min_area * frame:
                        continue
                    # A mask touching an INNER tile edge is clipped, and a
                    # clipped region misstates where the object ends. Drop it —
                    # the overlap means a neighbouring tile holds it whole.
                    touches = (
                        (a[0, :].any() and y1 > 0) or (a[ch - 1, :].any() and y2 < h)
                        or (a[:, 0].any() and x1 > 0) or (a[:, cw - 1].any() and x2 < w)
                    )
                    if touches:
                        continue
                    # Store by bounding box, NEVER as a full-frame array: one
                    # bool mask at 6586x15923 is 105MB, and there are hundreds.
                    ys_, xs_ = np.nonzero(a)
                    by1, by2 = int(ys_.min()), int(ys_.max()) + 1
                    bx1, bx2 = int(xs_.min()), int(xs_.max()) + 1
                    masks.append((y1 + by1, x1 + bx1, a[by1:by2, bx1:bx2].copy()))
                done += 1
                if done % 5 == 0 or done == len(xs) * len(ys):
                    print(f"    tile {done}/{len(xs)*len(ys)}  {len(masks)} kept", file=sys.stderr)
        raw = list(range(raw_count))          # only its length is reported
    else:
        result = gen(img, points_per_batch=32, points_per_crop=args.points)
        raw = result["masks"]
        masks = []
        for m in raw:
            a = np.asarray(m, dtype=bool)
            if a.sum() < args.min_area * frame:
                continue
            ys_, xs_ = np.nonzero(a)
            by1, by2 = int(ys_.min()), int(ys_.max()) + 1
            bx1, bx2 = int(xs_.min()), int(xs_.max()) + 1
            masks.append((by1, bx1, a[by1:by2, bx1:bx2].copy()))

    t_infer = time.time() - t0
    print(f"  {len(raw)} raw proposals, {len(masks)} kept, in {t_infer:.0f}s", file=sys.stderr)
    # Largest first: see THE NESTING RULE above. Painting in this order leaves
    # every pixel owned by the smallest region that contains it.
    masks.sort(key=lambda t: -int(t[2].sum()))

    label = np.zeros((h, w), dtype=np.int32)
    kept = []
    for (oy, ox, a) in masks:
        if len(kept) >= args.max_regions:
            break
        mh, mw = a.shape
        win = label[oy:oy + mh, ox:ox + mw]
        area = int(a.sum())
        # Overlapping tiles hand us the same object several times. If most of a
        # proposal is already claimed it is a duplicate or a nested fragment,
        # not a new plane.
        if area and int((win[a] > 0).sum()) / area > 0.70:
            continue
        kept.append((oy, ox, a))
        win[a] = len(kept)
    masks = kept

    # Colours from a fixed golden-angle walk so a region keeps roughly the same
    # hue between runs and the overlay is readable rather than a mud of greys.
    def colour(i: int):
        import colorsys
        r, g, b = colorsys.hsv_to_rgb((i * 0.61803398875) % 1.0, 0.62, 0.98)
        return (int(r * 255), int(g * 255), int(b * 255))

    # The overlay is for eyes, so it is built small. A 6586x15923 RGB overlay is
    # 315MB in memory and unopenable; the masks stay at full resolution.
    ov_scale = min(1.0, 2000 / max(w, h))
    ow, oh = max(1, round(w * ov_scale)), max(1, round(h * ov_scale))
    tint = np.zeros((oh, ow, 3), dtype=np.uint8)
    lab_small = np.asarray(Image.fromarray(label.astype(np.int32), mode="I")
                           .resize((ow, oh), Image.Resampling.NEAREST))

    regions = []
    for i, (oy, ox, a) in enumerate(masks, start=1):
        mh, mw = a.shape
        sel = (label[oy:oy + mh, ox:ox + mw] == i)     # what survived nearer regions
        area = int(sel.sum())
        if area == 0:
            continue
        ys, xs = np.nonzero(sel)
        by1, by2 = int(ys.min()), int(ys.max()) + 1
        bx1, bx2 = int(xs.min()), int(xs.max()) + 1
        # Masks are stored CROPPED with an offset. A full-frame PNG per region
        # at this size would be ~60 x 105MP of mostly zeros.
        Image.fromarray((sel[by1:by2, bx1:bx2] * 255).astype(np.uint8), mode="L") \
             .save(out / "masks" / f"{i:03d}.png")
        tint[lab_small == i] = colour(i)
        regions.append({
            "id": i, "area": area, "areaFraction": round(area / frame, 6),
            "bbox": [ox + bx1, oy + by1, ox + bx2, oy + by2],
            "offset": [ox + bx1, oy + by1],
            "centroid": [int(ox + xs.mean()), int(oy + ys.mean())],
            "mask": f"masks/{i:03d}.png",
            "depth": None,                 # YOURS to fill in. 0 = farthest.
        })

    unclaimed = int((label == 0).sum())

    base = np.asarray(img.resize((ow, oh), Image.Resampling.LANCZOS)).astype(np.float32)
    blend = (base * 0.55 + tint.astype(np.float32) * 0.45).astype(np.uint8)
    ov = Image.fromarray(blend)
    d = ImageDraw.Draw(ov)
    for r in regions:
        x, y = int(r["centroid"][0] * ov_scale), int(r["centroid"][1] * ov_scale)
        t = str(r["id"])
        for dx, dy in ((-1, -1), (1, 1), (-1, 1), (1, -1)):
            d.text((x + dx, y + dy), t, fill=(0, 0, 0))
        d.text((x, y), t, fill=(255, 255, 255))
    ov.save(out / "overlay.png")

    meta = {
        "tool": "segment-regions",
        "image": str(src), "sourceSize": [w0, h0], "workSize": [w, h],
        "model": args.model, "device": device,
        "rawProposals": len(raw), "regions": len(regions),
        "unclaimedPixels": unclaimed,
        "unclaimedFraction": round(unclaimed / frame, 4),
        "minArea": args.min_area, "maxRegions": args.max_regions,
        "overlay": str(out / "overlay.png"),
        "note": "depth is null on every region — assign it, 0 = farthest. Region 0 is unclaimed background.",
        "loadSeconds": round(t_load, 1), "inferSeconds": round(t_infer, 1),
    }
    (out / "regions.json").write_text(json.dumps({**meta, "regionList": regions}, indent=2))
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
