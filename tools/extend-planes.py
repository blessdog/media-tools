#!/usr/bin/env python3
"""media-tools — extend-planes: grow each plane PAST the edge of the shot.

One job. It does not fill behind occluders (`inpaint-planes`), seal gaps
(`complete-planes`), pin objects (`pin-objects`) or render.

WHY. A camera that only pushes forward stays inside the shot. A camera that
travels laterally runs out of shot — not out of paint behind an occluder, but
out of picture. Measured on wang-meng: at full lateral wander the frame is 88%
holes and needs 298px of reach where a straight push needs 53.

THE MARGIN IS THE PAINTING, NOT AN INVENTION. A shot is a CROP of a source
work, and what lies past its edge is, overwhelmingly, more of that work.
--source-crop names the provenance (master path + crop box + scale) and every
margin pixel whose master coordinate lands inside the master is SAMPLED from
it — exact, free, and actually by the artist. The first version of this tool
asked a model to invent the margin; three runs produced fabricated inscription
blocks, collector seals and garbled captions for territory that sat on disk the
whole time (wang-meng: the 720x1280 shot is 2% of a 105-megapixel scroll, with
4500+ shot-px of real painting above it). The model is a FALLBACK, used only
where the master itself ends — the true edges of the scroll.

DEPTH IS AN INPUT HERE, NEVER AN OUTPUT. Every margin pixel is painted into a
plane that already has an authored z, so its depth is known by construction.
The alternative — widen the picture, estimate its depth — is measured to fail:
generated shan shui scored 88.4% R-squared of depth against image ROW, worse
than the painting's own 48.9%, because the imitation reproduces the genre's
stacked-ridge depth CONVENTION and the estimator returns a ramp.

THE FREE CONTROL. New content is added strictly OUTSIDE the original canvas,
so a render at the original framing MUST come out unchanged.

WHICH PLANES GROW. Only those that reach the border. A plane whose silhouette
stops inside the picture is a thing with an edge — a pine, a figure, a rock —
and continuing it into the margin invents a bigger object. A plane that runs
off the edge is a surface that was cropped, and continuing THAT is just
restoring what the crop removed.

usage:
  extend-planes.py --layers DIR --source-crop crop.json --out DIR
                   [--margin N] [--touch N] [--dry-run]

  --layers DIR       a plane stack, ideally already through inpaint-planes
  --source-crop F    provenance JSON from locate-crop: {master, crop:{x,y,
                     masterPxPerShotPx}}. Master path resolves relative to F.
  --out DIR          the extended stack: layers.json + layers/*.png
  --margin N         px of new canvas on every side (default 256). Set it from
                     a measured path: probe-path-envelope reports the reach a
                     given camera wander needs.
  --touch N          a plane reaches the border if it comes within N px of it
                     (default 8)
  --prompt TEXT      fallback-model prompt, used ONLY past the master's edge
  --guidance F       fallback flux guidance (default 30)
  --context N        px of real painting around a fallback band as context
                     (default 420). Windows dominated by brushwork read as
                     "continue this surface"; the whole canvas reads as
                     "artwork on a page" and summons a catalogue layout.
  --seed N           fallback base seed; each plane gets seed+index
  --dry-run          report who grows, how much is sampled vs generated, then
                     stop WITHOUT spending anything
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _flux import SHANSHUI_PROMPT, fill  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main() -> int:
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--layers", required=True)
    ap.add_argument("--source-crop", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--margin", type=int, default=256)
    ap.add_argument("--touch", type=int, default=8)
    ap.add_argument("--prompt", default=SHANSHUI_PROMPT)
    ap.add_argument("--guidance", type=int, default=30)
    ap.add_argument("--context", type=int, default=420)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    lay, out = Path(a.layers), Path(a.out)
    meta = json.loads((lay / "layers.json").read_text())
    W, H = meta["size"]
    M = a.margin
    NW, NH = W + 2 * M, H + 2 * M

    shot_path = Path(meta["image"])
    if not shot_path.exists():
        print(f"layers.json names {shot_path}, missing from here. Run from the "
              f"repo root.", file=sys.stderr)
        return 1
    shot = np.asarray(Image.open(shot_path).convert("RGB"))

    prov_path = Path(a.source_crop)
    prov = json.loads(prov_path.read_text())
    crop = prov["crop"]
    k = float(crop["masterPxPerShotPx"])
    cx, cy = float(crop["x"]), float(crop["y"])
    master_path = (prov_path.parent / prov["master"]).resolve()
    if not master_path.exists():
        print(f"{a.source_crop} names master {master_path}, missing.",
              file=sys.stderr)
        return 1
    master = np.asarray(Image.open(master_path).convert("RGB"))
    mH, mW = master.shape[:2]

    # THE REAL MARGIN. Big-canvas (X,Y) sits at shot (X-M, Y-M), i.e. master
    # (cx + k(X-M), cy + k(Y-M)). warpAffine with the dst->src map resamples
    # the master onto the big canvas at exact subpixel alignment. k > 1 means
    # downsampling, and plain bilinear would alias the dry-brush strokes into
    # shimmer, so blur the master to the target Nyquist first — the standard
    # prefilter, sigma ~ 0.5*sqrt(k^2-1).
    sigma = 0.5 * np.sqrt(max(k * k - 1.0, 0.0))
    src = cv2.GaussianBlur(master, (0, 0), sigma) if sigma > 0.1 else master
    A_inv = np.float32([[k, 0, cx - k * M], [0, k, cy - k * M]])
    big_real = cv2.warpAffine(
        src, A_inv, (NW, NH),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=tuple(int(v) for v in np.median(shot.reshape(-1, 3), 0)))

    # Where the master actually HAS paint for us — computed from coordinates,
    # never inferred from pixel values.
    Xs = np.arange(NW)[None, :].repeat(NH, 0)
    Ys = np.arange(NH)[:, None].repeat(NW, 1)
    mx = cx + k * (Xs - M)
    my = cy + k * (Ys - M)
    valid = (mx >= 0) & (mx <= mW - 1) & (my >= 0) & (my <= mH - 1)

    # Interior stays the SHOT's own bytes: the frame-zero control demands the
    # original framing render unchanged, and the shot is the ground truth the
    # whole stack was cut from. The resampled master only supplies the margin.
    big_real[M:M + H, M:M + W] = shot

    planes = sorted([p for p in meta["planeList"] if p.get("layer")],
                    key=lambda p: p["depth"])

    plan = []
    for i, p in enumerate(planes):
        im = np.asarray(Image.open(lay / p["layer"]).convert("RGBA"))
        ox, oy = p["offset"]
        h, w = im.shape[:2]
        A = np.zeros((H, W), np.uint8)
        A[oy:oy + h, ox:ox + w] = im[..., 3]
        alpha = A > 128
        t = a.touch
        edges = {
            "left": bool(alpha[:, :t].any()), "right": bool(alpha[:, -t:].any()),
            "top": bool(alpha[:t, :].any()), "bottom": bool(alpha[-t:, :].any()),
        }
        plan.append((i, p, im, (ox, oy), alpha, edges))

    print(f"{'plane':26} {'depth':>6}  grows into", file=sys.stderr)
    for i, p, _, _, alpha, edges in plan:
        sides = [kk for kk, v in edges.items() if v]
        print(f"  {p['name'][:24]:24} {p['depth']:>6}  "
              f"{', '.join(sides) if sides else '— interior object, left alone'}",
              file=sys.stderr)

    growers = [x for x in plan if any(x[5].values())]
    if not a.dry_run:
        (out / "layers").mkdir(parents=True, exist_ok=True)

    # WHO OWNS EACH MARGIN PIXEL — by Voronoi, not by projection.
    # Edge-column replication (`alpha[:, -1:]`) produced HORIZONTAL STRIPES
    # wherever the edge was intermittent. Give every margin pixel to the
    # nearest border-touching plane instead; interior objects never grow, and
    # the margin tiles completely with contiguous regions.
    seed = np.full((NH, NW), 255, np.uint8)
    lab_to_plane: dict[int, int] = {}
    for i, p, im, (ox, oy), alpha, edges in plan:
        if not any(edges.values()):
            continue
        seed[M:M + H, M:M + W][alpha] = 0
    if (seed == 0).any():
        _, labels = cv2.distanceTransformWithLabels(
            seed, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        for i, p, im, (ox, oy), alpha, edges in plan:
            if not any(edges.values()):
                continue
            sub = np.zeros((NH, NW), bool)
            sub[M:M + H, M:M + W] = alpha
            for l in np.unique(labels[sub]):
                lab_to_plane[int(l)] = i
        vec = np.vectorize(lambda l: lab_to_plane.get(int(l), -1))
        owner_lab = vec(labels).astype(np.int32)
    else:
        owner_lab = np.full((NH, NW), -1, np.int32)

    margin_region = np.ones((NH, NW), bool)
    margin_region[M:M + H, M:M + W] = False

    # Bands are fully determined before a penny is spent, so --dry-run can
    # exercise the Voronoi rather than exiting above it.
    bands = {i: (margin_region & (owner_lab == i)) for i, *_ in plan}
    claimed = sum(int(b.sum()) for b in bands.values())
    real_px = sum(int((b & valid).sum()) for b in bands.values())
    gen_px = claimed - real_px
    calls = sum(1 for b in bands.values() if (b & ~valid).sum() >= 500)
    print(f"\nmargin is {int(margin_region.sum())}px; planes claim {claimed}px "
          f"({claimed / max(int(margin_region.sum()), 1) * 100:.1f}%)",
          file=sys.stderr)
    print(f"  sampled from the master : {real_px:8}px "
          f"({real_px / max(claimed, 1) * 100:.1f}%)", file=sys.stderr)
    print(f"  past the master's edge  : {gen_px:8}px -> {calls} model call(s)",
          file=sys.stderr)
    for i, p, *_ in plan:
        n = int(bands[i].sum())
        if n:
            print(f"  {p['name'][:24]:24} claims {n:8}px of margin",
                  file=sys.stderr)
    if a.dry_run:
        print(json.dumps({"tool": "extend-planes", "dryRun": True,
                          "margin": M, "canvas": [NW, NH],
                          "planes": len(plan), "wouldGrow": len(growers),
                          "marginPx": int(margin_region.sum()),
                          "claimedPx": claimed, "sampledPx": real_px,
                          "generatedPx": gen_px, "calls": calls,
                          "spent": "nothing"}, indent=2))
        return 0

    new_list, report = [], []
    for i, p, im, (ox, oy), alpha, edges in plan:
        big_a = np.zeros((NH, NW), np.uint8)
        big_rgb = big_real.copy()
        h, w = im.shape[:2]
        big_a[M + oy:M + oy + h, M + ox:M + ox + w] = im[..., 3]
        big_rgb[M + oy:M + oy + h, M + ox:M + ox + w] = im[..., :3]

        band = bands[i]
        n = int(band.sum())
        n_gen = int((band & ~valid).sum())
        if n:
            # The sampled part is already sitting in big_rgb — claiming it is
            # just opacity. Only territory past the master's edge needs paint.
            missing = band & ~valid
            if n_gen >= 500:
                ys, xs = np.nonzero(missing)
                bx0, bx1 = int(xs.min()), int(xs.max()) + 1
                by0, by1 = int(ys.min()), int(ys.max()) + 1
                c = a.context
                cx0, cy0 = max(0, bx0 - c), max(0, by0 - c)
                cx1, cy1 = min(NW, bx1 + c), min(NH, by1 + c)
                sub_rgb = big_rgb[cy0:cy1, cx0:cx1]
                sub_band = missing[cy0:cy1, cx0:cx1]
                got = fill(sub_rgb, sub_band, a.prompt, a.seed + i, a.guidance)
                big_rgb[cy0:cy1, cx0:cx1] = np.where(
                    sub_band[..., None], got, sub_rgb)
            big_a = np.where(band, 255, big_a).astype(np.uint8)
        report.append((p["name"], n, min(n_gen, n) if n_gen >= 500 else 0))

        keep = big_a > 0
        ys, xs = np.nonzero(keep)
        if not len(ys):
            continue
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        tile = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        tile[..., :3] = big_rgb[y0:y1, x0:x1]
        tile[..., 3] = big_a[y0:y1, x0:x1]
        name = Path(p["layer"]).name
        Image.fromarray(tile).save(out / "layers" / name)

        q = dict(p)
        q["layer"] = f"layers/{name}"
        q["offset"] = [x0, y0]
        q["extendedPx"] = n
        new_list.append(q)

    # The master has to grow too, or the base plane cannot cover the new canvas.
    big_master_path = out / "master-extended.png"
    Image.fromarray(big_real).save(big_master_path)

    nm = dict(meta)
    nm["planeList"] = new_list
    nm["size"] = [NW, NH]
    nm["image"] = str(big_master_path)
    nm["tool"] = "extend-planes"
    nm["extendedFrom"] = str(lay)
    nm["sourceCrop"] = str(a.source_crop)
    nm["margin"] = M
    nm["originOffset"] = [M, M]
    nm["note"] = ("planes grown past the shot edge at their authored depths. "
                  "Margin pixels are SAMPLED from the source master via the "
                  "recorded crop provenance; a model paints only past the "
                  "master's own edge. Depth is never estimated here. A render "
                  "at the original framing, offset by originOffset, must be "
                  "unchanged.")
    (out / "layers.json").write_text(json.dumps(nm, indent=1))

    for nmm, n, g in sorted(report, key=lambda r: -r[1]):
        if n:
            tag = f" ({g}px generated)" if g else ""
            print(f"  {nmm:24} +{n:7}px outward{tag}", file=sys.stderr)

    print(json.dumps({
        "tool": "extend-planes", "layers": str(a.layers), "out": str(out),
        "sourceCrop": str(a.source_crop),
        "canvas": [NW, NH], "margin": M, "originOffset": [M, M],
        "planes": len(new_list), "grown": sum(1 for _, n, _ in report if n),
        "totalExtended": sum(n for _, n, _ in report),
        "sampledPx": sum(n - g for _, n, g in report),
        "generatedPx": sum(g for _, _, g in report),
        "verify": "render at originOffset — the original framing MUST be unchanged",
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
