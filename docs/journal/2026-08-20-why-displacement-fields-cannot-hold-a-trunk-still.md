# Why a displacement field cannot hold a trunk still

*Narrative extracted from `knowledge/foliage-motion.md` on 2026-08-21. The
claim keeps the RULE; this file keeps the story. Three layers, and a claim that
carries its own history stops being retrievable — measured the same day: with
this trace inside it, `foliage-motion` lost the query "make the leaves move" to
two shorter claims about the same subject. See the universal law
`three-layers-claim-narrative-status`.*

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
