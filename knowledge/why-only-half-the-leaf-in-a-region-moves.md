---
id: why-only-half-the-leaf-in-a-region-moves
kind: open
conflict-key: why-does-leaf-inside-an-animated-region-not-move
status: live
supersedes: []
proven: false
verified-on: 2026-08-24
evidence:
  - jobs/wang-meng/journey/measure-foliage-coverage.py
asked-as:
  - why is only some of the leaf in a region animated
  - the trees in the region are still
  - how much of a canopy actually moves
  - what limits foliage coverage inside a region
---

Inside regions that DO carry patches, ~40% of the catalogued leaf ink changes
across the cycle (z5w, 50 regions, 260,067 px). Four explanations were tested
and REFUTED; one is weakly supported. This is recorded as OPEN so the dead ends
are not re-walked.

**The ceiling is not 100%, and that is measured.** Translating a region's real
ink rigidly by 2px -- a motion that is complete by construction -- scores only
75-89% on this metric, because the interior of a solid mark does not change
colour when it moves; only edges do. Against each region's own ceiling the real
range is 27-80%. So roughly half the shortfall was never a shortfall.

REFUTED, with the number that killed each:

  * *the card size floor (--min-px 80) drops small distant marks.* Median ink
    cluster is 2-5px and 86-95% sit under the floor in the HIGH performers as
    much as the low. Size does not discriminate.
  * *leaf dots are not being joined into bushels before cutting.* After the
    default close (r=3) 96-100% of leaf ink is in clusters >=80px in every
    region, high and low alike.
  * *the metric is the artifact.* Partly true and quantified above, but it
    explains 11-25 points of a 50-point spread, not the spread.
  * *the builder and the measurement disagree about what leaf is* -- the builder
    crops the catalogue mask with NEAREST, the measurement with INTER_AREA and a
    threshold, on a 2.34x downsample. They agree to within 1% (484,554 vs
    489,759 px). Not the cause, and NEAREST is not losing thin sprays here.

WEAKLY SUPPORTED, and the only survivor: **card size**. A card rotates about its
own pivot, so a pixel's displacement scales with its distance from that pivot;
splitting a canopy into many small cards collapses the mean radius. Across 50
regions, ink-per-card vs moving fraction gives r = +0.32 -- regions below the
median (488 px/card) move 28% of their leaf, those above move 43%. Real, but
about 10% of the variance. A scale-aware swing (small cards given a
proportionally larger angle so displacement, not angle, is what is held
constant) is the obvious next experiment and has NOT been run.

A METHOD NOTE THAT COST TIME: `--frames 4` probes report a peakAngleDeg of
1.6-2.0 degrees against 15.08 at full length, because two sampled drawings never
land on the gust peak. That number is meaningless in a short probe and was
briefly mistaken for a sevenfold difference between regions.
