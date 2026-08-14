#!/usr/bin/env python3
"""media-tools — segment-points: clicked points → depth planes. One job.

You say WHERE and HOW FAR; SAM says where the edges are. It cuts masks and
writes a layer stack. It does not render, warp, or move a camera.

WHY POINTS AND NOT AUTOMATIC SAMPLING (2026-08-13, measured twice). SAM's
automatic mask generator gives you OBJECTS, never PLANES. On Wang Meng's
葛稚川移居圖 it cut forty figures, rocks, roots and seals along their ink
contours in sixteen seconds — and left 66% of the frame unclaimed. Quadrupling
the sample density recovered three percentage points and produced only more
small objects. Tiling made it worse (82% unclaimed), correctly, because a plane
larger than a tile is clipped in every tile it appears in.

The big planes — cliff, canopy, ground, water, mist — are low-contrast and
amorphous, and no sampling density conjures them. But ONE CLICK does, because a
point prompt is what SAM is actually best at.

THE WINDOW IS THE RESOLUTION KNOB. SAM resizes its input to 1024 whatever you
give it, so the crop around your point decides the mask's precision: a 1200px
window yields ~1.2 native px per model px, an 8000px window yields ~8. A mask
cannot extend beyond its window either, so a plane needs a window big enough to
contain it. Small window for a crisp figure, large one for a whole cliff.

Overlap is resolved by DEPTH, not by area: nearer planes are painted last, so
where two masks disagree the nearer one wins. That is the correct rule here and
the opposite of segment-regions' nesting rule, which has no depth to consult.

usage:
  segment-points.py --image IN --points points.json --out DIR [flags]

  --image PATH     the master image (full resolution)
  --points PATH    points.json from pick.html
  --out DIR        layers/NNN-<name>.png, layers.json, overlay.png land here
  --window N       default native-pixel window when a point omits one (2500)
  --feather N      blur the mask edge by N px before cutting (default 2). Ink
                   contours are soft; a hard binary edge reads as a sticker.
  --max-grow N     when a mask hits its window edge, DOUBLE the window and cut
                   again, up to N times (default 3). Clipping is detectable
                   without looking at the picture, so it is fixed here rather
                   than handed back to a person or to a vision model.
  --max-plane F    reject a grown mask covering more than this fraction of the
                   WHOLE image and keep the previous attempt (default 0.35).
                   Without it, growing converges on window = whole image, where
                   clipping is impossible by definition and SAM answers a
                   coarser question — one plane came back as 75% of the scroll.
  --grow-ceiling F never grow past this multiple of the requested window
                   (default 4.0).

  --model ID       default facebook/sam-vit-huge
  --device NAME    mps (default on Apple Silicon) | cpu
  --no-layers      write masks and overlay only, skip the cut RGBA layers

Per-point fields honoured from points.json: x, y, depth, window, name, and
  pick   whole (default) | best | tight
         SAM returns three nested candidates. 'best' takes the highest IoU
         score, which is usually the TIGHTEST — a click on a riverbank came
         back as one pebble at 0.98. 'whole' takes the largest, which is what a
         depth plane almost always means.

Any plane whose mask reaches its window edge is reported as clippedByWindow.
That is a straight artificial boundary, not a real one — raise that point's
window and run again.

JSON on stdout. Progress on stderr.

example:
  .venv/bin/python tools/segment-points.py \\
    --image corpus/grabs/wang-meng.png \\
    --points jobs/wang-meng/points.json --out jobs/wang-meng/layers
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
    ap.add_argument("--points", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--window", type=int, default=2500)
    ap.add_argument("--feather", type=int, default=2)
    ap.add_argument("--max-grow", type=int, default=3)
    ap.add_argument("--max-plane", type=float, default=0.35)
    ap.add_argument("--grow-ceiling", type=float, default=4.0)
    ap.add_argument("--model", default="facebook/sam-vit-huge")
    ap.add_argument("--device", default=None)
    ap.add_argument("--no-layers", action="store_true")
    args = ap.parse_args()

    src, ptf, out = Path(args.image), Path(args.points), Path(args.out)
    for p in (src, ptf):
        if not p.exists():
            print(f"no such file: {p}", file=sys.stderr)
            return 1
    (out / "masks").mkdir(parents=True, exist_ok=True)
    if not args.no_layers:
        (out / "layers").mkdir(parents=True, exist_ok=True)

    import numpy as np
    import torch
    from PIL import Image, ImageFilter
    from transformers import SamModel, SamProcessor

    Image.MAX_IMAGE_PIXELS = None
    device = args.device or ("mps" if torch.backends.mps.is_available() else "cpu")

    spec = json.loads(ptf.read_text())
    points = spec.get("points", [])
    if not points:
        print("points.json has no points", file=sys.stderr)
        return 2

    img = Image.open(src).convert("RGB")
    W, H = img.size
    print(f"  {src.name}  {W}x{H}  {len(points)} points  device={device}", file=sys.stderr)

    t0 = time.time()
    processor = SamProcessor.from_pretrained(args.model)
    model = SamModel.from_pretrained(args.model).to(device).eval()
    t_load = time.time() - t0

    # Farthest first, so nearer planes paint over them where they disagree.
    points = sorted(points, key=lambda p: p.get("depth", 0))
    label = np.zeros((H, W), dtype=np.int16)          # 0 = unclaimed
    records = []
    t0 = time.time()

    def cut_at(px, py, win, mode):
        """One SAM point-prompt at one window size. Returns everything needed
        to decide whether the window was big enough."""
        x1, y1 = max(0, px - win // 2), max(0, py - win // 2)
        x2, y2 = min(W, x1 + win), min(H, y1 + win)
        x1, y1 = max(0, x2 - win), max(0, y2 - win)   # re-anchor at the edges
        crop = img.crop((x1, y1, x2, y2))

        enc = processor(crop, input_points=[[[px - x1, py - y1]]], return_tensors="pt")
        orig_sizes, resh_sizes = enc["original_sizes"], enc["reshaped_input_sizes"]
        # SamProcessor emits input_points as float64 and MPS has no float64 at
        # all — it raises rather than downcasting. Do it here, explicitly.
        inputs = {k: (v.float() if torch.is_tensor(v) and v.dtype == torch.float64 else v)
                  for k, v in enc.items()}
        inputs = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in inputs.items()}
        with torch.inference_mode():
            o = model(**inputs, multimask_output=True)
        masks = processor.image_processor.post_process_masks(
            o.pred_masks.cpu(), orig_sizes, resh_sizes
        )[0][0].numpy()
        # SAM returns three nested candidates: subpart, part, whole. Taking the
        # highest IoU score picks the TIGHTEST one — a click on a riverbank
        # returned a single pebble at 0.98 (2026-08-13). For a depth plane the
        # whole thing is almost always wanted, so 'whole' is the default and
        # scoring is available per point when it isn't.
        scores = o.iou_scores.cpu().numpy().reshape(-1)
        areas = [int(masks[i].astype(bool).sum()) for i in range(masks.shape[0])]
        if mode == "best":
            chosen = int(scores.argmax())
        elif mode == "tight":
            chosen = int(min(range(len(areas)), key=lambda i: areas[i] or 1 << 60))
        else:
            chosen = int(max(range(len(areas)), key=lambda i: areas[i]))
        m = masks[chosen].astype(bool)

        if args.feather > 0:
            soft = Image.fromarray((m * 255).astype(np.uint8), mode="L") \
                        .filter(ImageFilter.GaussianBlur(args.feather))
            m = np.asarray(soft) > 127

        # A mask running to the crop edge means the window CLIPPED the plane —
        # you get a straight artificial boundary that reads as a torn sticker in
        # the render. It is not a soft warning; the window was too small.
        # The image's OWN edge does not count: a plane really can end there.
        ch, cw = m.shape
        clipped = bool(
            (m[0, :].any() and y1 > 0) or (m[ch - 1, :].any() and y2 < H)
            or (m[:, 0].any() and x1 > 0) or (m[:, cw - 1].any() and x2 < W)
        )
        return {"m": m, "box": (x1, y1, x2, y2), "clipped": clipped,
                "score": float(scores[chosen]), "areas": areas, "win": win}

    for n, p in enumerate(points, start=1):
        px, py = int(round(p["x"] * W)), int(round(p["y"] * H))
        win = int(p.get("window") or args.window)
        mode = (p.get("pick") or "whole").lower()
        # Cap growth relative to what was asked for. An unbounded ceiling is
        # what let a 5000px window become 15923 and stop meaning anything.
        ceiling = min(max(W, H), int(win * args.grow_ceiling))

        # AUTO-GROW. A clipped mask is detectable without looking at anything,
        # so there is no reason to hand the problem back to a human or to a
        # vision model — just widen the crop and cut again. Measured on this
        # scroll: the planner's own review pass raised windows but under-raised
        # 9 of 17, because a clipped edge is invisible in an overlay unless you
        # already know the crop geometry.
        tries, res = [], None
        for _ in range(args.max_grow + 1):
            got = cut_at(px, py, win, mode)
            frac_of_image = int(got["m"].sum()) / (W * H)
            # A grown result that swallows the frame is NOT a fix. Doubling the
            # window until nothing is clipped converges on window = whole image,
            # where clipping is impossible by definition and SAM answers a
            # coarser question entirely ("the mountain"). Measured 2026-08-13:
            # six planes grew to the full height and one covered 75% of the
            # scroll. So a grow step is only accepted if it stays sane, and the
            # last sane attempt is what we keep.
            degenerate = frac_of_image > args.max_plane
            tries.append({"window": win, "clipped": got["clipped"],
                          "imageFraction": round(frac_of_image, 4),
                          "rejected": bool(degenerate and res is not None)})
            if degenerate and res is not None:
                break                                  # keep the previous, smaller cut
            res = got
            if not got["clipped"] or win >= ceiling:
                break
            win = min(win * 2, ceiling)

        m = res["m"]
        x1, y1, x2, y2 = res["box"]
        label[y1:y2, x1:x2][m] = n
        area = int(m.sum())
        records.append({
            "n": n, "id": p.get("id", n), "name": p.get("name") or f"plane-{n}",
            "depth": p.get("depth", 0), "point": [px, py],
            "window": res["win"], "windowRequested": int(p.get("window") or args.window),
            "grewTo": res["win"] if len(tries) > 1 else None, "attempts": tries,
            "cropBox": [x1, y1, x2, y2], "pick": mode,
            "score": round(res["score"], 4),
            "candidateAreas": res["areas"],
            "clippedByWindow": res["clipped"],
            "areaInWindow": area,
            "windowFraction": round(area / max(1, (x2 - x1) * (y2 - y1)), 4),
        })
        r = records[-1]
        grew = f"  grew {r['windowRequested']}→{r['window']}" if r["grewTo"] else ""
        flag = "  ← STILL CLIPPED at ceiling" if r["clippedByWindow"] else ""
        print(f"    {n}/{len(points)}  {r['name']:<24} depth={r['depth']} "
              f"win={r['window']}  iou={r['score']:.2f}  "
              f"fills {r['windowFraction']*100:.0f}%{grew}{flag}", file=sys.stderr)

    t_infer = time.time() - t0

    # Cut the actual layers, farthest first, each as cropped RGBA + an offset.
    for r in records:
        sel = label == r["n"]
        area = int(sel.sum())
        r["areaFinal"] = area
        if area == 0:
            r["layer"] = None                # entirely covered by nearer planes
            continue
        ys, xs = np.nonzero(sel)
        bx1, by1, bx2, by2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        r["bbox"] = [bx1, by1, bx2, by2]
        r["offset"] = [bx1, by1]
        sub = sel[by1:by2, bx1:bx2]
        Image.fromarray((sub * 255).astype(np.uint8), mode="L").save(out / "masks" / f"{r['n']:03d}.png")
        if args.no_layers:
            r["layer"] = None
            continue
        rgba = np.dstack([
            np.asarray(img.crop((bx1, by1, bx2, by2)), dtype=np.uint8),
            (sub * 255).astype(np.uint8),
        ])
        name = f"{r['depth']}{r['n']:02d}-{r['name']}".replace("/", "-")
        Image.fromarray(rgba, mode="RGBA").save(out / "layers" / f"{name}.png")
        r["layer"] = f"layers/{name}.png"

    ov_scale = min(1.0, 1600 / max(W, H))
    ow, oh = max(1, round(W * ov_scale)), max(1, round(H * ov_scale))
    small = np.asarray(Image.fromarray(label.astype(np.int32), mode="I")
                       .resize((ow, oh), Image.Resampling.NEAREST))
    base = np.asarray(img.resize((ow, oh), Image.Resampling.LANCZOS)).astype(np.float32)
    tint = np.zeros((oh, ow, 3), dtype=np.uint8)
    for r in records:
        d = r["depth"]
        # Same ramp as the picker: far is cool, near is warm.
        import colorsys
        cr, cg, cb = colorsys.hsv_to_rgb(((210 - d * 22) % 360) / 360, 0.72, 0.95)
        tint[small == r["n"]] = (int(cr * 255), int(cg * 255), int(cb * 255))
    Image.fromarray((base * 0.55 + tint.astype(np.float32) * 0.45).astype(np.uint8)).save(out / "overlay.png")

    unclaimed = int((label == 0).sum())
    meta = {
        "tool": "segment-points",
        "image": str(src), "size": [W, H], "model": args.model, "device": device,
        "planes": len(records),
        "unclaimedFraction": round(unclaimed / (W * H), 4),
        "overlay": str(out / "overlay.png"),
        "feather": args.feather,
        "note": "planes painted farthest-first; nearer wins on overlap. Layers are cropped RGBA + offset.",
        "loadSeconds": round(t_load, 1), "inferSeconds": round(t_infer, 1),
        "planeList": records,
    }
    (out / "layers.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in meta.items() if k != "planeList"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
