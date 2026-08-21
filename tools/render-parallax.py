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
  --relief PATH    per-plane SURFACE SHAPE, as {"plane-name": {"map": png,
                   "band": 0.05}} (map paths resolve against the JSON's own
                   dir). The map is centered grayscale — 128 sits ON the
                   card, bright is toward the camera — and each pixel of the
                   plane is re-projected at z = zr − (map−128)/127 · band/2.
                   This is the LDI hybrid: cards keep their completed edges,
                   surfaces gain continuous parallax WITHIN a card, so a
                   cliff face bulges as the camera passes instead of sliding
                   as a flat sheet. Displacement is identically zero at
                   camZ=0, so frame zero stays the painting pixel-for-pixel.
                   Off = old renders reproduce byte-identically.
  --relief-band F  default band (depth units across the full map) for relief
                   entries that do not set their own (default 0.05)
  --fill NAME      what shows through gaps: paper (default) | black | edge
  --preview N      render only every Nth frame, for a fast look
  --stills         write first/middle/last only, then stop

Camera path JSON:
  { "fps": 30, "duration": 12,
    "keys": [ {"t":0,  "x":0.5, "y":0.93, "z":0.0,  "fov":1.0},
              {"t":12, "x":0.5, "y":0.10, "z":-0.25,"fov":1.0} ] }
  Optional per key: rx, ry, rz — camera ROTATION in degrees (pitch, yaw,
  roll). Rotation shares the center of projection, so it adds NO new
  parallax — it is the head turning, not moving. Use small values (≤2°)
  layered over a translation for the floating-camera feel; keep them 0 at
  t=0 so frame zero stays the painting pixel-for-pixel.
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
import math
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
            return {f: smoothstep(k0.get(f, 0.0), k1.get(f, 0.0), u)
                    for f in ("x", "y", "z", "fov", "rx", "ry", "rz")}
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
    ap.add_argument("--truck", type=float, default=0.0,
                    help="MULTIPLANE TRUCK. 0 = every plane translates at the "
                         "same rate, which is a PAN over a flat sheet no matter "
                         "how many planes the stack has (measured: z-step 0.30 "
                         "and z-step 0.0 render byte-identically on a traverse). "
                         "1 = fully physical, near planes traverse z_ref/z times "
                         "faster than far ones. 0.15-0.35 is the useful band on "
                         "this stack, whose z spans 1.0..3.7.")
    ap.add_argument("--truck-max", type=float, default=36.0,
                    help="ceiling on the truck's relative displacement, in "
                         "OUTPUT px, soft-clamped with tanh. The rate "
                         "difference ACCUMULATES over a move, and these planes "
                         "are cut from one painting rather than painted as "
                         "separate cels -- measured 2026-08-21, an uncapped "
                         "0.25 truck over a 10s rise put the nearest plane ~500px "
                         "out of register with the farthest and tore the picture "
                         "along the cut lines. Parallax is a VELOCITY cue, so "
                         "ramp at full rate and then saturate. 0 = uncapped.")
    ap.add_argument("--no-base", action="store_true")
    ap.add_argument("--geometry")
    ap.add_argument("--living",
                    help='JSON map {plane-name: {"dir": textures dir of '
                         '%%03d.png sized like the plane, "n": count, "on": '
                         'hold}} — the plane\'s texture is swapped per frame '
                         '(index = frame//on %% n) so its ink moves while its '
                         'depth, footprint, and tilt stay authored. Or '
                         '{plane-name: {"patches": [{"dir","box":[x,y],"n",'
                         '"on"}, ...]}} to paste small cycles onto the plane\'s '
                         'own texture — use this when the moving ink is a small '
                         'part of a big plane. Off = '
                         'every plane static, old renders reproduce.')
    ap.add_argument("--relief")
    ap.add_argument("--relief-band", type=float, default=0.05)
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
        p["orig"] = img                 # kept unmodified: --living patches paste onto it
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

    # PER-PLANE RELIEF (the LDI hybrid). Each entry carries an "L" map the
    # size of its plane; per frame the map rides the plane's own transform
    # into screen space, then the composited card is radially remapped about
    # the camera axis by r = scale(zr+dz)/scale(zr). Since scale depends on
    # camZ, r == 1 everywhere when camZ == 0: the null is structural, not a
    # promise. cv2 is imported only if relief is actually requested.
    relief = {}
    if args.relief:
        rj = Path(args.relief)
        for rname, rspec in json.loads(rj.read_text()).items():
            if not any(p.get("name") == rname for p in planes):
                print(f"--relief names unknown plane '{rname}' — ignored",
                      file=sys.stderr)
                continue
            rimg = Image.open((rj.parent / rspec["map"])).convert("L")
            pl = next(p for p in planes if p.get("name") == rname)
            if rimg.size != pl["img"].size:
                print(f"relief map for '{rname}' is {rimg.size}, plane is "
                      f"{pl['img'].size} — resizing", file=sys.stderr)
                rimg = rimg.resize(pl["img"].size, Image.BILINEAR)
            relief[rname] = {"img": rimg,
                             "band": float(rspec.get("band", args.relief_band))}
        if relief:
            import cv2
            xgrid, ygrid = np.meshgrid(
                np.arange(args.width, dtype=np.float32),
                np.arange(args.height, dtype=np.float32))
            print(f"  relief planes: {sorted(relief)}", file=sys.stderr)

    # MULTIPLANE TRUCK (Disney, 1937). A plane stack only produces parallax on
    # a traverse if the planes translate at DIFFERENT RATES -- near faster than
    # far. --plane-fit deliberately equalises every plane's SCALE at rest, which
    # is right, but the sampling offset was equalised with it, so thirteen
    # planes moved as one sheet and the whole stack contributed nothing. Proven
    # by the null: collapsing every plane to one depth changed 0 of 2,073,600
    # pixels. Rate is what carries a truck; scale is what carries a dolly.
    #
    # Anchored at the path's FIRST key so the composition is exactly as painted
    # at t=0 and the separation is earned by the move, never present at rest.
    _pz = sorted(p["z"] for p in planes)
    z_ref = _pz[len(_pz) // 2]
    camX0, camY0 = keys[0]["x"] * W_SRC, keys[0]["y"] * H_SRC
    if args.truck:
        print(f"  multiplane truck {args.truck:g}: rate "
              f"{1 + args.truck * (z_ref / _pz[0] - 1):.2f}x near .. "
              f"{1 + args.truck * (z_ref / _pz[-1] - 1):.2f}x far "
              f"(z_ref {z_ref:.2f})", file=sys.stderr)

    t0 = time.time()
    for n, i in enumerate(idx):
        t = i / fps
        c = sample(keys, t)
        camX, camY, camZ, fov = c["x"] * W_SRC, c["y"] * H_SRC, c.get("z", 0.0), c.get("fov", 1.0) or 1.0

        # CAMERA ROTATION (rx pitch, ry yaw, rz roll — DEGREES in path keys).
        # Rotation is depth-independent: it moves every plane by the same
        # screen-space homography H = K Rᵀ K⁻¹, so it creates NO new parallax
        # (same center of projection — turning the head, not moving it). Its
        # value is the keystone + drift it adds ON TOP of a translation.
        # The focal is fov·width px (~53° lens at fov 1); zooming multiplies
        # the focal, so the same physical turn moves a zoomed frame further,
        # as a real lens does. All three zero = H is None = old renders
        # reproduce byte-identically.
        rx, ry, rz = (math.radians(c.get(k) or 0.0) for k in ("rx", "ry", "rz"))
        H_rot = None
        if rx or ry or rz:
            fpx = fov * args.width
            K = np.array([[fpx, 0, args.width / 2.0],
                          [0, fpx, args.height / 2.0],
                          [0, 0, 1.0]])
            cx_, sx_ = math.cos(rx), math.sin(rx)
            cy_, sy_ = math.cos(ry), math.sin(ry)
            cz_, sz_ = math.cos(rz), math.sin(rz)
            Rx = np.array([[1, 0, 0], [0, cx_, -sx_], [0, sx_, cx_]])
            Ry = np.array([[cy_, 0, sy_], [0, 1, 0], [-sy_, 0, cy_]])
            Rz = np.array([[cz_, -sz_, 0], [sz_, cz_, 0], [0, 0, 1]])
            H_rot = K @ (Rz @ Rx @ Ry).T @ np.linalg.inv(K)

        def rot_pt(x, y):
            if H_rot is None:
                return (x, y)
            v = H_rot @ (x, y, 1.0)
            return (v[0] / v[2], v[1] / v[2])

        canvas = Image.new("RGBA", (args.width, args.height), bg)

        for p in planes:
            lv = living.get(p.get("name"))
            if lv:
                # Two forms. "dir" = a full-plane texture cycle (the z1 form:
                # every drawing is the whole plane re-rendered). "patches" = a
                # list of small cycles pasted onto the plane's own texture at
                # their box, which is what the upper zones need: there the
                # moving water is 0.2-1.2% of a plate-sized plane, so a
                # full-plane cycle would be ~40MB a drawing for ink that lives
                # in a 220x415 window. Patches carry the plane's own alpha, so
                # pasting them cannot change the plane's footprint.
                if "patches" in lv:
                    key = tuple((i // q.get("on", 1)) % q["n"] for q in lv["patches"])
                    held = living_cache.get(p["name"])
                    if held is None or held[0] != key:
                        # Patches are opened, not cached: a drawing index is
                        # used for `on` consecutive frames and then not again
                        # for a whole cycle, so a cache only holds memory. A
                        # zone can carry a hundred canopy patches; decoded,
                        # that is over a gigabyte for no reuse.
                        comp = p["orig"].copy()
                        for q, ti in zip(lv["patches"], key):
                            comp.paste(Image.open(
                                Path(q["dir"]) / f"{ti:03d}.png").convert("RGBA"),
                                tuple(q["box"]))
                        held = (key, comp)
                        living_cache[p["name"]] = held
                    p["img"] = held[1]
                else:
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

            # This plane's own share of the truck. w > 1 for planes nearer than
            # z_ref, w < 1 for planes further away.
            if args.truck:
                w_tr = 1.0 + args.truck * (z_ref / p["z"] - 1.0)
                dx, dy = (camX - camX0) * (w_tr - 1.0), (camY - camY0) * (w_tr - 1.0)
                if args.truck_max > 0:
                    # SATURATE. The rate difference accumulates, so on a long
                    # traverse an unbounded truck slides the planes hundreds of
                    # px apart and the cut lines open as paper. Depth is read
                    # from differential VELOCITY at the start of a move, not
                    # from where the planes end up, so ramp at full rate and
                    # then asymptote. tanh is used because it is exactly linear
                    # near zero -- no knee, no visible moment of clamping.
                    cap = args.truck_max / max(fov, 1e-6)   # output px -> source px
                    dx = cap * math.tanh(dx / cap)
                    dy = cap * math.tanh(dy / cap)
                pcamX, pcamY = camX + dx, camY + dy
            else:
                pcamX, pcamY = camX, camY

            rl = relief.get(p.get("name"))
            warped = None

            tilt = tilts.get(p.get("name", ""), {})
            tx, ty = float(tilt.get("tiltX", 0.0)), float(tilt.get("tiltY", 0.0))
            if tx or ty or H_rot is not None:
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
                    dst.append(rot_pt(args.width / 2.0 + (wx - pcamX) * sc,
                                      args.height / 2.0 + (wy - pcamY) * sc))
                    src.append((lx, ly))
                if ok:
                    try:
                        coeffs = find_coeffs(dst, src)
                    except np.linalg.LinAlgError:
                        ok = False
                if ok:
                    warped = p["img"].transform(
                        (args.width, args.height), Image.PERSPECTIVE, coeffs,
                        resample=Image.BILINEAR)
                    if rl is not None:
                        rel_scr = rl["img"].transform(
                            (args.width, args.height), Image.PERSPECTIVE,
                            coeffs, resample=Image.BILINEAR, fillcolor=128)
                # degenerate projection: fall through to the flat path

            if warped is None:
                s = screen_scale(p["z"], camZ, fov)
                if s is None or s <= 1e-6:
                    continue
                # Inverse affine: for each OUTPUT pixel, which source pixel?
                #   u = (x - W/2)/s + camX - ox
                # Cost is O(output), so the master's size is irrelevant per frame.
                a = 1.0 / s
                cx = pcamX - (args.width / 2.0) / s - p["ox"]
                cy = pcamY - (args.height / 2.0) / s - p["oy"]
                warped = p["img"].transform(
                    (args.width, args.height), Image.AFFINE, (a, 0, cx, 0, a, cy),
                    resample=Image.BILINEAR,
                )
                if rl is not None:
                    rel_scr = rl["img"].transform(
                        (args.width, args.height), Image.AFFINE,
                        (a, 0, cx, 0, a, cy), resample=Image.BILINEAR,
                        fillcolor=128)

            if rl is not None and abs(camZ) > 1e-9:
                # RELIEF REMAP. A point whose depth is zr+dz instead of zr
                # projects at C + (q_flat - C)·r, with r the ratio of its
                # screen scales — so the whole correction is one radial remap
                # about the camera axis C. dz is sampled AT THE DESTINATION
                # (the standard small-displacement approximation; measured
                # magnitudes here are single-digit pixels). Bright map = near
                # = smaller z. camZ == 0 → r ≡ 1 → this block is skipped and
                # frame zero stays the painting by construction. Tilt's own
                # per-pixel zr variation is second-order in r and ignored.
                dz = (128.0 - np.asarray(rel_scr, dtype=np.float32)) / 127.0 \
                    * (rl["band"] / 2.0)
                zr = p["z"]
                den = np.maximum(zr + dz - camZ, 0.05)
                if args.plane_fit:
                    ratio = ((zr + dz) * (zr - camZ)) / (zr * den)
                else:
                    ratio = (zr - camZ) / den
                crx, cry = rot_pt(args.width / 2.0, args.height / 2.0)
                xs = ((xgrid - crx) / ratio + crx).astype(np.float32)
                ys = ((ygrid - cry) / ratio + cry).astype(np.float32)
                remapped = cv2.remap(
                    np.asarray(warped), xs, ys, cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
                warped = Image.fromarray(remapped, "RGBA")

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
        "zNear": args.z_near, "zStep": args.z_step, "planeFit": bool(args.plane_fit), "truck": args.truck,
        "truckMax": args.truck_max,
        "zRange": [round(planes[-1]["z"], 4), round(planes[0]["z"], 4)],
        "fill": args.fill,
        "keys": keys,
        "seconds": round(secs, 1), "secondsPerFrame": round(secs / max(1, len(idx)), 3),
        "encode": f"ffmpeg -r {fps} -i {out}/%05d.png -c:v libx264 -crf 16 -pix_fmt yuv420p out.mp4",
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
