---
id: figure-motion
kind: procedure
conflict-key: how-to-move-a-figure
status: live
supersedes: []
sibling: foliage-motion
applies-when: >
  a painted PERSON or ANIMAL should move -- a robe stirring, the deer walking.
  Same two tests as foliage and it answers yes to both: a limb uncovers the
  ground behind it, and the head, torso and face are structure that must not
  deform. A figure is a jointed cut-out, which is what cel animation has always
  said it is.
not-when: >
  the figure is smaller than roughly 40px of ink, where a hinge reads as a
  jitter and stillness is correct. The old blanket ban on INVENTING a motion is
  retired -- Ryan 2026-08-21: "we can invent a little bit of ink... as long as it
  looks hand-drawn." See invented-ink-is-allowed-in-the-painters-hand for the
  line that replaces it: new marks may be drawn in Wang's hand, EXISTING marks
  are still moved rigidly and never deformed.
route: >
  reuse a verified cycle from jobs/wang-meng/living/cycles/ where one exists ->
  otherwise cut-stroke.py (one card per limb, pivot at the joint) ->
  walk-figure.py --limbs (getRotationMatrix2D about each pivot, warpAffine of
  RGB and alpha, alpha-blit) -> render-parallax (composite at depth)
verified-on: 2026-08-16
evidence:
  - jobs/wang-meng/living/cycles
asked-as:
  - animate a person
  - make the robe stir
  - move the deer
---

## The raw trace

`walk-figure.py --limbs` has swung the deer's legs since 2026-08-16. It is the
oldest working hinge in this job and the mechanism `hinge-foliage.py` was later
copied from -- rigid-body rotation about a per-card pivot, so the strokes keep
their edges instead of becoming a resample of a resample.

The `figure` class in `regions.json` carried the note *"reuse proven cycles
only; never generate a new figure cycle without a verdict"* with nothing
enforcing it. That sentence is the `not-when` above now, where a query can
reach it.

Ryan, 2026-08-20, on the queue: *"Maybe eventually we can get to moving the
characters a little bit or changing their facial expressions, but we'll cross
that bridge when we get to it."* Robes are in scope under [[what-moves]];
faces are not, yet.
