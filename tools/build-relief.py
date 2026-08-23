#!/usr/bin/env python3
"""media-tools — build-relief: a plane stack → within-plane surface shape. One job.

It writes relief maps and a manifest. It does not cut planes, author depth,
move a camera or render — `render-parallax --relief` consumes what this makes.

WHAT RELIEF IS. A cut plane is a flat card: it can only get bigger as the camera
approaches, which is a zoom, not a surface. Relief gives each card its own
within-card shape, so a rock face bulges toward the lens and the plane reads as
something the camera is passing rather than a sticker at a distance.

WHAT IT IS NOT, and this distinction is the whole reason it works: **scene depth
is NOT authored here.** Monocular depth on this material is measurably dead
(49-88% row-explained — see knowledge/depth-is-authored.md). What a depth model
IS good at is LOCAL shape from shading inside one card, so the scene-scale
component is removed BY CONSTRUCTION: relief = raw depth minus a heavy gaussian
of itself. A flat ramp across a plane high-passes to exactly zero. The blur is
masked-normalized (blur(raw*a)/blur(a)) so paper background never mixes in — an
unmasked blur rings at the card boundary, i.e. displacement exactly where edges
must stay pinned.

WHAT THIS IS NOT FOR, AND WHAT IS:
  estimate-depth.py   a depth map of a WHOLE IMAGE. Correct for photographs;
                      on an authored plane stack its scene-scale component is
                      the measured failure. This tool calls it per-plane and
                      throws that component away.
  compose-depth.py    combining authored plane order into one map.
  render-parallax.py  consumes --relief. It never builds one.

BAND IS COMPUTED, NOT GUESSED. Displacement sensitivity for a plane at rest
depth zr under a dolly camZ goes as camZ/(zr*(zr-camZ)), so equal screen
movement needs band proportional to zr*(zr-camZ)/camZ -- roughly 20x more for a
far wall than a foreground rock, which is why one global number cannot work.

But equal displacement is NOT what looks right, and that is measured rather than
assumed: physics wants an 18x ratio between z1's wall (zr 3.7) and its
foreground rock (zr 1.0), while the two bands Ryan approved by eye differ by
7.5x. So the band takes that sensitivity to the power `--compensation`, default
0.697, which is the exponent FIT to those two approved points and reproduces
both to three places. 1.0 would equalise displacement and overshoot; a far plane
moving less is part of how it reads as far.

ROLES. Rock and wall surfaces take relief; water, figures and structures never
do — a bulging bridge is a broken bridge. Foliage is EXCLUDED BY DEFAULT and
`--include-foliage` turns it on: in ink painting a canopy is separate sprays
over bare ground, not a surface, so a bulge there can read as a blob. That was
z1's original judgement and it is preserved as a flag rather than a hardcode.

usage:
  build-relief.py --layers DIR --out DIR [--z-step F] [--z-near F]
                  [--band-ref NAME=VALUE] [--band-max F] [--dolly F]
                  [--only A,B] [--include-foliage] [--sheet PATH]

  --layers DIR     a plane stack (layers.json + layers/*.png)
  --out DIR        relief/<plane>.png + relief.json land here
  --z-step F       must match the renderer's (default 0.30)
  --z-near F       distance to the nearest plane (default 1.0)
  --band-ref N=V   calibrate the band constant so plane N gets band V
                   (default foreground-rock-mass=0.08, proven on z1)
  --band-max F     clamp (default 0.8; z1's walls were hand-set to 0.6)
  --dolly F        the representative camera travel bands are sized for (0.30)
  --only A,B       just these planes, bypassing role selection
  --include-foliage  let canopy/tree planes take relief too
  --sheet PATH     write the evidence sheet [crop | raw | relief] here

JSON on stdout. Progress on stderr.

example:
  build-relief.py --layers jobs/wang-meng/journey/z3w/layers-filled \
      --out jobs/wang-meng/journey/z3w --sheet jobs/wang-meng/evidence/relief-z3w.png
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
PAPER = (214, 203, 176)

SURFACE = ("rock", "cliff", "wall", "hill", "mass", "ledge", "bank", "knoll",
           "shelf", "ground", "path", "peak", "ridge", "slope", "boulder")
FOLIAGE = ("tree", "pine", "canopy", "foliage", "maple", "leaf", "grove", "bamboo")
NEVER = ("water", "fall", "stream", "pool", "rapid", "river", "figure", "bridge",
         "deer", "boat", "hall", "court", "fence", "roof", "hut", "ge")


def role(name, include_foliage):
    """Match WHOLE hyphen tokens, never substrings. Measured 2026-08-22: bare
    "ge" (Ge Hong) matched inside "gorge-wall-right" and "resting-ledge" and
    skipped two real rock surfaces, one of them already proven by eye."""
    toks = set(name.lower().replace("_", "-").split("-"))
    hit = lambda ks: any(t == k or t.rstrip("s") == k for t in toks for k in ks)
    if hit(NEVER):
        return None
    if hit(FOLIAGE):
        return "foliage" if include_foliage else None
    if hit(SURFACE):
        return "surface"
    return None


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--layers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--z-step", type=float, default=0.30)
    ap.add_argument("--z-near", type=float, default=1.0)
    ap.add_argument("--band-ref", default="foreground-rock-mass=0.08")
    ap.add_argument("--compensation", type=float, default=0.697,
                    help="how much of the depth falloff the band cancels. 1.0 = "
                         "full (every plane displaces equally). 0.697 is FIT to "
                         "the two z1 bands Ryan approved by eye -- 0.08 at zr 1.0 "
                         "and 0.6 at zr 3.7 -- and reproduces both exactly.")
    ap.add_argument("--band-max", type=float, default=0.8)
    ap.add_argument("--dolly", type=float, default=0.30)
    ap.add_argument("--only")
    ap.add_argument("--include-foliage", action="store_true")
    ap.add_argument("--sheet")
    a = ap.parse_args()

    REPO = Path(__file__).resolve().parent.parent
    L = Path(a.layers)
    meta = json.loads((L / "layers.json").read_text())
    planes = [p for p in meta["planeList"] if p.get("layer")]
    if not planes:
        print("no planes with layers", file=sys.stderr); return 2

    depths = [int(p["depth"]) for p in planes]
    maxd = max(depths)
    zr_of = lambda d: a.z_near + (maxd - d) * a.z_step
    # Full compensation (exponent 1.0) equalises displacement across depth and
    # measurably OVERSHOOTS: physics wants a 18x band ratio between zr 3.7 and
    # zr 1.0, while the two bands approved by eye differ by 7.5x. A far wall is
    # supposed to move less -- that is part of reading as far. The exponent is
    # the fit, not a fudge: 0.697 reproduces both approved values to 3 places.
    sens = lambda zr: (zr * (zr - a.dolly) / a.dolly) ** a.compensation

    refname, refval = a.band_ref.split("=")
    refplane = next((p for p in planes if p["name"] == refname), None)
    k = float(refval) / sens(zr_of(refplane["depth"])) if refplane else \
        float(refval) / sens(a.z_near)

    if a.only:
        want = [p for p in planes if p["name"] in set(a.only.split(","))]
    else:
        want = [p for p in planes if role(p["name"], a.include_foliage)]

    OUT = Path(a.out); (OUT / "relief").mkdir(parents=True, exist_ok=True)
    work = OUT / "relief" / "_work"; work.mkdir(exist_ok=True)

    manifest, rows, skipped = {}, [], [p["name"] for p in planes if p not in want]
    for p in want:
        name = p["name"]
        zr = zr_of(p["depth"])
        band = round(min(k * sens(zr), a.band_max), 4)
        rgba = Image.open(L / p["layer"]).convert("RGBA")
        w, h = rgba.size
        flat = Image.new("RGB", (w, h), PAPER); flat.paste(rgba, (0, 0), rgba)
        crop = work / f"{name}-crop.png"; flat.save(crop)

        raw_p = work / f"{name}-raw.npy"
        if not raw_p.exists():
            # same interpreter we are running under -- estimate-depth needs
            # torch, so whichever venv launched this one is the right one.
            r = subprocess.run([sys.executable,
                                str(REPO / "tools/estimate-depth.py"),
                                "--image", str(crop), "--raw", str(raw_p),
                                "--out", str(work / f"{name}-depth.png"),
                                "--max-side", str(max(w, h))],
                               capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stderr, file=sys.stderr); return 1

        raw = np.load(raw_p).astype(np.float32)
        if raw.shape != (h, w):
            raw = cv2.resize(raw, (w, h), interpolation=cv2.INTER_LINEAR)

        sigma = min(w, h) / 4.0
        alpha = np.asarray(rgba.split()[3]).astype(np.float32) / 255.0
        low = cv2.GaussianBlur(raw * alpha, (0, 0), sigma) / \
              np.maximum(cv2.GaussianBlur(alpha, (0, 0), sigma), 1e-4)
        hp = (raw - low) * alpha
        vals = hp[alpha > 0.5]
        scale = 3.0 * vals.std() if vals.size else 1.0
        rel8 = np.round(np.clip(hp / max(scale, 1e-6), -1, 1) * 127 + 128).astype(np.uint8)
        Image.fromarray(rel8, "L").save(OUT / "relief" / f"{name}.png")
        manifest[name] = {"map": f"relief/{name}.png", "band": band,
                          "sigmaPx": round(sigma, 1), "clipStd": 3.0,
                          "zRest": round(zr, 3), "size": [w, h]}
        print(f"  {name:28} zr={zr:.2f} band={band:.3f} {w}x{h}", file=sys.stderr)

        if a.sheet:
            th = 300
            sc = lambda im: im.resize((max(1, int(im.width * th / im.height)), th))
            rawv = (255 * (raw - raw.min()) / max(float(np.ptp(raw)), 1e-6)).astype(np.uint8)
            ims = [sc(flat), sc(Image.fromarray(rawv, "L").convert("RGB")),
                   sc(Image.fromarray(rel8, "L").convert("RGB"))]
            row = Image.new("RGB", (sum(i.width for i in ims) + 20, th), (30, 30, 30))
            x = 0
            for im in ims: row.paste(im, (x, 0)); x += im.width + 10
            rows.append((f"{name}   zr={zr:.2f} band={band:.3f}   [crop | raw depth | relief]", row))

    (OUT / "relief.json").write_text(json.dumps(manifest, indent=1))

    if a.sheet and rows:
        sw = max(r.width for _, r in rows); sh = sum(r.height + 26 for _, r in rows)
        sheet = Image.new("RGB", (sw, sh), (30, 30, 30)); d = ImageDraw.Draw(sheet)
        y = 0
        for label, row in rows:
            d.text((6, y + 5), label, fill=(230, 220, 190))
            sheet.paste(row, (0, y + 26)); y += row.height + 26
        Path(a.sheet).parent.mkdir(parents=True, exist_ok=True)
        sheet.save(a.sheet)

    print(json.dumps({"tool": "build-relief", "layers": str(L),
                      "relief": str(OUT / "relief.json"), "planes": len(manifest),
                      "ofPlanes": len(planes), "skipped": skipped,
                      "bandConstant": round(k, 6), "sheet": a.sheet}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
