---
id: foliage-motion
kind: procedure
conflict-key: how-to-move-foliage
status: live
supersedes:
  - foliage-motion-by-displacement
sibling: water-motion
applies-when: >
  a painted mass UNCOVERS GROUND when it moves, or it has INTERNAL STRUCTURE
  THAT MUST STAY PUT. Either test alone is sufficient. Foliage answers yes to
  both: a canopy reveals cliff behind it, and its trunk and branches are mass
  that must not travel with the leaves.
not-when: >
  the mark is a thin stroke that quivers in place, uncovers nothing, and has no
  structure to protect. That is water — use the sibling, water-motion.
route: >
  clean-plate.py --method shiftmap (synthesise the ground behind the canopy,
  ONCE) -> hinge-foliage.py --from-ink --branch-radius auto --attach-max 14
  --leaf-marks (cut one card per ink cluster, pivot WHERE IT JOINS A BRANCH --
  see hinge-at-the-attachment -- rotate on a gust envelope delayed by position
  along the wind, AND split each card into its individual leaf marks so each one
  moves on its own phase -- see leaf-marks-are-the-second-scale, without which a
  spray of touching marks is one rigid blob that can only tilt) ->
  render-parallax (composite at depth). Implemented as the
  foliage-motion entry in jobs/wang-meng/living/build-zone-living.py's
  TECHNIQUES table. NOT cut-stroke.py first: hinge-foliage cuts its own cards,
  because the card decomposition is what decides crown-sway vs leaf-flutter and
  therefore belongs to the tool that swings them.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/living/evidence-warp-blurs-lift-does-not.png
  - jobs/wang-meng/evidence/AB-leafmarks-s-pine-over-bridge.mp4
asked-as:
  - make the leaves move
  - animate a tree
  - foliage in wind
---

## The raw trace, 2026-08-20

Six parameter passes were spent inside `animate-strokes` before the technique
was questioned at all. What each one measured:

    keep=all, warp, wobble 3    peak displacement 5.2px on a 423x495 canopy.
                                Ryan: "almost none of the foliage appears to
                                move at all." One percent of the canopy width.
    mode warp vs mode lift      identical 7.1px displacement. High-frequency
                                energy (Laplacian variance) of the peak-gust
                                drawing: plate 341.1, warp 291.1 (-15%),
                                lift 311.6 (-9%).
    amplitude sweep             wobble 3/8/16/28 -> peak 5.2/13.8/27.6/47.8px.

Neither mode was right, for structurally different reasons.

`--mode warp` is `cv2.remap` over the whole patch. Every drawing is an
interpolation of an interpolation, and trunk, branch and leaves all travel
together -- the lollipop-on-a-stick tell. A displacement FIELD cannot hold part
of its own region still, so it cannot express "only the leaves move".

`--mode lift` mattes the ink out and fills the hole at `animate-strokes.py:178`
with `cv2.INPAINT_TELEA`. That is the exact averaging inpainter that
`clean-plate.py`'s docstring was written to warn against: *"they diffuse
surrounding colour inward and a figure-sized hole becomes mush with no weave
and no brush."* Ryan, looking at the output with no knowledge of that file,
said: "it seems like you're just doing a weird mush." Same word, months apart.

Two further defects found while measuring, both fixed:

    hold clips were 6.0s        the gust cycle is 96 drawings x on2 @ 24fps =
                                8.0s, and the envelope occupies only 40% of it,
                                delayed per card by position along the wind. For
                                some canopies the gust fell entirely inside the
                                2s never shown. Every A/B is now >= one cycle.
    holds framed ONE body       water and foliage were never in one frame. A
                                testing artifact leaking into review.

The hinge is not new work: `walk-figure.py --limbs` has swung the deer's legs
since 2026-08-16 using `getRotationMatrix2D` about each limb's own pivot,
`warpAffine` of RGB and alpha, then an alpha blit. `hinge-foliage.py` is that
mechanism with a gust envelope in place of a gait.
