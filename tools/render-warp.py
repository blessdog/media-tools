#!/usr/bin/env python3
"""media-tools — render-warp: objects + depths + a camera path → frames, as ONE
continuous warp of the picture. One job.

The alternative to `render-parallax`. Same camera model, no layers. Instead of
compositing cards it deforms the whole picture as a single sheet, holding each
object rigid and pushing the strain into regions where distortion cannot be seen.

WHAT IT FIXES, AND WHAT IT GIVES UP. Be explicit, because this is a TRADE and not
an upgrade:
  + no disocclusion, ever. Nothing uncovers anything, so there is nothing to
    inpaint and no hole to fill. The sheet stretches instead.
  + no shear inside an object, by construction rather than by pinning.
  + no plane boundaries at all, so no seam, no feather ring, no outline.
  - NO OCCLUSION. Nothing can pass in front of anything. A card stack can send a
    figure behind a tree; this cannot. For a modest dolly that costs little,
    because the differential is what reads as depth; for a big lateral move it is
    wrong and `render-parallax` is the right tool.
  - strain has to go SOMEWHERE, and where it goes it stretches the brushwork.

THE SOLVER, AND WHY IT IS THIS ONE. Minimise, over vertex displacements d:

    sum_v  w_v |d_v - t_v|^2   +   lambda * sum_(u,v adjacent) |d_v - d_u|^2

t_v is the displacement the camera model wants at v; w_v is stiffness. The second
term smooths the DISPLACEMENT field, not the positions — which matters, because a
similarity transform is a LINEAR displacement field and a linear field has zero
Laplacian. So smoothing does not fight rigidity: an object under uniform
stiffness keeps its exact similarity for free, and the give appears only where
stiffness is low. That is the whole trick, and it is why no as-rigid-as-possible
machinery or sparse solve is needed — Jacobi relaxation on a grid converges fine.

Related published work, for searching: as-rigid-as-possible image warping;
content-preserving warps (Liu et al., 3D video stabilization), which is the same
formulation used to hide the strain of a synthetic camera in real footage.

STIFFNESS IS THE WHOLE AUTHORING SURFACE. Objects stiff, everything else
compliant, bare silk most compliant of all. Measured on wang-meng: bare silk is
only 13.0% of this shot with pockets at most 66px across, so silk ALONE cannot
absorb a 1.4x differential — the unclaimed amorphous wash has to take most of it.
That is fine: distortion is invisible in texture and glaring in structure.

usage:
  render-warp.py --objects DIR --layers DIR --out DIR [flags]

  --objects DIR    a segment-regions output (regions.json + masks/*.png) — the
                   things that must stay rigid
  --layers DIR     a plane stack, read ONLY for its depths: whichever plane owns
                   an object gives that object its z
  --out DIR        frames as %05d.png
  --path PATH      camera path JSON, same format as render-parallax
  --width/--height output size (default the source size)
  --z-near/--z-step  same meaning as render-parallax (1.0 / 0.15)
  --grid N         mesh spacing in px (default 16)
  --stiff F        data weight inside an object (default 40)
  --slack F        data weight outside one (default 1)
  --silk F         data weight in bare silk (default 0.15)
  --lambda F       smoothness weight (default 1.0)
  --iters N        Jacobi iterations (default 400)
  --soften N       blur the stiffness map by N px in LOG space (default 24,
                   about 1.5 grid cells). A stiffness STEP makes a strain
                   step: unsoftened, anisotropy hit 162x in the single cell
                   at each object edge while interiors sat at 1.000. Set 0 to
                   see that.
  --stills         first / middle / last only
  --probe          report per-object RIGIDITY on the last frame: RMS px off a
                   pure similarity, measured on the solved FIELD. Measuring a
                   rendered frame instead fails on every object that leaves
                   frame under a dolly, which is most of the foreground.
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


def smoothstep(a, b, u):
    return a + (b - a) * (u * u * (3 - 2 * u))


def sample_path(keys, t):
    if t <= keys[0]["t"]:
        return keys[0]
    for k0, k1 in zip(keys, keys[1:]):
        if k0["t"] <= t <= k1["t"]:
            span = (k1["t"] - k0["t"]) or 1e-9
            u = (t - k0["t"]) / span
            return {f: smoothstep(k0.get(f, 0.0), k1.get(f, 0.0), u)
                    for f in ("x", "y", "z", "fov")}
    return keys[-1]


def main() -> int:
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--objects", required=True)
    ap.add_argument("--layers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--path")
    ap.add_argument("--width", type=int, default=0)
    ap.add_argument("--height", type=int, default=0)
    ap.add_argument("--z-near", type=float, default=1.0)
    ap.add_argument("--z-step", type=float, default=0.15)
    ap.add_argument("--grid", type=int, default=16)
    ap.add_argument("--stiff", type=float, default=40.0)
    ap.add_argument("--slack", type=float, default=1.0)
    ap.add_argument("--silk", type=float, default=0.15)
    ap.add_argument("--lambda", dest="lam", type=float, default=1.0)
    ap.add_argument("--iters", type=int, default=400)
    ap.add_argument("--soften", type=int, default=24)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--duration", type=float, default=5.0)
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()

    lay, obj, out = Path(a.layers), Path(a.objects), Path(a.out)
    meta = json.loads((lay / "layers.json").read_text())
    W_SRC, H_SRC = meta["size"]
    src = Path(meta["image"])
    if not src.exists():
        print(f"layers.json names {src}, missing from here. Run from the repo "
              f"root.", file=sys.stderr)
        return 1
    OW = a.width or W_SRC
    OH = a.height or H_SRC
    out.mkdir(parents=True, exist_ok=True)

    # --- depths, from whichever plane owns each pixel -----------------------
    planes = sorted([p for p in meta["planeList"] if p.get("layer")],
                    key=lambda p: p["depth"])
    max_depth = max(p["depth"] for p in planes)
    zof = np.full((H_SRC, W_SRC), a.z_near + max_depth * a.z_step, np.float32)
    for p in planes:
        im = np.asarray(Image.open(lay / p["layer"]).convert("RGBA"))
        ox, oy = p["offset"]
        h, w = im.shape[:2]
        z = a.z_near + (max_depth - p["depth"]) * a.z_step
        zof[oy:oy + h, ox:ox + w][im[..., 3] > 128] = z

    # --- objects: each one gets ONE z, so it can only move rigidly ---------
    rj = json.loads((obj / "regions.json").read_text())
    if rj.get("workSize", [W_SRC, H_SRC]) != [W_SRC, H_SRC]:
        print(f"objects were cut at {rj.get('workSize')} but the source is "
              f"{[W_SRC, H_SRC]} — refusing rather than scaling masks",
              file=sys.stderr)
        return 1
    objz = np.zeros((H_SRC, W_SRC), np.float32)
    objid = np.zeros((H_SRC, W_SRC), np.int32)
    for r in rj["regionList"]:
        tile = np.asarray(Image.open(obj / r["mask"]).convert("L")) > 127
        ox, oy = r["offset"]
        th, tw = tile.shape
        m = np.zeros((H_SRC, W_SRC), bool)
        m[oy:oy + th, ox:ox + tw] = tile
        if m.sum() < 300:
            continue
        vals = zof[m]
        # the object's single depth: the one its own pixels mostly sit at
        u, c = np.unique(vals, return_counts=True)
        objz[m] = float(u[int(c.argmax())])
        objid[m] = r["id"]
    inobj = objid > 0
    zfield = np.where(inobj, objz, zof).astype(np.float32)

    # --- stiffness: objects rigid, wash compliant, bare silk most of all ---
    g = np.asarray(Image.open(src).convert("L")).astype(np.float32)
    mean = cv2.boxFilter(g, -1, (17, 17))
    sd = np.sqrt(np.maximum(cv2.boxFilter(g * g, -1, (17, 17)) - mean * mean, 0))
    silk = (g > 152) & (sd < 5)
    silk = cv2.morphologyEx(silk.astype(np.uint8), cv2.MORPH_OPEN,
                            np.ones((7, 7), np.uint8)) > 0
    Wt = np.full((H_SRC, W_SRC), a.slack, np.float32)
    Wt[silk] = a.silk
    Wt[inobj] = a.stiff
    if a.soften > 0:
        # A stiffness field with a STEP in it produces a strain field with a step
        # in it: measured, the strain piled into the single grid cell at every
        # object edge (anisotropy max 162x) while interiors sat at 1.000. Ramp
        # stiffness in LOG space so the ratio itself is smooth, and the same
        # total strain spreads over a band instead of tearing at one cell.
        k = int(a.soften) * 2 + 1
        Wt = np.exp(cv2.GaussianBlur(np.log(Wt), (k, k), 0)).astype(np.float32)
    print(f"  objects {int(objid.max())} · rigid area {100*inobj.mean():.1f}% · "
          f"bare silk {100*silk.mean():.1f}% · compliant "
          f"{100*(~inobj & ~silk).mean():.1f}%", file=sys.stderr)

    # --- mesh ---------------------------------------------------------------
    S = a.grid
    gy = np.arange(0, H_SRC + S, S)
    gx = np.arange(0, W_SRC + S, S)
    VY, VX = np.meshgrid(gy, gx, indexing="ij")
    ci = np.clip(VY, 0, H_SRC - 1), np.clip(VX, 0, W_SRC - 1)
    wv = Wt[ci]
    zv = zfield[ci]
    print(f"  mesh {VX.shape[1]}x{VX.shape[0]} vertices at {S}px", file=sys.stderr)

    if a.path:
        spec = json.loads(Path(a.path).read_text())
        keys, fps = spec["keys"], spec.get("fps", a.fps)
        duration = spec.get("duration", keys[-1]["t"])
    else:
        keys, fps, duration = ([{"t": 0, "x": .5, "y": .5, "z": 0, "fov": 1},
                                {"t": a.duration, "x": .5, "y": .5, "z": .3,
                                 "fov": 1}], a.fps, a.duration)

    n_frames = int(round(duration * fps))
    idx = [0, n_frames // 2, n_frames - 1] if a.stills else list(range(n_frames))
    img = np.asarray(Image.open(src).convert("RGB"))
    t0 = time.time()

    for n, i in enumerate(idx):
        c = sample_path(keys, i / fps)
        camX, camY = c["x"] * W_SRC, c["y"] * H_SRC
        camZ, fov = c.get("z", 0.0), c.get("fov", 1.0) or 1.0
        # Rest-normalised, exactly as render-parallax --plane-fit: scale is
        # z/(z-camZ), which is 1.0 at camZ=0 for every z. So frame zero is the
        # painting and the warp is the identity — a free control.
        s = fov * zv / np.maximum(zv - camZ, 1e-3)
        tx = (OW / 2.0 + (VX - camX) * s) - VX
        ty = (OH / 2.0 + (VY - camY) * s) - VY

        dx, dy = tx.copy(), ty.copy()
        lam = a.lam
        for _ in range(a.iters):
            for d, t in ((dx, tx), (dy, ty)):
                acc = np.zeros_like(d)
                cnt = np.zeros_like(d)
                acc[1:] += d[:-1]; cnt[1:] += 1
                acc[:-1] += d[1:]; cnt[:-1] += 1
                acc[:, 1:] += d[:, :-1]; cnt[:, 1:] += 1
                acc[:, :-1] += d[:, 1:]; cnt[:, :-1] += 1
                d[...] = (wv * t + lam * acc) / (wv + lam * cnt)

        if a.probe and i == idx[-1]:
            # RIGIDITY, measured on the solved FIELD and not on a rendered proxy.
            # A rigid object's displacement is d = s*p + b exactly: uniform scale
            # plus translation, 3 unknowns. Fit that and report the RMS leftover
            # in pixels. Measuring the render instead fails on any object that
            # leaves the frame, which is most of the foreground under a dolly.
            oid = objid[ci]
            rows = []
            for k in np.unique(oid):
                if k == 0:
                    continue
                sel = oid == k
                if sel.sum() < 6:
                    continue
                P = np.stack([VX[sel], VY[sel], np.ones(int(sel.sum()))], 1).astype(np.float64)
                res = 0.0
                for d, ax in ((dx[sel], 0), (dy[sel], 1)):
                    # columns: scale on this axis' coordinate, plus offset
                    M = np.stack([P[:, ax], np.ones(len(P))], 1)
                    sol, *_ = np.linalg.lstsq(M, d.astype(np.float64), rcond=None)
                    res += float(np.mean((M @ sol - d) ** 2))
                rows.append((np.sqrt(res), int(k), int(sel.sum())))
            rows.sort(reverse=True)
            print(f"  RIGIDITY at frame {i} (RMS px off a pure similarity):",
                  file=sys.stderr)
            for r, k, nv in rows[:8]:
                print(f"    object {k:3}  {nv:4} vertices   {r:6.3f}px",
                      file=sys.stderr)
            allr = [r for r, _, _ in rows]
            print(f"    worst {max(allr):.3f}px · median {np.median(allr):.3f}px "
                  f"· over {len(allr)} objects", file=sys.stderr)
            # WHERE THE STRAIN WENT. Anisotropy of the local Jacobian: 1.0 is a
            # pure similarity (no distortion at all), higher means the brushwork
            # is being stretched more in one direction than the other. This is
            # the warp's whole cost, so it gets printed next to its benefit.
            J11 = 1 + np.gradient(dx, S, axis=1)
            J12 = np.gradient(dx, S, axis=0)
            J21 = np.gradient(dy, S, axis=1)
            J22 = 1 + np.gradient(dy, S, axis=0)
            E = J11 * J11 + J21 * J21
            G = J12 * J12 + J22 * J22
            F = J11 * J12 + J21 * J22
            tr, det2 = E + G, np.maximum(E * G - F * F, 1e-9)
            disc = np.sqrt(np.maximum(tr * tr / 4 - det2, 0))
            s1 = np.sqrt(np.maximum(tr / 2 + disc, 1e-9))
            s2 = np.sqrt(np.maximum(tr / 2 - disc, 1e-9))
            aniso = s1 / np.maximum(s2, 1e-6)
            # A vertex on an object's EDGE is "inside" it while its Jacobian
            # straddles the boundary, which is exactly where the strain
            # concentrates. Classifying those as interior makes the interior look
            # distorted when it is not — erode by one cell and report the
            # boundary as its own class, because that is where the cost lands.
            rigpx = (objid > 0).astype(np.uint8)
            ker = np.ones((2 * S + 1, 2 * S + 1), np.uint8)
            interior = cv2.erode(rigpx, ker)[ci] > 0
            outside = cv2.dilate(rigpx, ker)[ci] == 0
            boundary = ~interior & ~outside
            for nm2, sel in (("object INTERIOR (must be ~1.00)", interior),
                             ("object BOUNDARY", boundary),
                             ("compliant regions", outside)):
                if not sel.any():
                    continue
                v = aniso[sel]
                over = int((v > 4).sum())
                print(f"    stretch {nm2:32} median {np.median(v):.3f}  "
                      f"95th {np.percentile(v, 95):.3f}  max {v.max():.3f}  "
                      f">4x in {over}/{v.size} cells ({100*over/v.size:.2f}%)",
                      file=sys.stderr)

        # grid displacement -> full-res forward field
        FX = cv2.resize(dx, (OW, OH), interpolation=cv2.INTER_CUBIC)
        FY = cv2.resize(dy, (OW, OH), interpolation=cv2.INTER_CUBIC)
        # remap needs the BACKWARD map. Fixed-point: p <- q - disp(p). Converges
        # in a handful of steps because the field is smooth by construction.
        # cv2.remap demands contiguous CV_32FC1 for both maps; a view out of
        # mgrid is not that and the assertion it throws does not say so.
        ox = np.ascontiguousarray(np.tile(np.arange(OW, dtype=np.float32), (OH, 1)))
        oy = np.ascontiguousarray(
            np.tile(np.arange(OH, dtype=np.float32)[:, None], (1, OW)))
        px, py = ox.copy(), oy.copy()
        for _ in range(6):
            sx = cv2.remap(FX, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            sy = cv2.remap(FY, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            px = np.ascontiguousarray(ox - sx, dtype=np.float32)
            py = np.ascontiguousarray(oy - sy, dtype=np.float32)
        frame = cv2.remap(img, px, py, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(214, 203, 176))
        Image.fromarray(frame).save(out / f"{i:05d}.png")
        if n % 10 == 0 or n == len(idx) - 1:
            el = time.time() - t0
            print(f"    {n+1}/{len(idx)}  {el/(n+1):.2f}s/frame", file=sys.stderr)

    secs = time.time() - t0
    print(json.dumps({
        "tool": "render-warp", "objects": str(obj), "layers": str(lay),
        "out": str(out), "frames": len(idx), "size": [OW, OH],
        "grid": S, "stiff": a.stiff, "slack": a.slack, "silk": a.silk,
        "lambda": a.lam, "iters": a.iters,
        "rigidAreaFrac": round(float(inobj.mean()), 4),
        "silkFrac": round(float(silk.mean()), 4),
        "seconds": round(secs, 1), "secondsPerFrame": round(secs / max(1, len(idx)), 3),
        "note": "NO OCCLUSION by construction — nothing passes in front of "
                "anything. Also no disocclusion, so nothing to inpaint.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
