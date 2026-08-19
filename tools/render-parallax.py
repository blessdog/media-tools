#!/usr/bin/env python3
"""media-tools — render-parallax: depth planes + a camera path → frames. One job.

It renders frames. It does not cut layers, animate water, grade, or encode
video — ffmpeg turns the frames into a file and that is a shell command, not a
tool's business.

WHY THIS INSTEAD OF A VIDEO MODEL. Every output frame is the SAME PAINTING
resampled from a new camera position. The diffusion model ran zero times; the
ink is fixed texels being reprojected. So the medium cannot boil, cannot
re-derive itself, and cannot grow a sixth finger — the failures that started
this whole lane are structurally impossible here rather than merely unlikely.

THE CAMERA IS A REAL PINHOLE, not a stack of sliding cards. Each plane sits at
its own z, and screen scale is f/(z - camZ). That single expression gives you
parallax on lateral motion AND correct differential zoom on a dolly, for free
and consistently. Cards sliding at hand-tuned rates look right for one move and
wrong for the next.

WHY THE SOURCE IS NEVER RESIZED. Layers come from a 6586x15923 master. Scaling
17 of those per frame is minutes per frame. Image.transform with an inverse
affine costs O(OUTPUT pixels) instead — it asks "for this output pixel, what
source pixel?" — so a frame costs 17 x 2MP regardless of how big the painting
is. That is the difference between an hour and a second.

A hanging scroll is 1:2.4 and composed bottom-to-top as a journey, so the
default path with no --path is exactly that: a slow climb from the river to the
peaks, easing in and out.

usage:
  render-parallax.py --layers DIR --out DIR [flags]

  --layers DIR     a segment-points output dir (layers.json + layers/*.png)
  --out DIR        frames land here as %05d.png
  --path PATH      camera path JSON. Omitted = the default climb.
  --width N        output width (default 1920)
  --height N       output height (default 1080)
  --fps N          default 30
  --duration S     seconds, when the path does not say (default 12)
  --z-near F       distance to the NEAREST plane (default 1.0). Smaller = more
                   violent parallax; this is the main dial.
  --z-step F       extra distance per depth level (default 0.035). Small ONLY
                   because of the single-focal bug --plane-fit fixes: at 0.28
                   the farthest plane sat 3.5x away and rendered at 28% scale,
                   which is not parallax, it is a diorama. WITH --plane-fit
                   that constraint is gone and 0.15-0.30 is the useful range.
  --plane-fit      REST-NORMALISED PROJECTION. Fixes the reason a push looks
                   like a zoom. Without it one global focal f0 is taken at
                   mid-depth, so separating planes in z changes their PAINTED
                   size — near ones balloon, far ones shrink — and the only way
                   to keep the composition was to throttle --z-step until the
                   depth range was too small to see. Measured on wang-meng's
                   11-plane shot stack: z spanned 1.000..1.315 and a 0.22 dolly
                   produced 1.201x of common zoom against 6.8% of differential.
                   96% of the motion was identical for every pixel, which is
                   what a zoom IS. With --plane-fit every world point is scaled
                   by zr/(zr-camZ) using its OWN rest depth zr, which is exactly
                   1.0 at camZ=0 for every plane at any separation. So frame
                   zero is the painting pixel-for-pixel however far apart the
                   planes are, tilted or not, and --z-step is free to be real.
                   Same z-step 0.035 -> 6.8%; 0.15 -> 16.2%; 0.15 with a 0.5
                   dolly -> 57%. Off by default so old renders reproduce.
  --no-base        do not lay the whole master underneath as a backing plane.
                   By default it IS laid down, farthest of all, so the pixels
                   no plane claimed still show the painting instead of a hole.
  --geometry PATH  per-plane 3D ORIENTATION, as {"plane-name": {"tiltX":..,
                   "tiltY":..}}. Without it every plane is fronto-parallel — a
                   billboard — and a Z push can only magnify pixels, which is a
                   zoom, not a flight. Tilt makes a plane recede: tiltX pitches
                   it away with height (ground planes), tiltY yaws it away
                   across width (cliff faces turning out of frame).
                   Units are dz per source pixel, so 0.00004 over a 3000px
                   plane is 0.12 of depth across it. Small numbers.
  --fill NAME      what shows through gaps: paper (default) | black | edge
  --preview N      render only every Nth frame, for a fast look
  --stills         write first/middle/last only, then stop

Camera path JSON:
  { "fps": 30, "duration": 12,
    "keys": [ {"t":0,  "x":0.5, "y":0.93, "z":0.0,  "fov":1.0},
              {"t":12, "x":0.5, "y":0.10, "z":-0.25,"fov":1.0} ] }
  x,y   camera target, normalised on the master. 0,0 top-left.
  z     dolly. NEGATIVE pulls back, positive pushes in. Keep it small: the
        nearest plane is only z-near away and pushing past it turns the frame
        inside out.
  fov   zoom multiplier, 1.0 = the framing that fits the output width.
  Interpolation is smoothstep between keys — eased at both ends, which is what
  makes a move read as serene rather than mechanical.

JSON on stdout. Progress on stderr.

example:
  .venv/bin/python tools/render-parallax.py \\
    --layers jobs/wang-meng/layers-v4 --out jobs/wang-meng/frames --duration 14
  ffmpeg -r 30 -i jobs/wang-meng/frames/%05d.png -c:v libx264 -crf 16 \\
    -pix_fmt yuv420p jobs/wang-meng/drift.mp4
"""

import argparse
import json
import sys
import time
from pathlib import Path


def smoothstep(a, b, t):
    t = max(0.0, min(1.0, t))
    return a + (b - a) * (t * t * (3 - 2 * t))


def sample(keys, t):
    """Piecewise smoothstep through the keyframes."""
    if t <= keys[0]["t"]:
        return keys[0]
    if t >= keys[-1]["t"]:
        return keys[-1]
    for k0, k1 in zip(keys, keys[1:]):
        if k0["t"] <= t <= k1["t"]:
            span = (k1["t"] - k0["t"]) or 1e-9
            u = (t - k0["t"]) / span
            return {f: smoothstep(k0.get(f, 0.0), k1.get(f, 0.0), u) for f in ("x", "y", "z", "fov")}
    return keys[-1]


def main() -> int:
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--layers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--path")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--duration", type=float, default=12.0)
    ap.add_argument("--z-near", type=float, default=1.0)
    ap.add_argument("--z-step", type=float, default=0.035)
    ap.add_argument("--plane-fit", action="store_true")
    ap.add_argument("--no-base", action="store_true")
    ap.add_argument("--geometry")
    ap.add_argument("--living",
                    help='JSON map {plane-name: {"dir": textures dir of '
                         '%%03d.png sized like the plane, "n": count, "on": '
                         'hold}} — the plane\'s texture is swapped per frame '
                         '(index = frame//on %% n) so its ink moves while its '
                         'depth, footprint, and tilt stay authored. Off = '
                         'every plane static, old renders reproduce.')
    ap.add_argument("--fill", default="paper")
    ap.add_argument("--preview", type=int, default=1)
    ap.add_argument("--stills", action="store_true")
    args = ap.parse_args()

    lay = Path(args.layers)
    meta_path = lay / "layers.json"
    if not meta_path.exists():
        print(f"no layers.json in {lay}", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    def find_coeffs(dst, src):
        """8 coefficients mapping OUTPUT quad -> SOURCE quad.

        PIL's PERSPECTIVE transform, like AFFINE, is an INVERSE map: it asks
        'for this output pixel, which source pixel?'. So the solve is dst->src,
        which is also why the cost stays O(output pixels) no matter how big the
        painting is.
        """
        A, B = [], []
        for (dx, dy), (sx, sy) in zip(dst, src):
            A.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
            A.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
            B += [sx, sy]
        res = np.linalg.solve(np.asarray(A, dtype=np.float64), np.asarray(B, dtype=np.float64))
        return tuple(res)

    tilts = json.loads(Path(args.geometry).read_text()) if args.geometry else {}

    meta = json.loads(meta_path.read_text())
    W_SRC, H_SRC = meta["size"]
    planes = [p for p in meta["planeList"] if p.get("layer")]
    if not planes:
        print("layers.json has no cut layers (was --no-layers used?)", file=sys.stderr)
        return 1
    planes.sort(key=lambda p: p["depth"])          # farthest first = paint order

    max_depth = max(p["depth"] for p in planes)
    for p in planes:
        # Nearest plane sits at z-near; each step further back adds z-step.
        p["z"] = args.z_near + (max_depth - p["depth"]) * args.z_step
        img = Image.open(lay / p["layer"]).convert("RGBA")
        p["img"] = img
        p["ox"], p["oy"] = p["offset"]
    if not args.no_base:
        base = {
            "name": "__master__", "depth": planes[0]["depth"], "layer": None,
            "z": args.z_near + (max_depth - planes[0]["depth"] + 1) * args.z_step,
            "img": Image.open(meta["image"]).convert("RGBA"), "ox": 0, "oy": 0,
        }
        planes.insert(0, base)

    print(f"  {len(planes)} planes, depth {planes[0]['depth']}..{max_depth}, "
          f"z {planes[-1]['z']:.2f}..{planes[0]['z']:.2f}", file=sys.stderr)

    if args.path:
        spec = json.loads(Path(args.path).read_text())
        keys, fps = spec["keys"], spec.get("fps", args.fps)
        duration = spec.get("duration", keys[-1]["t"])
    else:
        # The scroll's own journey: river to peaks, easing at both ends, with a
        # gentle pull-back so the near planes sweep past rather than crawl.
        fps, duration = args.fps, args.duration
        keys = [
            {"t": 0.0,          "x": 0.50, "y": 0.93, "z": 0.00,  "fov": 1.00},
            {"t": duration * .5, "x": 0.46, "y": 0.52, "z": -0.12, "fov": 1.02},
            {"t": duration,     "x": 0.52, "y": 0.10, "z": -0.22, "fov": 1.04},
        ]

    # fov 1.0 means NATIVE PIXELS at the middle depth — you are inside the
    # painting looking at brushwork, which is the whole reason for a 105MP
    # master. Framing the entire scroll instead made it a stamp in a field of
    # paper, because a 1:2.4 canvas fitted to 16:9 is mostly margin.
    f0 = args.z_near + (max_depth / 2.0) * args.z_step

    def screen_scale(z_rest, cam_z, fov):
        """Pixels per source pixel for a world point whose REST depth is z_rest.

        One global f0 means only the mid-depth plane is native size, so pushing
        planes apart in z visibly resizes them and the composition comes apart
        at frame zero. --plane-fit normalises each point by its own rest depth
        instead: zr/(zr-camZ) is exactly 1.0 at camZ=0 for every zr, so depth
        separation costs nothing at rest and every bit of it shows up as
        DIFFERENTIAL motion once the camera moves. That difference is the whole
        distinction between a zoom and a flight.
        """
        eff = z_rest - cam_z
        if eff <= 0.05:
            return None
        return fov * (z_rest / eff if args.plane_fit else f0 / eff)

    if args.fill == "black":
        bg = (0, 0, 0, 255)
    elif args.fill == "edge":
        bg = (0, 0, 0, 0)
    else:
        # The paper itself, sampled from a corner of the master's own tone, so
        # a gap reads as unpainted silk rather than as a hole.
        bg = (214, 203, 176, 255)

    n_frames = int(round(duration * fps))
    idx = list(range(0, n_frames, max(1, args.preview)))
    if args.stills:
        idx = [0, n_frames // 2, max(0, n_frames - 1)]
    print(f"  {len(idx)} frames @ {args.width}x{args.height}  {fps}fps  {duration}s", file=sys.stderr)

    living = json.loads(Path(args.living).read_text()) if args.living else {}
    if living:
        known = {p.get("name") for p in planes}
        for lname in living:
            if lname not in known:
                print(f"--living names unknown plane '{lname}' — ignored", file=sys.stderr)
        living = {k: v for k, v in living.items() if k in known}
        print(f"  living planes: {sorted(living)}", file=sys.stderr)
    living_cache = {}

    t0 = time.time()
    for n, i in enumerate(idx):
        t = i / fps
        c = sample(keys, t)
        camX, camY, camZ, fov = c["x"] * W_SRC, c["y"] * H_SRC, c.get("z", 0.0), c.get("fov", 1.0) or 1.0
        canvas = Image.new("RGBA", (args.width, args.height), bg)

        for p in planes:
            lv = living.get(p.get("name"))
            if lv:
                ti = (i // lv.get("on", 1)) % lv["n"]
                held = living_cache.get(p["name"])
                if held is None or held[0] != ti:
                    held = (ti, Image.open(
                        Path(lv["dir"]) / f"{ti:03d}.png").convert("RGBA"))
                    living_cache[p["name"]] = held   # one texture per plane
                p["img"] = held[1]
            eff = p["z"] - camZ
            if eff <= 0.05:
                continue                        # camera has passed through it

            tilt = tilts.get(p.get("name", ""), {})
            tx, ty = float(tilt.get("tiltX", 0.0)), float(tilt.get("tiltY", 0.0))
            if tx or ty:
                # ORIENTED PLANE. Four corners at four different depths, each
                # projected separately, then a homography maps the output quad
                # back to the layer. This is the whole difference between a
                # zoom and a flight: a fronto-parallel plane can only get
                # bigger, an oriented one turns as you pass it.
                iw, ih = p["img"].size
                ox, oy = p["ox"], p["oy"]
                xc, yc = ox + iw / 2.0, oy + ih / 2.0
                dst, src, ok = [], [], True
                for lx, ly in ((0, 0), (iw, 0), (iw, ih), (0, ih)):
                    wx, wy = ox + lx, oy + ly
                    # Rest depth of this corner. Under --plane-fit the corner is
                    # normalised by THIS value, so a tilted plane still lands on
                    # its painted rectangle at camZ=0 and only keystones as the
                    # camera moves — tilt costs nothing until it is earned.
                    zr = p["z"] + (wy - yc) * tx + (wx - xc) * ty
                    sc = screen_scale(zr, camZ, fov)
                    if sc is None:              # corner is behind the camera
                        ok = False
                        break
                    dst.append((args.width / 2.0 + (wx - camX) * sc,
                                args.height / 2.0 + (wy - camY) * sc))
                    src.append((lx, ly))
                if ok:
                    try:
                        coeffs = find_coeffs(dst, src)
                    except np.linalg.LinAlgError:
                        ok = False
                if ok:
                    canvas.alpha_composite(p["img"].transform(
                        (args.width, args.height), Image.PERSPECTIVE, coeffs,
                        resample=Image.BILINEAR))
                    continue
                # degenerate projection: fall through to the flat path

            s = screen_scale(p["z"], camZ, fov)
            if s is None or s <= 1e-6:
                continue
            # Inverse affine: for each OUTPUT pixel, which source pixel?
            #   u = (x - W/2)/s + camX - ox
            # Cost is O(output), so the master's size is irrelevant per frame.
            a = 1.0 / s
            cx = camX - (args.width / 2.0) / s - p["ox"]
            cy = camY - (args.height / 2.0) / s - p["oy"]
            warped = p["img"].transform(
                (args.width, args.height), Image.AFFINE, (a, 0, cx, 0, a, cy),
                resample=Image.BILINEAR,
            )
            canvas.alpha_composite(warped)

        canvas.convert("RGB").save(out / f"{i:05d}.png")
        if n % 10 == 0 or n == len(idx) - 1:
            el = time.time() - t0
            print(f"    {n + 1}/{len(idx)}  t={t:5.2f}s  {el / (n + 1):.2f}s/frame", file=sys.stderr)

    secs = time.time() - t0
    print(json.dumps({
        "tool": "render-parallax", "layers": str(lay), "out": str(out),
        "planes": len(planes), "frames": len(idx), "size": [args.width, args.height],
        "fps": fps, "duration": duration,
        "zNear": args.z_near, "zStep": args.z_step, "planeFit": bool(args.plane_fit),
        "zRange": [round(planes[-1]["z"], 4), round(planes[0]["z"], 4)],
        "fill": args.fill,
        "keys": keys,
        "seconds": round(secs, 1), "secondsPerFrame": round(secs / max(1, len(idx)), 3),
        "encode": f"ffmpeg -r {fps} -i {out}/%05d.png -c:v libx264 -crf 16 -pix_fmt yuv420p out.mp4",
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
