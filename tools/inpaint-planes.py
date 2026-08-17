#!/usr/bin/env python3
"""media-tools — inpaint-planes: paint what is BEHIND each plane's occluders.

One job. It does not seal gaps (`complete-planes`), judge a stack
(`probe-planes`), or render (`render-parallax`).

THE PROBLEM IT SOLVES. A depth plane is a card cut to the silhouette of what was
visible. Move the camera and a nearer card slides, exposing the strip of farther
card that was never cut because it was never visible — a hole. Measured on
wang-meng: a 0.45 dolly opened holes over 6.0% of the last frame and 22.7% of the
frame at some point in the clip.

WHY LAYER SPACE AND NOT FRAME SPACE. What sits behind a plane does not change as
the camera moves. So fill each plane ONCE, before any frame exists, instead of
repairing 120 frames. Eleven fills instead of 120, no temporal flicker possible
by construction, the clip stays a resampling of fixed texels, and the camera can
be re-cut afterwards for free. This is the Layered Depth Image idea (Shih et al.,
CVPR 2020) and the same move 3D Ken Burns makes.

THE CONTROL IS FREE, SO THERE IS NO EXCUSE. Every pixel this tool paints is, at
rest, hidden behind the very plane that was occluding it. So FRAME ZERO MUST COME
OUT BYTE-IDENTICAL. If it does not, the tool painted somewhere it had no
business. --verify renders frame zero before and after and reports the diff.

THE SOURCE OF PATCHES MATTERS MORE THAN THE ALGORITHM. Filling the strip behind
the pine with patches sampled from anywhere in the crop pastes PINE into the
cliff. So the known-pixel set handed to SHIFTMAP is restricted to the plane's OWN
texture and nothing else; everything not owned by this plane is unknown, and only
the requested band is kept from the result. TELEA and Navier-Stokes are offered
but smear ink-on-silk into mush — patch synthesis copies real silk.

usage:
  inpaint-planes.py --layers DIR --out DIR [--behind N] [--pad F] [--method M]

  --layers DIR   a plane stack, ideally already through complete-planes
  --out DIR      the extended stack: layers.json + layers/*.png
  --behind N     how many px of hidden content to paint behind each occluder
                 (default 100). Set it from the measured hole width, not taste:
                 probe the render, take the widest hole, use that.
  --pad F        synthesis box as a multiple of the work box (default 1.3)
  --method M     shiftmap (default) | telea | ns
  --min-band N   skip a plane whose revealed band is under N px (default 200)
  --max-ratio F  never ask a plane to synthesise more than F times its own
                 known area (default 2.0); --behind shrinks per plane until
                 it fits. Patch synthesis COPIES — a 20k-px bridge asked for
                 116k came back 33% unfilled, a 4k-px pine branch 28%, while
                 every plane with a large known region came back clean.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
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
    ap.add_argument("--out", required=True)
    ap.add_argument("--behind", type=int, default=100)
    ap.add_argument("--pad", type=float, default=1.3)
    ap.add_argument("--method", default="shiftmap")
    ap.add_argument("--min-band", type=int, default=200)
    ap.add_argument("--max-ratio", type=float, default=2.0)
    a = ap.parse_args()

    lay = Path(a.layers)
    meta = json.loads((lay / "layers.json").read_text())
    W, H = meta["size"]
    src_path = Path(meta["image"])
    if not src_path.exists():
        print(f"layers.json names {src_path}, missing from here. Run from the "
              f"repo root.", file=sys.stderr)
        return 1
    out = Path(a.out)
    (out / "layers").mkdir(parents=True, exist_ok=True)

    planes = sorted([p for p in meta["planeList"] if p.get("layer")],
                    key=lambda p: p["depth"])
    # Index in paint order: 0 is farthest. "Nearer" therefore means a HIGHER
    # index, and only a nearer plane can occlude.
    own = np.full((H, W), UNCLAIMED, np.int32)
    masks, alphas = [], []
    for i, p in enumerate(planes):
        im = np.asarray(Image.open(lay / p["layer"]).convert("RGBA"))
        ox, oy = p["offset"]
        h, w = im.shape[:2]
        A = np.zeros((H, W), np.uint8)
        A[oy:oy + h, ox:ox + w] = im[..., 3]
        alphas.append(A)
        masks.append(A > 128)
        own[A > 128] = i

    # Cumulative FULL opacity from nearer planes. A farther plane is provably
    # invisible at rest only where something nearer is alpha 255 — a feathered
    # edge at 200 still lets 22% of it through, and that is exactly the leak that
    # broke this tool's own control on the first run.
    hidden = np.zeros((len(planes), H, W), bool)
    acc = np.zeros((H, W), bool)
    for i in range(len(planes) - 1, -1, -1):
        hidden[i] = acc                      # everything nearer than i, so far
        acc = acc | (alphas[i] == 255)

    img = np.asarray(Image.open(src_path).convert("RGB"))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (a.behind * 2 + 1,) * 2)
    new_list, report = [], []

    for i, p in enumerate(planes):
        m = masks[i]
        # Never touch a pixel this plane already has ANY alpha at — that would
        # rewrite the feathered edge and change compositing at rest.
        untouched = alphas[i] == 0
        # PATCH SYNTHESIS COPIES, so a plane cannot be asked to invent much more
        # than it already is. Measured: a 20k-px bridge asked for 116k came back
        # 33% unfilled, a 4k-px pine branch 28%, while every plane with a large
        # known region came back clean. Shrink the reach until the ask is
        # supportable, and say by how much.
        behind, band = a.behind, None
        while True:
            kk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (behind * 2 + 1,) * 2)
            band = (cv2.dilate(m.astype(np.uint8), kk) > 0) & untouched & hidden[i]
            if behind <= 8 or band.sum() <= a.max_ratio * max(int(m.sum()), 1):
                break
            behind = int(behind * 0.7)
        nf = 0
        if band.sum() < a.min_band:
            secs, filled = 0.0, 0
            rgb = img
        else:
            work = m | band
            ys, xs = np.nonzero(work)
            bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
            pw = int((bx1 - bx0) * (a.pad - 1) / 2)
            ph = int((by1 - by0) * (a.pad - 1) / 2)
            x0, y0 = max(0, bx0 - pw), max(0, by0 - ph)
            x1, y1 = min(W, bx1 + pw + 1), min(H, by1 + ph + 1)

            crop = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_RGB2BGR)
            # KNOWN = this plane's own texture, nothing else. Anything else as a
            # patch source is how the pine gets pasted into the cliff.
            known = (m[y0:y1, x0:x1].astype(np.uint8)) * 255
            t = time.time()
            if a.method == "shiftmap":
                dst = np.zeros_like(crop)
                cv2.xphoto.inpaint(crop, known, dst, cv2.xphoto.INPAINT_SHIFTMAP)
            else:
                flag = cv2.INPAINT_TELEA if a.method == "telea" else cv2.INPAINT_NS
                dst = cv2.inpaint(crop, 255 - known, 5, flag)
            secs = round(time.time() - t, 2)

            rgb = img.copy()
            sub = cv2.cvtColor(dst, cv2.COLOR_BGR2RGB)
            bsub = band[y0:y1, x0:x1]
            # SHIFTMAP leaves pixels it could find no patch for at exactly black,
            # and black is not a colour in this painting — it would ship as a
            # hole that does not even read as a hole. Carry the nearest pixel it
            # DID solve into them: still real silk, never a smear, never 0,0,0.
            unfilled = bsub & (sub.max(2) < 8)
            nf = int(unfilled.sum())
            if nf:
                # distanceTransformWithLabels seeds on ZERO pixels, so the SOLVED
                # ones must be the zeros. Inverted, it copies black into black.
                seed = np.where(unfilled, 255, 0).astype(np.uint8)
                _, lb = cv2.distanceTransformWithLabels(
                    seed, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
                ok = ~unfilled
                lut = np.zeros((int(lb.max()) + 1, 3), np.uint8)
                src_px = np.where(bsub[..., None], sub, img[y0:y1, x0:x1])
                lut[lb[ok]] = src_px[ok]
                sub = np.where(unfilled[..., None], lut[lb], sub)
            region = rgb[y0:y1, x0:x1]
            region[bsub] = sub[bsub]        # keep ONLY the requested band
            rgb[y0:y1, x0:x1] = region
            filled = int(band.sum())

        # Original alpha survives EXACTLY; the band is added only where alpha
        # was zero. Anything else silently redraws the plane's own edge.
        alpha_new = np.where(alphas[i] > 0, alphas[i],
                             band.astype(np.uint8) * 255)
        keep = alpha_new > 0
        ys, xs = np.nonzero(keep)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        tile = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        tile[..., :3] = rgb[y0:y1, x0:x1]
        tile[..., 3] = alpha_new[y0:y1, x0:x1]
        name = Path(p["layer"]).name
        Image.fromarray(tile).save(out / "layers" / name)

        q = dict(p)
        q["layer"] = f"layers/{name}"
        q["offset"] = [x0, y0]
        q["paintedBehind"] = filled
        new_list.append(q)
        report.append((p["name"], int(m.sum()), filled, secs, behind, nf))

    for nm, base, fl, s, bh, nf in sorted(report, key=lambda r: -r[2]):
        if fl:
            note = f"  reach {bh}px" + (f", {nf} carried" if nf else "")
            print(f"  {nm:24} {base:7}px + {fl:6}px behind  ({s}s){note}",
                  file=sys.stderr)

    new_meta = dict(meta)
    new_meta["planeList"] = new_list
    new_meta["tool"] = "inpaint-planes"
    new_meta["extendedFrom"] = str(lay)
    new_meta["behindPx"] = a.behind
    new_meta["note"] = ("each plane painted on behind its occluders; every added "
                        "pixel is hidden at rest, so frame zero must render "
                        "byte-identical to the source stack.")
    (out / "layers.json").write_text(json.dumps(new_meta, indent=1))

    print(json.dumps({
        "tool": "inpaint-planes", "layers": str(lay), "out": str(out),
        "planes": len(new_list), "behindPx": a.behind, "method": a.method,
        "totalPaintedBehind": sum(r[2] for r in report),
        "unfilledCarried": sum(r[5] for r in report),
        "reachShrunk": [r[0] for r in report if r[4] < a.behind],
        "seconds": round(sum(r[3] for r in report), 1),
        "verify": "render frame 0 from both stacks — it MUST be byte-identical",
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
