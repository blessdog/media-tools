#!/usr/bin/env python3
"""Build LIVING PATCH CYCLES for a zone world's planes.

Why this exists (Ryan, 2026-08-20, after five days of camera moves over still
ink): only z1 ever had living cycles. z3w-z6w -- every waterfall, cascade and
stream above the bridge -- were STILL IMAGES being flown past. `film/
compile-flight.py` now refuses to render those legs (the LIVING GATE), so the
zones need cycles before the film can be built again.

The shape of the problem is different from z1 and that is why this is a new
tool rather than build-plane-cycles.py. In z1 the water WAS a plane, so the
cycle could be a full-plane texture swap. In the upper zones the water is
0.2-1.2% of a plate-sized plane it shares with a whole cliff wall, and it is
split across several planes at once (w-midstream is 98% on left-cliff-wall and
24% on upper-stream-rocks, because the rocks sit in front of it). So:

  1. region masks come from the NATIVE masks already audited in living/native
     (seals sealed, the porter's basket weave excluded) -- downscaled by k into
     plate space rather than re-cut, so the audit carries over.
  2. every plane holding >= --min-frac of a region gets its own cycle, cut from
     that plane's OWN filled texture, masked by region AND the plane's alpha.
     Whichever plane ends up in front, the water it shows is moving.
  3. the cycle is stored as a PATCH (region bbox + pad) with the plane's alpha
     baked in, and render-parallax --living pastes it onto the plane texture.
     A full-plane cycle here would be ~40MB a drawing for a 220x415 window.

Motion params are the class winners in regions.json, in 720-space -- and that
is the right space, because a zone plate is master/2.34 which is the scale the
cel water was proven at (STATE 2026-08-19 night, scale law 3).

  --stage masks     region -> plate-space masks + a tinted evidence overlay
  --stage cycle     animate every (region, plane) pair  [--region ID --plane N]
  --stage register  write living/living-<zone>.json for compile-flight
  --stage audit     what-moved heat map -> living/evidence-living-<zone>.png
"""
import argparse, json, os, subprocess, sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).parent          # jobs/wang-meng/living
JOB = HERE.parent                     # jobs/wang-meng
ROOT = JOB.parents[1]                 # media-tools


# ── TECHNIQUE DISPATCH ───────────────────────────────────────────────────────
# One entry per LIVE `procedure` claim in knowledge/, keyed by its claim id.
# The class in regions.json names the id; check-routing.py refuses to build a
# class whose claim is superseded or refuted, and cross-checks this table
# against the store in both directions (`--implements`).
#
# Before 2026-08-20 there was no table: one hardcoded call to animate-strokes
# and no branch to take, which is why the store recording
# foliage-motion-by-displacement as SUPERSEDED could not stop 14 regions from
# still rendering through it. The technique has to be DATA before a type system
# can have an opinion about it.
#
# Each entry returns a LIST of argv steps to run in order -- a route, matching
# the claim's `route:` field, rather than a single command.

def _water_motion(wd, cls, pivot, cx0, cy0):
    """knowledge/water-motion.md — displace thin marks in place, keep=tophat."""
    cmd = ["python3", str(ROOT / "tools/animate-strokes.py"),
           "--image", str(wd / "plate.png"), "--masks", str(wd / "mask"),
           "--out", str(wd / "preview.mp4"),
           "--out-frames", str(wd / "drawings"),
           "--frames", str(cls.get("drawings", 36) * cls.get("on", 2)),
           "--on", str(cls.get("on", 2)),
           "--field", cls["field"], "--mode", cls["mode"], "--keep", cls["keep"]]
    for flag in ("wobble", "drift", "wavelength", "angle", "stiffness",
                 "scale", "boil", "max-thick"):
        if flag in cls:
            cmd += [f"--{flag}", str(cls[flag])]
    if pivot is not None:
        cmd += ["--pivot", f"{pivot[0]-cx0:.1f},{pivot[1]-cy0:.1f}"]
    return [cmd]


def _foliage_motion(wd, cls, pivot, cx0, cy0, exclude=None):
    """knowledge/foliage-motion.md — cut-out cards hinged over a clean plate.

    Two steps, because the ground behind a leaf has to exist before the leaf
    can move off it. clean-plate synthesises it ONCE with shiftmap patch
    synthesis; the alternative (animate-strokes --mode lift) fills the hole with
    cv2.INPAINT_TELEA, which is the averaging inpainter that produced the mush.

    `exclude` is EVERY foliage pixel in the crop, not just this region's --
    see knowledge/clean-plate-donor-scope.md. Shiftmap copies the best-matching
    patch from elsewhere in the image, so removing one canopy from a crop full
    of canopies makes another canopy the best match, and it gets copied in. It
    invented two masses of orange autumn leaves where a blue-green pine was.
    A masked pixel cannot be a donor, so masking the whole class leaves only
    ground -- which is the only thing actually behind a tree.
    """
    clean = wd / "clean.png"
    plate_step = ["python3", str(ROOT / "tools/clean-plate.py"),
                  "--image", str(wd / "plate.png"),
                  "--masks", str(exclude or (wd / "mask")),
                  "--out", str(clean),
                  "--grow", str(cls.get("cleanGrow", 4)),
                  "--method", cls.get("cleanMethod", "shiftmap")]
    hinge = ["python3", str(ROOT / "tools/hinge-foliage.py"),
             *([] if cls.get("under") == "hold" else ["--plate", str(clean)]),
             "--source", str(wd / "plate.png"),
             "--cards", str(wd / "mask"),
             "--out", str(wd / "drawings"), "--preview", str(wd / "preview.mp4"),
             "--frames", str(cls.get("drawings", 96) * cls.get("on", 2)),
             "--on", str(cls.get("on", 2)),
             "--swing", str(cls.get("swing", 15)),
             "--flutter", str(cls.get("flutter", 0.35)),
             "--angle", str(cls.get("angle", 8)),
             "--gust", str(cls.get("gust", "0.10,0.08,0.22")),
             "--gust-travel", str(cls.get("gust-travel", 1500)),
             "--gust-rest", str(cls.get("gust-rest", 0.15)),
             "--min-px", str(cls.get("minPx", 80)),
             # LEAVES HOLD UNDER LEAVES. `hold` leaves the source intact beneath
             # the cards, so a swing reveals the original leaf strokes instead of
             # a synthesised plate -- and with no hole to fill, a region no longer
             # needs a clean plate at all, which is what kept coverage at 8
             # regions. knowledge/leaves-hold-under-leaves.md
             "--under", str(cls.get("under", "clean")),
             *(["--leaf-mask", str(wd / "leaf-mask.png")]
               if cls.get("leafMask") and (wd / "leaf-mask.png").exists() else []),
             *(["--leaf-marks",
                "--mark-swing", str(cls.get("markSwing", 3.0)),
                "--mark-rate", str(cls.get("markRate", 3.0)),
                "--mark-twinkle", str(cls.get("markTwinkle", 0.25)),
                "--mark-shift", str(cls.get("markShift", 0.6)),
                "--min-mark", str(cls.get("minMark", 10))]
               if cls.get("leafMarks") else []),
             *(["--semantic", str(wd / "semantic"),
                "--semantic-mode", cls.get("semanticMode", "veto")]
               if cls.get("semantic") else []),
             "--branch-radius", str(cls.get("branchRadius", "auto")),
             "--branch-ratio", str(cls.get("branchRatio", 0.55)),
             "--attach-max", str(cls.get("attachMax", 14)),
             "--pivots", str(wd / "pivots.png"),
             "--ink-offset", str(cls.get("inkOffset", 0.11)),
             "--ink-close", str(cls.get("inkClose", 1))]
    hinge += ["--from-ink"] if cls.get("fromInk", True) else ["--whole-mask"]
    # UNDER:HOLD MAKES THE CLEAN PLATE DEAD WEIGHT. hinge-foliage never reads
    # --plate in that mode -- the source stays intact beneath the cards -- and
    # synthesising a plate per region was the expensive step that kept foliage at
    # 8 authored regions. Skipping it is what makes 114 catalogued regions
    # affordable. The path is still passed so the tool's contract is unchanged.
    if cls.get("under") == "hold":
        return [hinge]
    return [plate_step, hinge]


def _figure_motion(wd, cls, pivot, cx0, cy0):
    """knowledge/figure-motion.md — swing AUTHORED cards; never invent a motion.

    The gate this replaces refused outright, because generating a figure cycle
    is a fabrication decision. Ryan gave the verdict 2026-08-21 ("start on the
    figures", after "we can invent a little bit of ink... as long as it looks
    hand-drawn"), so what stands guard now is narrower and better: EVERY card
    must be a mask a human authored, named in regions.json. Nothing here decides
    which pixels are a sleeve.

    RESAMPLE THE STENCIL, NOT THE BRUSHWORK. The cards are cut at master
    resolution (SAM on a k=1.0 crop) while this zone's plate is at k=K. A mask
    is a stencil and survives being resized; the finished drawings would carry
    Wang Meng's ink through a second resample, so the cycle is REBUILT at plate
    scale here rather than pasted in from living/cycles/.
    """
    spec = (cls.get("cards") or {}).get(wd.name)
    if not spec:
        sys.exit(f"figure-motion: no cards authored for '{wd.name}'. Add "
                 f"classes.figure.cards['{wd.name}'] to regions.json naming the "
                 f"mask dir, the pivots file and which part swings. A figure "
                 f"cycle is never generated from nothing "
                 f"(knowledge/figure-motion.md).")

    src_master = spec["masterOrigin"]          # where the authored crop sits
    md = ROOT / spec["masks"]
    meta = json.loads((md / "layers.json").read_text())
    piv = json.loads((ROOT / spec["pivots"]).read_text())
    only = spec.get("only")

    cards = wd / "cards"
    (cards / "masks").mkdir(parents=True, exist_ok=True)
    plane_list, pivots_out = [], {}
    for pl in meta["planeList"]:
        if only and pl["name"] != only:
            continue
        m = Image.open(md / "masks" / f"{pl['n']:03d}.png").convert("L")
        # master px -> plate px -> this region's crop
        nw, nh = max(1, round(m.width / K)), max(1, round(m.height / K))
        m = m.resize((nw, nh), Image.LANCZOS)
        ox = round((src_master[0] + pl["offset"][0] - X0) / K) - cx0
        oy = round((src_master[1] + pl["offset"][1] - Y0) / K) - cy0
        m.save(cards / "masks" / f"{pl['n']:03d}.png")
        plane_list.append({"n": pl["n"], "name": pl["name"], "offset": [ox, oy]})
        if pl["name"] in piv:
            px, py = piv[pl["name"]]["pivot"]
            pivots_out[pl["name"]] = {"pivot": [
                round((src_master[0] + px - X0) / K - cx0, 1),
                round((src_master[1] + py - Y0) / K - cy0, 1)]}
    if not plane_list:
        sys.exit(f"figure-motion: '{only}' is not a plane in {spec['masks']}")
    (cards / "layers.json").write_text(json.dumps(
        {"tool": "build-zone-living", "note": "authored cards resampled from "
         f"master into {wd.name}'s crop at k={K}", "planeList": plane_list}))
    (cards / "pivots.json").write_text(json.dumps(pivots_out, indent=1))

    # THE GROUND BEHIND THE CARD, first. Same two-step shape as foliage: a card
    # that rotates over its own ink smears at the trailing edge. Only this
    # card's footprint is synthesised -- everywhere else the painting stands.
    return [["python3", str(ROOT / "tools/clean-plate.py"),
             "--image", str(wd / "plate.png"), "--masks", str(cards),
             *(["--only", only] if only else []),
             "--method", "shiftmap", "--grow", "2",
             "--out", str(wd / "clean.png")],
            ["python3", str(ROOT / "tools/swing-card.py"),
             "--plate", str(wd / "clean.png"),
             "--source", str(wd / "plate.png"),
             "--masks", str(cards), "--pivots", str(cards / "pivots.json"),
             *(["--only", only] if only else []),
             "--swing", str(spec.get("swing", cls.get("swing", 5.0))),
             "--gust", str(cls.get("gust", "0.10,0.08,0.22")),
             "--gust-rest", str(cls.get("gustRest", 0.15)),
             "--frames", str(cls.get("drawings", 48) * cls.get("on", 2)),
             "--on", str(cls.get("on", 2)),
             "--prefix", "dr-", "--out", str(wd / "drawings")]]


TECHNIQUES = {
    "water-motion":   _water_motion,
    "foliage-motion": _foliage_motion,
    "figure-motion":  _figure_motion,
}

# techniques whose clean plate must exclude every pixel of their own class
CLASS_WIDE_EXCLUDE = {"foliage-motion"}

if "--techniques" in sys.argv:
    # so check-routing.py can compare the store against what is IMPLEMENTED,
    # instead of the two drifting apart silently.
    print(json.dumps(sorted(TECHNIQUES)))
    sys.exit(0)

ap = argparse.ArgumentParser()
ap.add_argument("--zone", required=True)
ap.add_argument("--stage", required=True,
                choices=["masks", "cycle", "register", "audit"])
ap.add_argument("--region", default=None, help="restrict to one region id")
ap.add_argument("--plane", default=None, help="restrict to one plane name")
ap.add_argument("--canopy-win", type=int, default=21,
                help="gust: window (plate px) for the local ink-density read "
                     "that finds a canopy inside its authored box")
ap.add_argument("--canopy-dens", type=float, default=0.40,
                help="gust: ink fraction above which a window is canopy")
ap.add_argument("--canopy-compact", type=float, default=0.70,
                help="gust: max ink-boundary per ink area; leaves are a solid "
                     "body of ink (0.25-0.47 measured), cliff is separate "
                     "strokes (1.1-1.4)")
ap.add_argument("--canopy-grow", type=int, default=120,
                help="gust: px the authored box is grown by for the density "
                     "read, so a canopy straddling its edge comes out whole")
ap.add_argument("--canopy-min", type=int, default=1500,
                help="gust: smallest canopy worth its own cantilever, plate px")
ap.add_argument("--classes", default="wave,fall",
                help="region classes to build (default: the water ones)")
ap.add_argument("--min-frac", type=float, default=0.02,
                help="skip a (region, plane) pair holding less of the region "
                     "than this -- a few hundred stray px is a mask feather, "
                     "not water this plane owns")
ap.add_argument("--min-px", type=int, default=500)
ap.add_argument("--pad", type=int, default=64,
                help="px of context around the region bbox in the patch, so "
                     "the displacement field and its feather have room to die "
                     "out inside the patch instead of at its edge")
ap.add_argument("--drawings", type=int, default=36)
ap.add_argument("--keep-work", action="store_true",
                help="keep the full-frame intermediate drawings (ab-cycle.py "
                     "needs them; the renderer never does)")
a = ap.parse_args()

Z = JOB / "journey" / a.zone
plate_meta = json.loads((Z / "plate.json").read_text())
X0, Y0, X1, Y1 = plate_meta["masterBox"]
K = plate_meta["masterPxPerRegionPx"]
PW, PH = plate_meta["size"]
LAY = Z / "layers-filled"
layers = json.loads((LAY / "layers.json").read_text())
REGF = HERE / "regions.json"
REG = json.loads(REGF.read_text())
CLASSES = REG["classes"]                     # SSOT for the motion parameters

# THE STORE GATES THE BUILD. Not a lint step somebody remembers to run: if a
# class routes to a technique that has been superseded or refuted, this build
# does not start. That is the whole difference between a knowledge store and a
# folder of notes.
_chk = subprocess.run(["python3", str(Path.home() / ".claude/knowledge/bin/check-routing.py"),
                       "--config", str(REGF), "--knowledge", str(ROOT / "knowledge"),
                       "--implements", "-"],
                      input=json.dumps(sorted(TECHNIQUES)), capture_output=True, text=True)
if _chk.returncode != 0:
    sys.exit("ROUTING GATE — regions.json routes to a technique the knowledge store "
             "does not believe:\n" + _chk.stderr)

POLYS = json.loads((HERE / "living-polys.json").read_text())
WANT = set(a.classes.split(","))
MASKD = Z / "living-masks"
WORK = Z / "living-work"
OUT = Z / "living"


def to_plate(pts):
    return [((mx - X0) / K, (my - Y0) / K) for mx, my in pts]


def regions_here():
    """Authored polygons whose plate-space footprint lands inside this zone."""
    out = []
    for r in POLYS["polys"]:
        if r["class"] not in WANT:
            continue
        if a.region and r["id"] != a.region:
            continue
        xs = [x for x, _ in to_plate(r["points"])]
        ys = [y for _, y in to_plate(r["points"])]
        if min(xs) >= PW or max(xs) <= 0 or min(ys) >= PH or max(ys) <= 0:
            continue
        out.append(r)
    return out


def dark_accent_mask(poly_mask, plate_rgb, cls):
    """The canopy on a DISTANT ridge: the darkest accents, and nothing else.

    The density+compactness read below is tuned on the compound canopies and
    it does not survive the trip up the scroll. Measured on s-summit-crest-left
    (living/_probe-canopy-*.png, _probe-master-*.png): the tuned numbers claim
    36-46% of the crop, and three attempted fixes all failed to shrink it onto
    the trees --

      * a tighter window and a harder ink threshold (still the whole shoulder),
      * high-pass texture energy, at plate res AND at master res (0.64% ->
        0.63% of plate: no effect),
      * local contrast at master res (44.8% -> 29%, still the shoulder).

    The mechanism they all miss: up here Wang Meng's 牛毛皴 covers rock and
    forest alike, so no local texture statistic separates them -- the shoulder
    really is a dense, compact, high-contrast field of ink. What DOES separate
    them is plain tone. The trees at this distance are painted as the darkest
    accents on a mid-tone slope: the darkest 2-3% of the box lands on tree
    mass and on the crest ribbon and nowhere else (living/evidence-summit-darkness-map.png,
    living/evidence-summit-dark-accents.png). So take the darkest N%, close it into coherent
    masses, drop the specks, and grow it a little for the warp's feather.

    Conservative by construction -- the paler pines on the left of that same
    crest are not claimed. Coverage is widened after a verdict on the look,
    never before.
    """
    grow = cv2.dilate(poly_mask, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * a.canopy_grow + 1,) * 2))
    sel = grow > 128
    v = cv2.cvtColor(plate_rgb, cv2.COLOR_RGB2HSV)[..., 2].astype(np.float32) / 255
    t = float(np.percentile(v[sel], cls.get("accentPct", 3.0)))
    m = ((v < t) & sel).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (cls.get("accentClose", 9),) * 2))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    inside = poly_mask > 128
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] < cls.get("accentMin", 110):
            continue
        cy, cx = int(round(cen[i][1])), int(round(cen[i][0]))
        if inside[cy, cx]:
            keep[lab == i] = 1
    g = cls.get("accentGrow", 5)
    if g:
        keep = cv2.dilate(keep, cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (g,) * 2))
    return (keep * 255).astype(np.uint8)


_CATALOGUE_CACHE = {}


def catalogue_mask(poly_mask, cls):
    """Card territory = the authored polygon AND the catalogue's own leaf mask.

    THE THIRD WHERE-DECIDER. the-catalogue-decides-what-is-foliage says the
    catalogue answers WHAT, SAM answers WHERE, and the ink cut answers WHICH.
    canopy_mask below is a FOURTH answer to WHERE -- a density+compactness
    texture read -- and it runs AFTER the first two have already answered
    pixel-exactly. Measured 2026-08-24 across all five zones: the authored
    polygons enclose 902,771 px of catalogued leaf ink and canopy_mask hands
    299,858 of it to the cutter, i.e. it discards two thirds of the leaf we had
    already located. That is the whole of the foliage deficit Ryan has been
    describing for three days as "you still haven't animated the foliage".

    So where a catalogue mask exists, IT is the territory. Density is the
    fallback for a region the catalogue never saw, which is what it was written
    for -- it predates the catalogue entirely.

    Closed before use: the catalogue mask is per-STROKE, and a card wants a
    bushel. Closing joins the marks of one spray into one body without
    reaching across the gap to the next tree, which is the same reason
    hinge-foliage cuts cards from connected components of ink.
    """
    fm = cls.get("leafMask")
    if not fm:
        return None
    fmp = (HERE / fm) if not Path(fm).is_absolute() else Path(fm)
    if not fmp.exists():
        return None
    if fmp not in _CATALOGUE_CACHE:
        big = Image.open(fmp).convert("L")
        sub = big.crop((int(X0), int(Y0), int(X0 + PW * K), int(Y0 + PH * K)))
        _CATALOGUE_CACHE[fmp] = np.array(sub.resize((PW, PH), Image.NEAREST)) > 127
    leaf = _CATALOGUE_CACHE[fmp]
    m = ((poly_mask > 128) & leaf).astype(np.uint8)
    c = int(cls.get("catalogueClose", 11))
    if c:
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (c, c)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] >= int(cls.get("catalogueMin", 60)):
            keep[lab == i] = 1
    g = int(cls.get("catalogueGrow", 3))
    if g:
        keep = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (g, g)))
    return (keep * 255).astype(np.uint8)


def canopy_mask(poly_mask, plate_rgb, cls):
    """The canopy inside an authored box, by local ink DENSITY.

    Colour cannot do this and that is measured twice: only 0.9% of leaf ink is
    green/cyan, cliff ink is MORE saturated than leaf ink, and in Lab the
    compound canopies sit 1-3 units from bare cliff on both a and b. What DOES
    separate them is texture -- a leaf mass is a dense field of repeated dot or
    outline strokes, while a 皴 cliff is sparse hatching. Read the ink fraction
    in a window and the canopies come out whole (living/evidence-canopy-density.png).

    Density alone is not enough on its own, though: run it over the WHOLE plate
    and it claims 36% of the painting, because a dark wash band and a shadowed
    cliff face are also "a lot of ink" (living/evidence-canopy-density-unbounded.png). So the
    authored box still decides WHERE to look. The analysis runs on the box
    GROWN by --canopy-grow and then keeps only components whose centroid is
    inside the original box: a canopy that straddles the edge comes out whole
    instead of being sliced along a straight line, which is what a warp would
    have torn.
    """
    if cls.get("canopyRule") == "catalogue":
        m = catalogue_mask(poly_mask, cls)
        if m is not None:
            return m
        print("    canopyRule=catalogue but no leafMask on disk -- "
              "falling back to density", file=sys.stderr)
    if cls.get("canopyRule") == "dark-accent":
        return dark_accent_mask(poly_mask, plate_rgb, cls)
    grow = cv2.dilate(poly_mask, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * a.canopy_grow + 1,) * 2))
    sel = grow > 128
    v = cv2.cvtColor(plate_rgb, cv2.COLOR_RGB2HSV)[..., 2].astype(np.float32) / 255
    ground = float(np.percentile(v[sel], 75))
    ink = ((v < ground - 0.08) & sel).astype(np.float32)
    dens = cv2.blur(ink, (a.canopy_win, a.canopy_win))
    # AND the ink has to be COMPACT. Density alone still swallows the dark
    # cliff bands next to a canopy, because a shadowed 皴 face is also a lot of
    # ink. A leaf mass is a solid body of ink, a cliff is many separate
    # strokes, so boundary-per-ink tells them apart: measured on z3w, leaf
    # canopy 0.25 and the great-trees knoll 0.47, against cliff wash 1.14 and
    # bare cliff 1.37.
    edge = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_GRADIENT,
                            np.ones((3, 3), np.uint8)).astype(np.float32)
    compact = cv2.blur(edge, (a.canopy_win, a.canopy_win)) / np.maximum(dens, 1e-6)
    m = ((dens > a.canopy_dens) & (compact < a.canopy_compact) & sel).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    inside = poly_mask > 128
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] < a.canopy_min:
            continue
        cx, cy = int(round(cen[i][0])), int(round(cen[i][1]))
        if 0 <= cy < inside.shape[0] and 0 <= cx < inside.shape[1] and inside[cy, cx]:
            keep[lab == i] = 1
    return (keep * 255).astype(np.uint8)


def plate_mask(rid):
    """Region mask in full-plate space, uint8 0/255."""
    return np.array(Image.open(MASKD / f"{rid}.png").convert("L"))


# ---------------------------------------------------------------- masks -----
if a.stage == "masks":
    from PIL import ImageDraw
    MASKD.mkdir(parents=True, exist_ok=True)
    plate = Image.open(Z / "plate.png").convert("RGB")
    over = plate.copy()
    idxf = MASKD / "index.json"
    index = json.loads(idxf.read_text()) if idxf.exists() else {}
    # SELF-HEAL. This index is a build CACHE, and a cache that carries a stale
    # copy of a region's class is a third place the class lives -- which is how
    # 13 summit polys survived their own revert. Reconcile against the poly list
    # on every run: refresh every entry's class, drop ids no longer authored.
    _live = {q["id"]: q["class"] for q in POLYS["polys"]}
    for _k in [k for k in index if k not in _live]:
        del index[_k]
    # RECONCILE AGAINST THE DIRECTORY TOO, not just the poly list. The index is
    # a cache of what is ON DISK and nothing invalidated it when a mask png went
    # away: z3w's index claimed 17 regions while 4 pngs existed, and the overlay
    # loop below -- which reads EVERY entry -- died on the first ghost. An index
    # entry with no file is not a region, it is a memory of one.
    for _k in [k for k in index if not (MASKD / f"{k}.png").exists()]:
        print(f"    index: {_k} has no mask png -- dropping the ghost entry",
              file=sys.stderr)
        del index[_k]
    for _k, _v in index.items():
        if isinstance(_v, dict) and _v.get("class") != _live[_k]:
            print(f"    index: {_k} class {_v.get('class')} -> {_live[_k]}", file=sys.stderr)
            _v["class"] = _live[_k]
    for r in regions_here():
        m = Image.new("L", (PW, PH), 0)
        d = ImageDraw.Draw(m)
        d.polygon(to_plate(r["points"]), fill=255)
        for ex in POLYS.get("excludes", []):
            if ex["forId"] == r["id"]:
                d.polygon(to_plate(ex["points"]), fill=0)
        canvas = np.array(m)
        if CLASSES[r["class"]].get("perCanopy"):
            canvas = canopy_mask(canvas, np.array(plate), CLASSES[r["class"]])
        if not canvas.any():
            continue
        Image.fromarray(canvas).save(MASKD / f"{r['id']}.png")
        ys, xs = np.nonzero(canvas)
        cov = int((canvas > 128).sum())
        index[r["id"]] = {"class": r["class"], "px": cov,
                          "pctOfPlate": round(100 * cov / (PW * PH), 3),
                          "plateBox": [int(xs.min()), int(ys.min()),
                                       int(xs.max()) + 1, int(ys.max()) + 1]}
        print(f"{r['id']:20s} {r['class']:5s} {cov:8d}px "
              f"({index[r['id']]['pctOfPlate']}% of plate)", file=sys.stderr)
        tint = Image.new("RGB", plate.size,
                         (30, 90, 200) if r["class"] in ("wave", "fall") else (200, 90, 30))
        over = Image.composite(Image.blend(over, tint, 0.5), over,
                               Image.fromarray(canvas))
    idxf.write_text(json.dumps(index, indent=1))
    # the overlay shows EVERY mask the zone carries, not just the classes this
    # run touched -- an evidence sheet that hides half the living layer is worse
    # than none
    for rid, meta in index.items():
        mm = np.array(Image.open(MASKD / f"{rid}.png"))
        tint = Image.new("RGB", plate.size,
                         (30, 90, 200) if meta["class"] in ("wave", "fall") else (40, 190, 90))
        over = Image.composite(Image.blend(over, tint, 0.5), over, Image.fromarray(mm))
    s_ = 1400 / max(over.size)
    over.resize((int(over.width * s_), int(over.height * s_))).save(
        HERE / f"evidence-masks-{a.zone}.png")
    print(json.dumps({"zone": a.zone, "regions": index}, indent=1))

# ---------------------------------------------------------------- cycle -----
if a.stage == "cycle":
    OUT.mkdir(parents=True, exist_ok=True)
    plate = Image.open(Z / "plate.png").convert("RGB")

    # WHO OWNS A PIXEL. layers.json is sorted farthest-first, so the plane that
    # is actually SEEN at a pixel is the LAST one in paint order with alpha
    # there. This matters more than it sounds: a plane's filled texture is only
    # real painting where nothing nearer covers it -- everywhere else it is
    # disocclusion fill, and over the midstream pool that fill is smeared
    # streaks where the ripple arcs used to be (evidence:
    # living/evidence-fill-vs-plate.png, master | plate | left-cliff-wall).
    # Animating the fill would move garbage. So each water pixel is animated by
    # exactly one plane: the one that shows it.
    order = sorted(layers["planeList"], key=lambda q: q["depth"])
    alphas, vis = {}, {}
    for q in order:
        tex = Image.open(LAY / q["layer"]).convert("RGBA")
        A = np.zeros((PH, PW), bool)
        ox, oy = q["offset"]
        al = np.array(tex.split()[3]) > 128
        h_, w_ = al.shape
        A[oy:oy + h_, ox:ox + w_] = al[:PH - oy, :PW - ox]
        alphas[q["name"]] = A
    covered = np.zeros((PH, PW), bool)
    for q in reversed(order):                       # nearest first
        vis[q["name"]] = alphas[q["name"]] & ~covered
        covered |= alphas[q["name"]]

    # UNITS OF WORK. Water is one unit per body: the whole surface shares one
    # travelling wave. Foliage is one unit per CANOPY, because sway is a
    # cantilever about a pivot -- swinging six trees about one distant pivot is
    # the decal tell animate-strokes exists to avoid -- so each connected
    # canopy gets its own crop, its own pivot at the foot of its own mass, and
    # its own run. The gust envelope still travels across all of them together,
    # since the delay is computed from position along the wind.
    units = []
    for r in regions_here():
        cls = CLASSES[r["class"]]
        tech = cls.get("technique")
        if tech in (None, "none"):
            print(f"--- {r['id']}: technique {tech!r} "
                  f"(retired by {cls.get('retired-by','?')}), skipped", file=sys.stderr)
            continue
        if not (MASKD / f"{r['id']}.png").exists():
            continue          # the mask stage found nothing of this body here
        rm = plate_mask(r["id"]) > 128
        # hinge-foliage cuts its OWN cards from the ink inside the region and
        # delays each one by its position along the wind, so splitting the
        # region here would break the travelling gust into per-canopy islands.
        if tech != "foliage-motion" and cls.get("perCanopy"):
            n, lab, st, cen = cv2.connectedComponentsWithStats(rm.astype(np.uint8), 8)
            for i in range(1, n):
                if st[i, 4] < a.canopy_min:
                    continue
                cm = lab == i
                ys_, xs_ = np.nonzero(cm)
                pivot = (float(xs_[ys_ > ys_.max() - 6].mean()), float(ys_.max()))
                units.append((f"{r['id']}-{i:02d}", r, cm, pivot))
        else:
            units.append((r["id"], r, rm, None))

    built = []
    for uid, r, rm, pivot in units:
        tot = int(rm.sum())
        cls = dict(CLASSES[r["class"]])
        ys, xs = np.nonzero(rm)
        cx0, cy0 = int(max(0, xs.min() - a.pad)), int(max(0, ys.min() - a.pad))
        cx1, cy1 = int(min(PW, xs.max() + 1 + a.pad)), int(min(PH, ys.max() + 1 + a.pad))

        # ONE animation per water body, cut from the plate, so the displacement
        # field is continuous across the plane seams that cross it.
        wd = WORK / uid
        (wd / "mask" / "masks").mkdir(parents=True, exist_ok=True)
        plate.crop((cx0, cy0, cx1, cy1)).save(wd / "plate.png")
        # THE MODEL'S MASK, CROPPED HERE. A master-px foliage mask (VLM catalogue
        # box -> refine-mask-sam -> composite-tile-masks) is one mask for the whole
        # painting, and this is the only place that knows how to cut a region out
        # of it: master = masterBox origin + plate px * K. Doing it in the tool
        # would make the tool depend on the zone's geometry, which is the caller's.
        fm = cls.get("leafMask")
        if fm:
            fmp = (HERE / fm) if not Path(fm).is_absolute() else Path(fm)
            if fmp.exists():
                big = Image.open(fmp).convert("L")
                sub = big.crop((int(X0 + cx0 * K), int(Y0 + cy0 * K),
                                int(X0 + cx1 * K), int(Y0 + cy1 * K)))
                sub = sub.resize((cx1 - cx0, cy1 - cy0), Image.NEAREST)
                sub.save(wd / "leaf-mask.png")
                keep = np.array(sub) > 127
                print(f"    leaf-mask: model keeps {100*keep.mean():.1f}% of the crop",
                      file=sys.stderr)
            else:
                sys.exit(f"leafMask {fmp} not found -- build it with "
                         f"jobs/wang-meng/catalogue/sam-all-tiles.sh, or unset "
                         f"classes.{r['class']}.leafMask. Falling back silently to "
                         f"the colour gate would hide which perception produced the "
                         f"cards, and that is the one thing the record must show.")
        Image.fromarray((rm[cy0:cy1, cx0:cx1] * 255).astype(np.uint8)).save(
            wd / "mask" / "masks" / "001.png")
        (wd / "mask" / "layers.json").write_text(json.dumps({
            "tool": "build-zone-living", "size": [cx1 - cx0, cy1 - cy0],
            "planeList": [{"n": 1, "name": uid, "offset": [0, 0]}]}))
        print(f"=== {uid} ({r['class']} / {cls['technique']}): {tot}px, crop "
              f"{cx1-cx0}x{cy1-cy0} at {cx0},{cy0}", file=sys.stderr)
        # DONOR SCOPE. clean-plate may only copy from material that is NOT the
        # class being removed (knowledge/clean-plate-donor-scope.md), so every
        # region of this class overlapping the crop becomes a hole, and only the
        # animated one becomes cards.
        extra = None
        if cls["technique"] in CLASS_WIDE_EXCLUDE:
            same = np.zeros((PH, PW), bool)
            # NOT regions_here(): that honours --region, and the whole point is
            # the SIBLINGS. Building one region must not change what the clean
            # plate is allowed to copy from.
            for o in POLYS["polys"]:
                if o["class"] == r["class"] and (MASKD / f"{o['id']}.png").exists():
                    same |= plate_mask(o["id"]) > 128
            sub = same[cy0:cy1, cx0:cx1]
            if sub.sum() > rm[cy0:cy1, cx0:cx1].sum():
                extra = wd / "exclude"
                (extra / "masks").mkdir(parents=True, exist_ok=True)
                Image.fromarray((sub * 255).astype(np.uint8)).save(extra / "masks" / "001.png")
                (extra / "layers.json").write_text(json.dumps({
                    "tool": "build-zone-living", "size": [cx1 - cx0, cy1 - cy0],
                    "planeList": [{"n": 1, "name": f"{uid}-classwide", "offset": [0, 0]}]}))
                print(f"    donor scope: {int(sub.sum()):,}px of {r['class']} masked "
                      f"(vs {int(rm[cy0:cy1, cx0:cx1].sum()):,} for this region alone)",
                      file=sys.stderr)

        fn = TECHNIQUES[cls["technique"]]
        args = (wd, cls, pivot, cx0, cy0) + ((extra,) if extra is not None else ())
        # A REGION THAT YIELDS NO CARD IS AN ANSWER, NOT A FAILURE, and it must
        # not take 23 other regions down with it. Catalogued leaf masses are
        # authored at every scale: some are a bamboo tuft whose ink never reaches
        # --min-px once the leaf mask has gated it. Skip it, say so, keep going.
        # Anything else still stops the build.
        empty = False
        for step in fn(*args):
            res = subprocess.run(step, cwd=ROOT, capture_output=True, text=True)
            if res.returncode != 0:
                if "reached --min-px" in res.stderr or "no card" in res.stderr:
                    print(f"    {uid}: no card met --min-px -- region left still",
                          file=sys.stderr)
                    empty = True
                    break
                sys.exit(f"{uid}: {Path(step[1]).name} failed\n{res.stderr[-900:]}")
        if empty:
            continue
        cyc = json.loads((wd / "drawings" / "cycle.json").read_text())
        draw = [np.array(Image.open(wd / "drawings" / f"dr-{i:03d}.png").convert("RGB"))
                for i in range(cyc["drawings"])]
        base = np.array(plate.crop((cx0, cy0, cx1, cy1)), np.int16)
        moved = np.zeros(base.shape[:2], np.uint8)
        for d in draw:
            moved = np.maximum(moved, np.abs(d.astype(np.int16) - base).max(-1).astype(np.uint8))
        Image.fromarray(moved).save(wd / "moved.png")

        for q in order:
            if a.plane and q["name"] != a.plane:
                continue
            own = rm & vis[q["name"]]
            n = int(own.sum())
            if n < a.min_px or n < tot * a.min_frac:
                continue
            oy_, ox_ = q["offset"][1], q["offset"][0]
            tex = Image.open(LAY / q["layer"]).convert("RGBA")
            w_, h_ = tex.size
            oys, oxs = np.nonzero(own)
            # patch box in PLANE-LOCAL coords, clipped to the plane and to the
            # animated crop (a drawing only exists inside the crop)
            bx0 = int(max(0, max(oxs.min() - a.pad, cx0) - ox_))
            by0 = int(max(0, max(oys.min() - a.pad, cy0) - oy_))
            bx1 = int(min(w_, min(oxs.max() + 1 + a.pad, cx1) - ox_))
            by1 = int(min(h_, min(oys.max() + 1 + a.pad, cy1) - oy_))
            if bx1 <= bx0 or by1 <= by0:
                continue
            gx0, gy0 = bx0 + ox_, by0 + oy_          # same box in plate coords
            gx1, gy1 = bx1 + ox_, by1 + oy_
            texa = np.array(tex.crop((bx0, by0, bx1, by1)))
            sel = own[gy0:gy1, gx0:gx1]
            od = OUT / f"{q['name']}__{uid}"
            od.mkdir(parents=True, exist_ok=True)
            for i, d in enumerate(draw):
                out = texa.copy()
                dd = d[gy0 - cy0:gy1 - cy0, gx0 - cx0:gx1 - cx0]
                out[..., :3][sel] = dd[sel]
                Image.fromarray(out).save(od / f"{i:03d}.png")
            mv = int((moved[gy0 - cy0:gy1 - cy0, gx0 - cx0:gx1 - cx0][sel] > 6).sum())
            built.append({"plane": q["name"], "region": uid, "dir": str(od),
                          "box": [bx0, by0], "n": cyc["drawings"], "on": cyc["on"],
                          "ownPx": n, "movedPx": mv,
                          "crop": [int(cx0), int(cy0)], "class": r["class"]})
            print(f"    {q['name']:26s} owns {n:7d}px ({100*n/tot:5.1f}%), "
                  f"patch {bx1-bx0}x{by1-by0} at {bx0},{by0}, moved {mv}px",
                  file=sys.stderr)
        # The full-frame drawings were only ever an intermediate: the patches
        # carry the pixels the renderer reads, and moved.png carries the audit.
        # Keeping them costs about as much disk as the patches themselves.
        if not a.keep_work:
            for f in (wd / "drawings").glob("dr-*.png"):
                f.unlink()

    manifest = OUT / "built.json"
    prev = json.loads(manifest.read_text()) if manifest.exists() else []
    keep = [b for b in prev
            if not any(b["plane"] == n["plane"] and b["region"] == n["region"]
                       for n in built)]
    # PRUNE, DO NOT ONLY MERGE. built.json is the shipped living layer, and a
    # merge keeps every region ever built -- including ones since retired.
    # Measured 2026-08-20 by the generated STATE.md on its first run: NINE
    # summit regions Ryan had reverted ("peaks shouldnt wobble") were still
    # registered and playing in z6w, plus all six `still`-class nubs in every
    # zone. A decision to stop animating something has to reach the artefact,
    # not just the config, or it is not a decision.
    animated = {q["id"] for q in POLYS["polys"]
                if CLASSES.get(q["class"], {}).get("technique") not in (None, "none")}
    def region_of(b):
        r = b["region"]
        return r.rsplit("-", 1)[0] if r.rsplit("-", 1)[-1].isdigit() else r
    dropped = [b for b in keep if region_of(b) not in animated]
    keep = [b for b in keep if region_of(b) in animated]
    if dropped:
        byreg = sorted({region_of(b) for b in dropped})
        print(f"    pruned {len(dropped)} stale patches from {len(byreg)} retired "
              f"region(s): {', '.join(byreg)}", file=sys.stderr)
    manifest.write_text(json.dumps(keep + built, indent=1))
    print(json.dumps(built, indent=1))

# ------------------------------------------------------------- register -----
if a.stage == "register":
    built = json.loads((OUT / "built.json").read_text())
    living, ghosts = {}, []
    for b in built:
        # A PATCH WITH NO DRAWINGS IS NOT A PATCH. built.json accumulates across
        # runs, so registering a class whose cycle stage was never run for it
        # writes an entry pointing at an empty directory -- and the failure does
        # not surface here, it surfaces as a FileNotFoundError inside
        # render-parallax minutes later, with nothing to say which stage was
        # skipped. Measured 2026-08-24: z3w registered foliage,wave,fall,figure
        # after a cycle run of foliage alone, and 37 of its patches pointed at
        # nothing. Refuse them here, where the cause is still legible.
        if not os.path.exists(os.path.join(b["dir"], "000.png")):
            ghosts.append(b["region"])
            continue
        living.setdefault(b["plane"], {"patches": []})["patches"].append(
            {"dir": b["dir"], "box": b["box"], "n": b["n"], "on": b["on"]})
    if ghosts:
        byreg = sorted(set(ghosts))
        print(f"    NOT REGISTERED -- {len(ghosts)} patch(es) across {len(byreg)} "
              f"region(s) have no drawings on disk: {', '.join(byreg)}\n"
              f"    Run --stage cycle for their classes before registering them.",
              file=sys.stderr)
    out = HERE / f"living-{a.zone}.json"
    out.write_text(json.dumps(living, indent=1))
    print(json.dumps({"out": str(out), "planes": sorted(living),
                      "patches": sum(len(v["patches"]) for v in living.values()),
                      "skippedNoDrawings": len(ghosts)}, indent=1))

# ---------------------------------------------------------------- audit -----
if a.stage == "audit":
    built = json.loads((OUT / "built.json").read_text())
    plate = Image.open(Z / "plate.png").convert("RGB")
    heat = np.zeros((PH, PW), np.uint8)
    for rid in sorted({b["region"] for b in built}):
        b0 = next(b for b in built if b["region"] == rid)
        m = np.array(Image.open(WORK / rid / "moved.png"))
        gx, gy = b0["crop"]
        hh, ww = m.shape
        gx1, gy1 = min(PW, gx + ww), min(PH, gy + hh)
        heat[gy:gy1, gx:gx1] = np.maximum(heat[gy:gy1, gx:gx1],
                                          m[:gy1 - gy, :gx1 - gx])
    red = np.array(plate).astype(np.float32)
    w = np.clip(heat.astype(np.float32) / 40.0, 0, 1)[..., None]
    red = red * (1 - w) + np.array([255, 40, 40], np.float32) * w
    ev = Image.fromarray(red.astype(np.uint8))
    s = 1400 / max(ev.size)
    ev.resize((int(ev.width * s), int(ev.height * s))).save(
        HERE / f"evidence-living-{a.zone}.png")
    print(json.dumps({"zone": a.zone, "movedPx": int((heat > 6).sum()),
                      "pctOfPlate": round(100 * (heat > 6).sum() / (PW * PH), 3),
                      "peak": int(heat.max()),
                      "evidence": f"living/evidence-living-{a.zone}.png"}, indent=1))
