---
id: foliage-motion-by-displacement
kind: procedure
conflict-key: how-to-move-foliage
status: superseded
supersedes: []
sibling: water-motion
applies-when: >
  RETIRED 2026-08-20. Claimed: foliage stirs, so use animate-strokes --field
  sway.
not-when: >
  RETIRED. It never applied.
route: animate-strokes.py --field sway --mode warp
verified-on: never
evidence:
  - jobs/wang-meng/living/evidence-warp-blurs-lift-does-not.png
asked-as:
  - animate leaves with animate-strokes
  - use field sway for trees
---

## Why this was retired, 2026-08-20

It was never verified. It was inferred from the existence of a flag.

`animate-strokes` has a `--field sway` option, and `SKILL.md`'s routing table
carried the row *"the water should move / the leaves should stir ->
animate-strokes"*. The row directly below read *"a thin painted thing should
swing -- a limb, branch, rope, rail -> cut-stroke -> walk-figure --limbs"*,
which was the correct answer. A branch with leaves on it is both rows; the
keyword "leaves" won, and the right entry one line down was never read.

The mechanism is worth keeping: **a tool that RUNS is more persuasive than a
tool that FITS.** A flag's existence is evidence that somebody once thought
about the case, not evidence that it works.

Superseded by `foliage-motion`. Both SKILL.md rows are now one canonical entry
that names its sibling and states the test separating them.
