---
id: water-motion
kind: procedure
conflict-key: how-to-move-water
status: live
supersedes: []
sibling: foliage-motion
applies-when: >
  thin drawn marks quiver in place — ripple arcs, the threads of a fall. A few
  px of travel, no ground uncovered, no structure inside the region that has to
  stay still.
not-when: >
  the thing has a trunk, a branch, or any mass that must not move with the rest,
  or it travels far enough to reveal ground behind it. That is foliage — use the
  sibling, foliage-motion. Do NOT cut water into cards.
route: >
  animate-strokes.py --field wave --mode lift --keep tophat, registered as
  patches via jobs/wang-meng/living/build-zone-living.py
verified-on: 2026-08-20
evidence:
  - jobs/wang-meng/living/AB-LOOP-z1-water.mp4
  - jobs/wang-meng/living/evidence-loop-seam-z1.png
asked-as:
  - make the water move
  - animate ripples
  - animate a waterfall
---

## The raw trace

Proven on z1 and on four upper zones. What is measured:

`--keep tophat` is load-bearing. `--keep thin` asks whether a connected
COMPONENT is thin. Every ripple arc in the midstream pool touches a rock it
curls around, so arcs and rocks label as one mass: 70,330 ink px in 46
components, 683 px kept, and the "animated" drawing came out pixel-identical to
the plate. `tophat` asks by SHAPE -- a mass survives an opening by a disk of
max-thick, a line does not -- and returns 2,035 px which are the arcs.

The loop has to close. The wave field's cross-current chop carried 1.7 turns of
phase per cycle, so the last drawing did not meet the first. Wrap step against
largest ordinary step: 1.34 on z1 `water`, 1.61 on `upper-stream-water`,
1.4-1.7 across the five z3w bodies. `2.0*t` closes it: 0.96 and 0.97. Measure
any drawings dir with `jobs/wang-meng/living/seam.py`.

Closing the loop is also a LOOK change, and that gets reported as one: removing
1.7 turns of spurious phase removed ~38% of the frame-to-frame change on z1
water (mean step 0.0341 -> 0.0213). The ripples travel the same; they no longer
carry the extra chop. `--wobble` is the dial if it reads too calm.

Ryan's verdict on the water, 2026-08-20: "the water's subtle, it's good."
