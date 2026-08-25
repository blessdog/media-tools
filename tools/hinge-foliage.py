#!/usr/bin/env python3
"""Swing cut-out foliage cards on a gust envelope over a clean plate. One job.

WHY THIS EXISTS RATHER THAN animate-strokes (2026-08-20). animate-strokes
displaces a pixel FIELD, and a field cannot express "only the leaves move":

  --mode warp   cv2.remap of the whole patch, so trunk, branch and leaf all
                travel together -- the lollipop-on-a-stick tell -- and every
                drawing is a resample of a resample. Measured on one canopy:
                15% of the ink's high-frequency energy gone at 7px of travel.
  --mode lift   mattes the ink out and fills the hole with cv2.INPAINT_TELEA,
                which is precisely the averaging inpainter clean-plate.py was
                written to replace ("a figure-sized hole becomes mush with no
                weave and no brush"). Ryan's word for the result was "mush".

A tree is a cut-out problem, not a displacement problem, on both of the tests
that decide this: it UNCOVERS GROUND when it moves, and it has STRUCTURE THAT
MUST STAY PUT. So each leaf mass becomes a card with its own hinge, the ground
behind it is synthesised once by clean-plate, and the trunk is simply not a
card -- Ryan's law ("just the delicate things move") stops being a discipline
and becomes a structural property of the rig.

The hinge is the one proven in walk-figure.py --limbs (the deer's legs):
getRotationMatrix2D about the card's own pivot, warpAffine of RGB and alpha,
alpha-blit. Rigid body, so the strokes keep their edges.

THE GUST IS AN EVENT, NOT A STATE (The Old Mill, 1937). Each card runs the
attack/hold/decay envelope on its own clock, delayed by its distance along the
wind, so the bending visibly travels across the frame. The envelope is zero at
both ends of its window, so the cycle closes exactly, and between gusts the
foliage idles at --gust-rest so it never reads as frozen.

WHAT THIS IS NOT FOR. Water. A ripple is a thin mark that quivers a few px,
uncovers no ground and has no structure to protect -- that is animate-strokes
--field wave, and it is right there. Do not cut water into cards.

usage:
  hinge-foliage.py --plate CLEAN.png --source ORIG.png --cards MASKDIR
                   --out DIR [--frames 192] [--on 2] [--fps 24]
                   [--swing 4.5] [--gust 0.10,0.08,0.22] [--gust-travel 1500]
                   [--gust-rest 0.15] [--angle 8] [--flutter 0.35] [--preview P.mp4]

  --plate    background with the cards already removed (clean-plate.py)
  --source   the image the card pixels are cut FROM (the untouched plate)
  --cards    dir with layers.json + masks/NNN.png; a plane may carry "pivot"
  --swing    degrees of rotation at gust peak, about each card's own pivot
  --angle    wind direction in degrees; the gust front travels along it
  --flutter  extra degrees of second-harmonic jitter, per card, so a stand of
             trees does not move as one object

  writes DIR/dr-%03d.png + DIR/cycle.json -- the same contract animate-strokes
  --out-frames emits, so the registration stage downstream is unchanged.

example:
  hinge-foliage.py --plate clean.png --source plate.png --cards canopy-masks \
      --out drawings --swing 5 --preview gust.mp4
"""
import argparse, json, subprocess, sys, tempfile, zlib
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

p = argparse.ArgumentParser()
p.add_argument('--plate', help='background with the cards removed. NOT REQUIRED under '
                    '--under hold, which never reads it: the source stays intact beneath the '
                    'cards, so there is no hole for a clean plate to fill. Demanding one there '
                    'forces a caller to synthesise a plate it will not use, which is the cost '
                    'that kept foliage coverage at 8 authored regions on this painting.')
p.add_argument('--under', choices=('clean', 'hold'), default='clean',
               help="what a card reveals when it swings off its rest position. "
                    "clean = the synthesised ground from --plate (bare silk and "
                    "rock under a tree). hold = the SOURCE, i.e. the original "
                    "leaves held still, so foliage is revealed behind foliage "
                    "and there is no hole to fill. See leaves-hold-under-leaves.")
p.add_argument('--source', required=True, help='image the card pixels come from')
p.add_argument('--cards', required=True, help='mask dir: layers.json + masks/')
p.add_argument('--only', default=None, help='restrict to one card by name')
p.add_argument('--out', required=True)
p.add_argument('--preview', default=None)
p.add_argument('--frames', type=int, default=192)
p.add_argument('--on', type=int, default=2)
p.add_argument('--fps', type=float, default=24)
p.add_argument('--swing', type=float, default=4.5,
               help='degrees at gust peak, about the card pivot')
p.add_argument('--flutter', type=float, default=0.35,
               help='degrees of second-harmonic jitter so a stand does not move as one')
p.add_argument('--angle', type=float, default=8.0, help='wind direction, degrees')
p.add_argument('--gust', default='0.10,0.08,0.22', help='attack,hold,decay as cycle fractions')
p.add_argument('--gust-travel', type=float, default=1500.0,
               help='px the gust front crosses in one cycle')
p.add_argument('--gust-rest', type=float, default=0.15,
               help='idle amplitude between gusts, as a fraction of --swing')
p.add_argument('--swing-px', type=float, default=0.0,
               help='hold DISPLACEMENT constant instead of angle: give every '
                    'card the angle that moves its mean leaf pixel this many px '
                    'at gust peak, clamped to --swing-min/--swing. 0 = off, use '
                    'a flat --swing. WHY: a card turns about its own pivot, so a '
                    'pixel moves r*sin(theta) -- one angle across cards of very '
                    'different size means the small ones barely move. Measured '
                    '2026-08-24 over 50 z5w regions: below the median 488 ink '
                    'px/card a region moves 28%% of its leaf, above it 43%%.')
p.add_argument('--swing-min', type=float, default=2.0,
               help='floor for --swing-px, degrees. Below this a hinge reads as '
                    'jitter rather than sway')
p.add_argument('--phase', type=float, default=0.0,
               help='shift this whole region along the gust clock, in cycles. '
                    'A GUST TRAVELS THROUGH THE PAINTING -- Ryan, 2026-08-24: '
                    '"further brushes move first and then closer move". Within a '
                    'region --gust-travel does that; ACROSS regions the caller '
                    'stages it by passing a phase taken from the plane depth, so '
                    'the far planes lead and the near ones answer')

p.add_argument('--carrier', type=int, default=1,
               help='how many times a card swings back and forth WITHIN one gust '
                    'cycle. THE ANIMATRONIC WAVE (Ryan, 2026-08-25): "it\'s almost '
                    'like the trees are animatronics, and then once in a while '
                    'they\'ll wave at you". At the default 1 the carrier sine and '
                    'the gust envelope share one clock, so on a 96-drawing loop '
                    'the branch takes 8s for a single out-and-back and completes '
                    'only 40%% of it before the envelope decays -- one wave, then '
                    '4.8s of near-stillness. A branch has its own natural period '
                    '(~1-2s) that is much shorter than a gust, so raise this to '
                    'separate the two clocks. This is a RATE change, not an '
                    'amplitude one: peak degrees are unchanged, which is what '
                    'keeps it clear of the two amplitude rejections. It is also '
                    'NOT the refuted broadband turbulence -- still one sine, still '
                    'one frequency, just not the gust\'s. Must be an integer or '
                    'the loop will not close.')

p.add_argument('--feather', type=int, default=2)
p.add_argument('--min-px', type=int, default=80, help='smallest card worth hinging')
p.add_argument('--branch-radius', default='auto',
               help='ink at least this half-width is BRANCH, not leaf; a card hinges '
                    'where it meets one (morphological opening by a disk). An integer, '
                    'or "auto": --branch-ratio x the 99th-percentile stroke half-width '
                    'of THIS tree, so a tree drawn smaller gets a thinner branch test')
p.add_argument('--branch-ratio', type=float, default=0.55,
               help='auto radius = this x p99 stroke half-width. 0.55 reproduces the '
                    'radius Ryan chose on s-pine-over-bridge (5 of 9.17)')
p.add_argument('--semantic', help='dir written by segment-semantic.py. A VISION MODEL decides which '
                    'regions are foliage (the WHAT); the ink cut below decides which pixels inside '
                    'them are painted mark (the WHICH). Supersedes --leaf-colour, which answered a '
                    'semantic question with colour thresholds')
p.add_argument('--semantic-class', default='green-and-orange-tree-leaves',
               help='slug of the class the cards belong to, as written by segment-semantic.py')
p.add_argument('--semantic-veto', default='bare-grey-rock-and-cliff',
               help='slug of the class that must NOT move')
p.add_argument('--semantic-mode', choices=('veto', 'keep'), default='veto',
               help='veto: drop ink only where the veto class beats the card class -- targets the '
                    'defect (rock swinging) and leaves everything else alone. keep: drop ink '
                    'anywhere the card class does not win, which is far stricter. MEASURED '
                    '2026-08-21 on z3w: keep costs real foliage (pine 21 cards -> 16, great trees '
                    '74 -> 52) because CLIPSeg draws blobby envelopes and misses small crowns; '
                    'veto removes the rock and holds the cards')
p.add_argument('--semantic-grow', type=int, default=4,
               help='px the semantic region is grown; CLIPSeg decodes at 352px and its edges sit '
                    'a few px inside the true canopy')
p.add_argument('--leaf-colour', dest='leaf_colour', action='store_true', default=True,
               help='a dark stroke is a LEAF only if it sits on coloured wash: green (Lab a '
                    'below the silk by --leaf-da) or orange (hue <= 28 deg, S >= 0.34). '
                    'Measured 2026-08-21: tone alone fuses a maple with the graphite cap of the '
                    'rock it stands on, and the rock swings (default on)')
p.add_argument('--no-leaf-colour', dest='leaf_colour', action='store_false')
p.add_argument('--leaf-da', type=float, default=2.5, help='green test: silk a minus this')
p.add_argument('--leaf-grow', type=int, default=5, help='px the leaf wash is grown to reach the strokes that draw it')
# ---- SECONDARY ACTION: the leaf, not the tree (2026-08-21, REJECTED) ------
# KEPT AS A DEAD END, not as a recommendation. Everything below works and the
# reasoning was sound animation theory -- and the output was still rejected, for
# a reason that outranks the theory: a card is a RIGID transform, so the ink
# inside it arrives unchanged, while deforming each mark redraws the painting in
# a hand that is not the painter's. Fidelity to the medium beats fidelity to the
# physics. Read knowledge/rigid-cards-preserve-the-brushwork.md before switching
# this on for any artwork you did not draw yourself.
# Ryan: "the entire leaf structure is one green blob... make the individual
# leaves kind of twinkle and shake. move around leaf not entire tree."
# A card is a connected component of ink, so a spray whose marks TOUCH is one
# blob on one hinge, and a blob on a hinge tilts -- it never shimmers. In cel
# practice a canopy has two scales: the spray swings on its branch (primary),
# and each leaf moves smaller, faster and out of phase with its neighbours
# (secondary action / overlapping action). The flash a real canopy gives off is
# a leaf turning edge-on, which for a flat mark is a narrowing along one axis.
p.add_argument('--leaf-mask',
               help='binary PNG in the SOURCE image\'s coordinate space: ink outside '
                    'it is not leaf. This is where a MODEL-derived mask goes -- a VLM '
                    'catalogue box refined by SAM (refine-mask-sam.py) and composited '
                    'to master px, then cropped to this plate by the caller. It '
                    'replaces --leaf-colour, which is a threshold and cannot tell a '
                    'rust maple from the cliff it stands on '
                    '(knowledge/perception-is-a-model-not-a-threshold.md)')
p.add_argument('--leaf-marks', action='store_true',
               help='OFF BY DEFAULT AND NOT FOR ANIMATING EXISTING BRUSHWORK. Splits '
                    'each card into individual leaf MARKS (distance-transform '
                    'watershed) and moves each on its own phase on top of the card '
                    'hinge. MEASURED 2026-08-21 on 葛稚川移居圖 and rejected: rotating '
                    'and narrowing a mark DEFORMS the stroke, which redraws the '
                    'painting instead of moving it. Ryan: "too aggressive. It deforms '
                    'the aesthetic." A card is a rigid transform and carries its '
                    'brushwork intact -- that is the point of a card. Use this only '
                    'where the marks are yours to redraw '
                    '(knowledge/rigid-cards-preserve-the-brushwork.md)')
p.add_argument('--mark-swing', type=float, default=3.0,
               help='degrees each mark rotates about its own centroid')
p.add_argument('--mark-rate', type=float, default=3.0,
               help='how many times faster than the gust a mark moves; non-integer '
                    'keeps marks from resynchronising with the spray')
p.add_argument('--mark-twinkle', type=float, default=0.25,
               help='0-1: how far a mark narrows as it turns edge-on. This is the '
                    'shimmer; rotation alone reads as wobble')
p.add_argument('--mark-shift', type=float, default=0.6,
               help='px of per-mark translation jitter')
p.add_argument('--min-mark', type=int, default=10, help='smallest blob worth calling a leaf')
p.add_argument('--marks-sheet', help='debug PNG: every mark in its own colour, so the '
                                     'split can be judged BEFORE 96 frames are rendered')
p.add_argument('--pivots', help='write a PNG of every card box and pivot over the '
                                'source: green = hinged at a branch, red = foot fallback')
p.add_argument('--attach-max', type=float, default=14.0,
               help='a card further than this from any branch is free-floating and '
                    'falls back to hinging at its own foot')
p.add_argument('--from-ink', dest='from_ink', action='store_true', default=True,
               help='cut cards from the INK inside each mask, not from the mask '
                    'itself (default). A canopy mask is a filled envelope; a card '
                    'cut from it carries the bare ground between the leaves and '
                    'drags it along. Cut to ink and only painted leaf travels, '
                    'while the clean plate shows through the gaps -- the same '
                    'reasoning as --keep tophat for water.')
p.add_argument('--whole-mask', dest='from_ink', action='store_false',
               help='one card per mask component instead: CROWN SWAY, the whole '
                    'mass bending on its branch. Right for a near isolated tree; '
                    'on a dense canopy it is a windscreen wiper.')
p.add_argument('--ink-offset', type=float, default=0.11,
               help='ink is V below the 75th percentile inside the mask, minus this')
p.add_argument('--ink-close', type=int, default=1,
               help='px to close the ink by, merging dots within a cluster '
                    'without bridging across clusters')
a = p.parse_args()

if a.under == 'hold':
    # Nothing is removed, so the "background with the cards removed" IS the
    # source. Bound to it rather than read from disk so the shape check below
    # and the metadata stay meaningful.
    plate = None
elif not a.plate:
    sys.exit('--plate is required unless --under hold')
else:
    plate = np.array(Image.open(a.plate).convert('RGB'), np.float32)
src = np.array(Image.open(a.source).convert('RGB'), np.float32)
if plate is None:
    plate = src.astype(np.float32)
if plate.shape != src.shape:
    sys.exit(f'plate {plate.shape[:2]} and source {src.shape[:2]} must be the same size')
H, W = plate.shape[:2]

meta = json.loads((Path(a.cards) / 'layers.json').read_text())
cards = []
n_attached = n_foot = branch_px = ink_dropped_px = 0
branch_radii = []
for pl in meta['planeList']:
    if a.only and pl['name'] != a.only:
        continue
    m = np.array(Image.open(Path(a.cards) / 'masks' / f"{pl['n']:03d}.png").convert('L'))
    ox, oy = pl.get('offset', (0, 0))
    full = np.zeros((H, W), np.uint8)
    full[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
    # ONE CARD PER LEAF MASS, not one per authored box: a stand of six trees on
    # a single hinge is the decal tell, and the pivot of a mass is a property
    # of that mass.
    src_mask = (full > 128)
    if a.from_ink:
        # A CARD IS PAINTED LEAF, NOT A REGION. The canopy mask is a filled
        # envelope produced by a density read; rotating it moves the bare ground
        # between the leaves too. Measured on s-compound-canopies-01: the
        # envelope is 53,773px in ONE component -- eroding it up to 12px never
        # splits it, so the envelope gives one rigid windscreen wiper. Cutting
        # to ink at offset 0.11 and closing by 1px gives 18 separate leaf
        # clusters, each with its own foot and its own phase, which is flutter
        # rather than sway.
        vsrc = cv2.cvtColor(src.astype(np.uint8), cv2.COLOR_RGB2HSV)[..., 2].astype(np.float32) / 255
        ground = float(np.percentile(vsrc[src_mask], 75))
        ink = ((vsrc < ground - a.ink_offset) & src_mask).astype(np.uint8)
        if a.ink_close:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.ink_close + 1,) * 2)
            ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, k)
        src_mask = ink > 0
        if a.semantic:
            # THE MODEL DECIDES WHAT, THE INK DECIDES WHICH PIXELS. Ryan,
            # 2026-08-21, on five hand-tuned colour thresholds answering "is this
            # a leaf": "this is a problem that has been astonishingly and
            # unbelievably solved by LLMs and vision models... and we're doing a
            # primitive, ridiculous way to point out what are trees from rocks."
            # He is right, and the failure is architectural: a threshold is a good
            # tool for "which pixels carry ink" and the worst possible tool for
            # "what is this thing". segment-semantic.py answers the second from
            # words; this cut answers the first. Neither alone is enough -- the
            # model's mask is a blobby envelope that includes the bare silk
            # between the leaves, and the ink cut has no idea what a tree is.
            sd = Path(a.semantic)
            scores = ({f.stem: np.array(Image.open(f).convert('L'), np.float32)
                       for f in sorted(sd.glob('*.png')) if f.stem != 'label'}
                      if sd.is_dir() else {})
            if a.semantic_class not in scores:
                # A MISSING SEMANTIC PASS MUST NOT SILENTLY SHIP THE OLD RIG, and
                # must not kill a whole zone build either. Say it loudly, fall back
                # to the colour gate, and record in cycle.json which one ran.
                print(f'!! semantic: {sd} has no {a.semantic_class!r} '
                      f'({sorted(scores) or "no masks at all"}) -- run '
                      f'living/build-semantic-masks.sh. FALLING BACK to the colour gate',
                      file=sys.stderr)
                a.semantic = None
            else:
                want = scores.pop(a.semantic_class)
                if a.semantic_mode == 'veto':
                    veto = scores.get(a.semantic_veto)
                    if veto is None:
                        sys.exit(f'--semantic-veto {a.semantic_veto!r} not in {sorted(scores)}')
                    bad = veto > want
                    if a.semantic_grow:
                        bad = cv2.erode(bad.astype(np.uint8), cv2.getStructuringElement(
                            cv2.MORPH_ELLIPSE, (2 * a.semantic_grow + 1,) * 2)) > 0
                    sem = ~bad
                    what = f'{a.semantic_veto} beats {a.semantic_class} on {100*bad.mean():.0f}%'
                else:
                    sem = want >= np.maximum.reduce(list(scores.values())) if scores else want > 127
                    if a.semantic_grow:
                        sem = cv2.dilate(sem.astype(np.uint8), cv2.getStructuringElement(
                            cv2.MORPH_ELLIPSE, (2 * a.semantic_grow + 1,) * 2)) > 0
                    what = f'{a.semantic_class} wins {100*sem.mean():.0f}%'
                dropped = int((src_mask & ~sem).sum())
                ink_dropped_px += dropped
                print(f'semantic[{a.semantic_mode}]: {what} of the crop; '
                      f'{dropped:,} ink px left still', file=sys.stderr)
                src_mask &= sem
        if a.leaf_mask:
            # A MODEL SAID SO, not a threshold. The mask arrives in the source
            # image's own space, so it needs no reprojection here -- the caller
            # owns the master->plate crop because the caller is what knows the
            # plate's masterBox and scale.
            lm = np.array(Image.open(a.leaf_mask).convert('L'))
            if lm.shape != src_mask.shape:
                lm = cv2.resize(lm, (src_mask.shape[1], src_mask.shape[0]),
                                interpolation=cv2.INTER_NEAREST)
            keep = lm > 127
            dropped = int((src_mask & ~keep).sum())
            ink_dropped_px += dropped
            print(f'leaf-mask: model keeps {100*keep.mean():.0f}% of the crop; '
                  f'{dropped:,} ink px left still', file=sys.stderr)
            src_mask &= keep
        elif (not a.semantic) and a.leaf_colour:
            # WHAT A LEAF IS, IN THIS PAINTING. Ryan, 2026-08-21: "The leaves are all
            # green or orange. You shouldn't be animating the graphite ridges of
            # rocks." The dark strokes that draw a leaf and the dark strokes that
            # draw a rock are the same grey ink, and where they touch, a tone
            # threshold fuses them into one card. The COLOUR is in the wash under
            # the strokes, never in the strokes themselves -- so classify the
            # mid-tone wash (green: Lab a below the silk's; orange: warm hue at a
            # saturation the silk never reaches), grow it a few px to reach the
            # strokes drawn over it, and keep only ink inside that. Measured on
            # s-gorge-foreground: 3,946 of 40,848 ink px dropped, all of it the
            # rock cap under the maples. evidence-leafcut-*.png
            mid = (vsrc >= ground - a.ink_offset) & (vsrc < ground + 0.15)
            lab = cv2.cvtColor(src.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
            hsvf = cv2.cvtColor(src.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
            hue, sat = hsvf[..., 0] * 2, hsvf[..., 1] / 255
            silk_a = float(np.median(lab[..., 1][mid])) if mid.any() else 128.0
            green = (lab[..., 1] <= silk_a - a.leaf_da) & mid
            orange = (hue <= 28) & (sat >= 0.34) & mid
            leaf = cv2.dilate((green | orange).astype(np.uint8),
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.leaf_grow + 1,) * 2)) > 0
            dropped = int((src_mask & ~leaf).sum())
            ink_dropped_px += dropped
            print(f'leaf colour: silk a={silk_a:.0f}; green {int(green.sum()):,}px, orange '
                  f'{int(orange.sum()):,}px of wash; {dropped:,} ink px are not on a leaf and are left still',
                  file=sys.stderr)
            src_mask &= leaf
    # WHAT IS A BRANCH. Wang Meng paints trunk and branch with a loaded brush
    # and leaves with a fine one, so THICKNESS separates them -- the same
    # morphological read that separates ripple arcs from rock (--keep tophat).
    # An opening by a disk of radius r keeps only what is at least 2r wide.
    # THE RADIUS IS A PROPERTY OF THE TREE, NOT OF THE PAINTING. Measured
    # 2026-08-21 across the seven near trees: the pine over the bridge has a
    # 9.2px p99 stroke half-width, every other tree 3.3-6.1px -- the same
    # drawing made smaller. A fixed radius 5 hinged 18/23 pine cards at a
    # branch and 1/68 on the big gorge canopy, because at that width the
    # smaller tree HAS no branch ink. evidence-branch-radius-sweep.json.
    if str(a.branch_radius) == 'auto':
        dts = cv2.distanceTransform(src_mask.astype(np.uint8), cv2.DIST_L2, 3)[src_mask]
        p99 = float(np.percentile(dts, 99)) if dts.size else 0.0
        br = max(2, int(round(a.branch_ratio * p99)))
        print(f'branch radius auto: p99 half-width {p99:.2f}px x {a.branch_ratio} -> r={br}',
              file=sys.stderr)
    else:
        br = int(a.branch_radius)
    branch_radii.append(br)
    kb = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * br + 1,) * 2)
    branch = cv2.morphologyEx(src_mask.astype(np.uint8), cv2.MORPH_OPEN, kb)
    branch_dist = (cv2.distanceTransform(1 - branch, cv2.DIST_L2, 3)
                   if branch.any() else np.full(src_mask.shape, 1e9, np.float32))
    branch_px += int(branch.sum())
    print(f'branch ink (opening by r={br}): {branch_px:,}px '
          f'of {int(src_mask.sum()):,}', file=sys.stderr)

    n, lab, st, cen = cv2.connectedComponentsWithStats(src_mask.astype(np.uint8), 8)
    for i in range(1, n):
        if st[i, 4] < a.min_px:
            continue
        solid = (lab == i).astype(np.float32)
        al = solid
        if a.feather:
            # FEATHER OUTWARD ONLY. Blurring the binary mask directly pulls the
            # alpha below 1 along the INSIDE of every edge, so the composite
            # base*(1-al) + rgb*al lerps the cluster's own outline toward the
            # clean plate -- which has the ink removed. Measured 2026-08-20: a
            # ZERO-degree hinge changed 26,293px by up to 102 levels and visibly
            # thinned every leaf spray, before any rotation happened at all.
            # Taking the max with the solid mask keeps the interior at exactly 1,
            # so a card at rest is a bit-exact no-op and the ramp only softens
            # the cut edge where the card leaves its hole.
            k = a.feather * 2 + 1
            al = np.maximum(solid, cv2.GaussianBlur(solid, (k, k), 0))
        ys, xs = np.nonzero(lab == i)
        x0, y0 = int(xs.min()), int(ys.min())
        x1, y1 = int(xs.max()) + 1, int(ys.max()) + 1
        pad = a.feather * 3 + 2
        x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
        x1, y1 = min(W, x1 + pad), min(H, y1 + pad)
        # THE HINGE IS THE ATTACHMENT, NOT THE FOOT (2026-08-20).
        # A leaf spray pivots where it joins its twig. Hinging it at the bottom
        # of its own mass swings the whole spray sideways and slides it off the
        # branch -- visible at 6 degrees, and no amplitude fixes it because the
        # axis is in the wrong place. Ryan: "these are not acceptable."
        # The branch is the THICK ink; the leaves are the thin marks. So the
        # pivot is the cluster pixel nearest a thick stroke, and where a cluster
        # touches no branch at all (a free-floating spray) the foot is the
        # honest fallback.
        near = branch_dist[ys, xs]
        j = int(np.argmin(near))
        attached = bool(near[j] <= a.attach_max)
        if attached:
            pvx, pvy = float(xs[j]), float(ys[j])
            n_attached += 1
        else:
            foot = ys > ys.max() - 6
            pvx, pvy = float(xs[foot].mean()), float(ys.max())
            n_foot += 1
        cards.append({
            'attached': attached,
            'name': f"{pl['name']}-{i:02d}", 'box': (x0, y0, x1, y1),
            'pivot': (pvx - x0, pvy - y0), 'along': 0.0, 'px': int(st[i, 4]),
            'rgb': src[y0:y1, x0:x1].copy(),
            'al': al[y0:y1, x0:x1].copy(),
            'solid': solid[y0:y1, x0:x1].copy(),
            # crc32, not hash(): str hash is salted per process, so the same
            # flags gave a different gust phase on every run and no two builds
            # of one tree were comparable.
            'seed': (zlib.crc32(pl['name'].encode()) + i) % 1000 / 1000.0,
        })
if not cards:
    sys.exit(f'no card in {a.cards} reached --min-px {a.min_px}')


def split_marks(solid, min_mark):
    """Cut one card's ink into individual leaf marks.

    Distance-transform watershed -- the standard separation for touching blobs
    of similar size, which is exactly what a leaf spray is. The seed spacing is
    read from the ink itself (the median distance-transform value over the ink
    is the typical mark half-width), because Wang Meng paints leaves at
    near-constant real size and a distant tree is the same drawing with smaller
    marks. A fixed spacing splits one tree and fuses the next.
    """
    u8 = (solid > 0.5).astype(np.uint8)
    if u8.sum() < min_mark * 2:
        return None
    dist = cv2.distanceTransform(u8, cv2.DIST_L2, 3)
    r = float(np.median(dist[u8 > 0]))
    k = max(3, int(2 * max(r, 1.0)) | 1)
    peaks = (dist >= cv2.dilate(dist, np.ones((k, k), np.uint8)) - 1e-6) & (dist > 0.6 * r)
    nseed, seeds = cv2.connectedComponents(peaks.astype(np.uint8))
    if nseed <= 2:
        return None
    markers = np.where(u8 > 0, seeds, 0).astype(np.int32)
    markers[u8 == 0] = 1                      # background is marker 1
    markers[(u8 > 0) & (seeds == 0)] = 0      # unknown: watershed fills these
    rgb3 = cv2.cvtColor((u8 * 255), cv2.COLOR_GRAY2BGR)
    cv2.watershed(rgb3, markers)
    out = []
    for lbl in range(2, nseed):
        m = (markers == lbl) & (u8 > 0)
        if m.sum() < min_mark:
            continue
        out.append(m)
    return out if len(out) > 1 else None


n_marks = 0
if a.leaf_marks:
    for c in cards:
        parts = split_marks(np.squeeze(c['solid']), a.min_mark)
        if not parts:
            continue
        marks = []
        for j, m in enumerate(parts):
            ys, xs = np.nonzero(m)
            # Each mark keeps its OWN tight box. Warping a mark inside the whole
            # card box would cost the card's area per mark per frame; on a dense
            # spray that is the difference between seconds and minutes.
            mx0, my0 = int(xs.min()), int(ys.min())
            mx1, my1 = int(xs.max()) + 1, int(ys.max()) + 1
            pad = 2
            mx0, my0 = max(0, mx0 - pad), max(0, my0 - pad)
            mx1 = min(c['solid'].shape[1], mx1 + pad); my1 = min(c['solid'].shape[0], my1 + pad)
            sub = m[my0:my1, mx0:mx1].astype(np.float32)
            marks.append({
                'box': (mx0, my0, mx1, my1),
                'cen': (float(xs.mean()) - mx0, float(ys.mean()) - my0),
                'rgb': c['rgb'][my0:my1, mx0:mx1].copy(),
                'al': (np.squeeze(c['al'])[my0:my1, mx0:mx1] * sub).copy(),
                'seed': ((zlib.crc32(c['name'].encode()) + j * 7919) % 1000) / 1000.0,
            })
        if len(marks) > 1:
            c['marks'] = marks
            n_marks += len(marks)
    print(f'leaf marks: {n_marks:,} across {sum(1 for c in cards if "marks" in c)} '
          f'of {len(cards)} cards', file=sys.stderr)

if a.marks_sheet:
    ov = src.astype(np.uint8).copy()
    rng = np.random.default_rng(7)
    for c in cards:
        x0, y0, x1, y1 = c['box']
        if 'marks' not in c:
            # a card nothing could split is drawn in grey: it is still one blob
            sol = np.squeeze(c['solid']) > 0.5
            ov[y0:y1, x0:x1][sol] = (140, 140, 140)
            continue
        for m in c['marks']:
            mx0, my0, mx1, my1 = m['box']
            col = rng.integers(60, 255, 3)
            sub = ov[y0 + my0:y0 + my1, x0 + mx0:x0 + mx1]
            sel = m['al'] > 0.5
            sub[sel] = (sub[sel] * 0.25 + col * 0.75).astype(np.uint8)
    Path(a.marks_sheet).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(ov).save(a.marks_sheet)
    print(f'marks sheet -> {a.marks_sheet}', file=sys.stderr)

if a.pivots:
    ov = src.astype(np.uint8).copy()
    for c in cards:
        x0, y0, x1, y1 = c['box']
        col = (40, 170, 60) if c['attached'] else (220, 40, 40)
        cv2.rectangle(ov, (x0, y0), (x1 - 1, y1 - 1), col, 1)
        px, py = int(round(c['pivot'][0] + x0)), int(round(c['pivot'][1] + y0))
        cv2.circle(ov, (px, py), 4, col, -1)
        cv2.circle(ov, (px, py), 5, (255, 255, 255), 1)
    Path(a.pivots).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(ov).save(a.pivots)

th = np.deg2rad(a.angle)
for c in cards:
    x0, y0, x1, y1 = c['box']
    c['along'] = (x0 + c['pivot'][0]) * np.cos(th) + (y0 + c['pivot'][1]) * np.sin(th)
amin = min(c['along'] for c in cards)
for c in cards:
    c['delay'] = (c['along'] - amin) / max(a.gust_travel, 1e-3)

# PER-CARD SWING, so displacement rather than angle is what is held constant.
# r is the mean distance of the card's own ink from its pivot; the angle that
# moves that mean pixel --swing-px is asin(px / r).
if a.swing_px > 0:
    for c in cards:
        ys, xs = np.nonzero(c['al'][..., 0] if c['al'].ndim == 3 else c['al'])
        if len(xs) == 0:
            c['swing'] = a.swing
            continue
        r = float(np.mean(np.hypot(xs - c['pivot'][0], ys - c['pivot'][1])))
        if r < 1.0:
            c['swing'] = a.swing_min
            continue
        deg = np.degrees(np.arcsin(min(1.0, a.swing_px / r)))
        c['swing'] = float(min(a.swing, max(a.swing_min, deg)))
else:
    for c in cards:
        c['swing'] = a.swing

ga, gh, gd = (float(q) for q in a.gust.split(','))
if ga + gh + gd >= 0.95:
    sys.exit('--gust A+H+D must leave calm air in the loop: keep the sum under 0.95')
if a.carrier < 1:
    sys.exit('--carrier must be an integer >= 1; a non-integer breaks the loop seam')

def envelope(u):
    """attack -> hold -> decay -> calm, zero at both ends so the loop closes.

    Fires --gusts times per cycle. An integer count keeps the loop seamless:
    the envelope is zero at both ends of each pulse window, so N pulses tile the
    cycle exactly however large N is.
    """
    u = u % 1.0
    if u < ga:
        return 0.5 - 0.5 * np.cos(np.pi * u / ga)
    if u < ga + gh:
        return 1.0
    if u < ga + gh + gd:
        return 0.5 + 0.5 * np.cos(np.pi * (u - ga - gh) / gd)
    return 0.0

# THE BASE IS THE SOURCE, NOT THE CLEAN PLATE (fix, 2026-08-20).
# `frame = plate.copy()` erased every masked pixel that did not become a card,
# and on a real tree that is most of it: measured on s-pine-over-bridge, the
# region is 72,564px, the cards are 33,227px, and the remaining 39,337px --
# 54.2% of the canopy, being the pale wash between the leaf strokes plus 197
# specks under --min-px -- was deleted before anything moved. Ryan's word for
# the result was "broken", and he was looking at a pine with half its paint
# gone, not at a swing that was too large.
#
# The clean plate is only needed where a card CAN VACATE, which is exactly each
# card's rest footprint. Everywhere else the painting stands.
#
# --under hold: DO NOT PUNCH THE PLATE THROUGH AT ALL. Ryan, 2026-08-24, looking
# at the pine over the bridge: "the movement of these leaves and the background
# of the canvas should be the same leaves, so it doesn't look like it tears
# anything like the trunk of this tree, but instead it just moves the set of
# leaves off to the side, so right behind it is still a set of leaves."
#
# That is the cel-animation double layer: the held under-layer of a moving
# foliage cel is more foliage. With the source left intact underneath, the
# sliver a card vacates shows the ORIGINAL leaf strokes rather than synthesised
# ground, so there is no hole to fill and nothing to tear at the trunk. It also
# stays inside clean-plate-donor-scope, which bans SYNTHESISING foliage into a
# foliage-shaped hole -- a held copy of the same card invents nothing; those
# marks are Wang Meng's and they were already there.
#
# The cost is a doubled edge at the swing extremes, bounded by the swing itself
# (6 deg on this painting), against a guaranteed bare-ground reveal otherwise.
base = src.astype(np.float32).copy()
if a.under == 'clean':
    vacate = np.zeros((H, W), bool)
    for c in cards:
        x0, y0, x1, y1 = c['box']
        # SOLID, not the feathered extent. Inside the ramp band the card's alpha
        # is < 1, so if the base there were the clean plate the composite would
        # mix plate and ink and thin the outline. With the base left as source, a
        # card at rest composites source-over-source and is bit-exact; the cost
        # is a ~2px ghost of the old edge once it swings.
        vacate[y0:y1, x0:x1] |= (np.squeeze(c['solid']) > 0.5)
    base[vacate] = plate[vacate]
    print(f'base: source everywhere except {int(vacate.sum()):,}px of card '
          f'footprint ({100*vacate.sum()/(H*W):.1f}% of the crop) where the '
          f'clean plate shows', file=sys.stderr)
else:
    print('base: SOURCE EVERYWHERE (--under hold) -- a card vacating reveals the '
          'original leaves, never synthesised ground', file=sys.stderr)

ndraw = max(1, a.frames // max(a.on, 1))
outd = Path(a.out); outd.mkdir(parents=True, exist_ok=True)
peak = 0.0
for k in range(ndraw):
    t = k / ndraw
    frame = base.copy()
    for c in cards:
        e = envelope(t - c['delay'])
        act = a.gust_rest + (1 - a.gust_rest) * e
        # ONE SINE, DELIBERATELY. A broadband turbulence spectrum was built and
        # REJECTED here on 2026-08-24 -- see knowledge/subtle-beats-continuous-
        # for-this-painting.md. It removed every still frame and multiplied
        # frame-to-frame motion by 87x at identical peak swing, and Ryan's verdict
        # on the A/B was "it looked better before the turbulent spectrum. I don't
        # want that. I like the subtleness of it."
        ph = 2 * np.pi * (a.carrier * (t - c['delay'] - a.phase) + c['seed'])
        sw = c['swing']
        ang = sw * act * np.sin(ph) + a.flutter * act * np.sin(3 * ph + 1.7)
        peak = max(peak, abs(float(ang)))
        x0, y0, x1, y1 = c['box']
        M = cv2.getRotationMatrix2D(c['pivot'], float(ang), 1.0)
        wh = (x1 - x0, y1 - y0)
        if 'marks' not in c:
            rgb = cv2.warpAffine(c['rgb'], M, wh, flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REPLICATE)
            al = cv2.warpAffine(c['al'], M, wh, flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT)[..., None]
            frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - al) + rgb * al
            continue
        # TWO SCALES, COMPOSED (2026-08-21). The spray's hinge M is the primary
        # motion; each mark then gets its own rotation, its own narrowing as it
        # turns edge-on, and its own jitter, about ITS OWN centroid. Composing
        # the two 3x3s and warping once per mark keeps this one resample -- warp
        # the mark by M and then again by its own matrix and every leaf softens.
        M3 = np.vstack([M, [0, 0, 1]])
        for mk in c['marks']:
            mx0, my0, mx1, my1 = mk['box']
            mph = 2 * np.pi * (t * a.mark_rate + mk['seed'])
            mang = a.mark_swing * act * np.sin(mph)
            # edge-on flash: narrow across the mark, never along it, so the leaf
            # reads as turning rather than shrinking
            sx = 1.0 - a.mark_twinkle * act * abs(np.sin(mph + 0.9))
            dx = a.mark_shift * act * np.sin(mph * 1.31 + mk['seed'] * 6.28)
            dy = a.mark_shift * act * np.cos(mph * 1.17 + mk['seed'] * 6.28)
            cx, cy = mk['cen']
            Rm = cv2.getRotationMatrix2D((cx, cy), float(mang), 1.0)
            Rm3 = np.vstack([Rm, [0, 0, 1]])
            S3 = np.array([[sx, 0, cx * (1 - sx) + dx], [0, 1.0, dy], [0, 0, 1]])
            # the mark lives at (mx0,my0) inside the card, so shift into card
            # space, apply the card hinge, and come back to the mark's own box
            T_in = np.array([[1, 0, mx0], [0, 1, my0], [0, 0, 1]], float)
            T_out = np.array([[1, 0, -mx0], [0, 1, -my0], [0, 0, 1]], float)
            full = (T_out @ M3 @ T_in @ Rm3 @ S3)[:2]
            mwh = (mx1 - mx0, my1 - my0)
            mrgb = cv2.warpAffine(mk['rgb'], full, mwh, flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REPLICATE)
            mal = cv2.warpAffine(mk['al'], full, mwh, flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT)[..., None]
            ax0, ay0 = x0 + mx0, y0 + my0
            ax1, ay1 = x0 + mx1, y0 + my1
            frame[ay0:ay1, ax0:ax1] = frame[ay0:ay1, ax0:ax1] * (1 - mal) + mrgb * mal
    Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(outd / f'dr-{k:03d}.png')

(outd / 'cycle.json').write_text(json.dumps({
    'tool': 'hinge-foliage', 'drawings': ndraw, 'on': a.on, 'fps': a.fps,
    'cards': len(cards), 'fromInk': a.from_ink, 'swingDeg': a.swing, 'peakAngleDeg': round(peak, 2),
    'gust': a.gust, 'gustTravel': a.gust_travel, 'gustRest': a.gust_rest,
    'carrier': a.carrier, 'branchPeriodSec': round(ndraw * a.on / a.fps / a.carrier, 2),
    'phase': a.phase,
    'angle': a.angle, 'flutter': a.flutter,
    'branchRadius': branch_radii[0] if len(set(branch_radii)) == 1 else branch_radii,
    'branchRadiusMode': str(a.branch_radius), 'branchRatio': a.branch_ratio, 'attachMax': a.attach_max,
    'cardsAttached': n_attached, 'cardsFoot': n_foot, 'branchPx': branch_px,
    'leafSource': ('leaf-mask' if a.leaf_mask else
                   'semantic' if a.semantic else ('colour' if a.leaf_colour else 'none')),
    'leafMask': a.leaf_mask,
    'semanticDir': a.semantic, 'semanticClass': a.semantic_class if a.semantic else None,
    'semanticMode': a.semantic_mode if a.semantic else None,
    'leafColour': bool(a.leaf_colour and not a.semantic and not a.leaf_mask), 'inkNotOnLeafPx': ink_dropped_px,
    'leafMarks': bool(a.leaf_marks), 'marks': n_marks,
    'markSwingDeg': a.mark_swing if a.leaf_marks else None,
    'markRate': a.mark_rate if a.leaf_marks else None,
    'markTwinkle': a.mark_twinkle if a.leaf_marks else None,
    'markShift': a.mark_shift if a.leaf_marks else None,
    'technique': ('cards hinged at their branch, each split into leaf marks that '
                  'rotate, narrow and jitter on their own phase'
                  if a.leaf_marks else
                  'rigid cut-out cards hinged where they meet a branch, over a clean plate'),
    'plate': a.plate, 'source': a.source, 'cards_dir': a.cards,
}, indent=1))

if a.preview:
    with tempfile.TemporaryDirectory() as td:
        for i in range(a.frames):
            src_f = outd / f'dr-{(i // a.on) % ndraw:03d}.png'
            (Path(td) / f'{i:05d}.png').symlink_to(src_f.resolve())
        subprocess.run(['ffmpeg', '-y', '-framerate', str(a.fps), '-i',
                        str(Path(td) / '%05d.png'), '-c:v', 'libx264', '-crf', '16',
                        '-pix_fmt', 'yuv420p', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
                        a.preview], check=True, capture_output=True)

print(json.dumps({'out': str(outd), 'drawings': ndraw, 'cards': len(cards),
                  'peakAngleDeg': round(peak, 2),
                  'preview': a.preview}, indent=1))
