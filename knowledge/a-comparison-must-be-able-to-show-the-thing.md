---
id: a-comparison-must-be-able-to-show-the-thing
kind: law
conflict-key: how-do-i-build-a-comparison-that-can-actually-decide
status: live
supersedes: []
verified-on: 2026-08-26
evidence:
  - jobs/wang-meng/evidence/2026-08-26-z3w-blender-vs-handrolled.mp4
  - jobs/wang-meng/evidence/2026-08-26-z3w-relief-in-motion.mp4
asked-as:
  - he says he cannot tell the difference
  - my A B comparison shows nothing
  - how do I set up a fair comparison
  - the two versions look identical
  - is my test able to detect the effect
---

## Before rendering an A/B, state what a POSITIVE result would look like

Ryan said *"I honestly can't tell the difference"* twice on 2026-08-26, about
three different comparisons. He was right every time, and each time the fault
was in the comparison, not his eyes:

1. **Two clips of the same renderer.** Yesterday's dolly and today's z3w clip
   were BOTH `blender-multiplane.py`. There was no difference to see.
2. **A framing offset swamping the signal.** Blender vs `render-parallax`
   differed by mean 20 across 75% of pixels *at frame zero*, before either
   camera moved. Any parallax difference was buried under a constant offset.
   Worse, the framing excluded the depth entirely
   ([[z3w-depth-sits-below-a-16x9-frame]]), so neither clip contained parallax.
3. **A STILL of a MOTION effect.** Relief's whole value is within-card parallax
   as the camera passes. A frozen frame is the single medium in which it cannot
   appear.

**The check, before spending a render:** name the number or the visible change a
POSITIVE result would produce, and confirm the comparison can carry it. If the
effect lives in motion, the artefact is a clip. If a constant offset dominates,
normalise it or isolate the variable. If both arms share a hidden confound, the
test is measuring the confound.

**And exaggerate before tuning.** Render the effect at several times its
authored strength FIRST. If it is invisible at 5x it is not a tuning problem and
no amount of dialing will rescue it — that is a verdict, and the approach should
be archived rather than parameter-searched. This is the same trap as
[[null-before-the-metric]] approached from the other side: the null tells you
whether a positive is real, the exaggeration tells you whether a negative is
real.

Related: [[an-absence-is-invisible-in-the-output]].
