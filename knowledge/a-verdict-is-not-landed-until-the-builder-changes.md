---
id: a-verdict-is-not-landed-until-the-builder-changes
kind: law
conflict-key: what-makes-a-proven-technique-actually-spread
status: live
supersedes: []
asked-as:
  - why did a proven technique never get used again
  - we figured this out already why isn't it everywhere
  - what does joins the locked recipe actually require
  - a discovery was made and then lost
  - how do I make a verdict stick across the project
  - relief only exists on one zone
---

## Prose saying "this joins the locked recipe" is a wish. The recipe is whatever script runs next.

Measured on 2026-08-22, from the commit log of a single night.

**2026-08-19, 19:47 — `02f025d`, "verdict: relief wins the river-entry A/B —
LDI hybrid joins the locked recipe."** The A/B was real, the null was verified,
the technique was right. The commit changed **`STATE.md` and nothing else: seven
lines of prose, zero lines of code.**

**The same night, `ade1381` through `3bcb93e` — six zone worlds built** through
`jobs/wang-meng/journey/build-zone.sh`, whose own header documents the chain:

    segment-points -> invariant check -> complete-planes -> segment-regions
    -> pin-objects -> inpaint-planes --flux -> frame-zero control

**There is no relief step in it.** So the six zones built hours after the verdict
never got the thing the verdict had just proven. Result, measured three days
later: **relief on 3 of 74 planes — 4% of the film.** Ryan, seeing the number:
*"whatever happened that it didn't get extended once we figured out that, hey,
cool, this technique works, should have been written in and built throughout."*

### The proof is the contrast, and it happened the same night

`bb4961c` — *"gen-geometry: zone tilts by role from z1 proven values"* — took the
OTHER z1 discovery and generalised it into a script. Tilt therefore reached every
zone. Relief did not.

**Same night, same project, two proven techniques. The one that got CODE spread
to 100% of the planes; the one that got a SENTENCE reached 4%.** Nothing else
differs. That is the whole mechanism, and it is not about diligence — it is about
which artefact the next run reads.

### The obligation

When an A/B produces a verdict, the verdict is not landed until **the builder**
has changed — the script, the config, the chain that will run next. Ask, before
closing it out:

1. **What will BUILD the next instance of this?** Name the file. If the answer is
   "someone will remember", the verdict has not landed.
2. **Change that file in the same commit as the verdict.** A verdict commit that
   touches only STATE.md or `knowledge/` is a half-commit.
3. **Make the coverage countable** ([[a-threshold-must-be-countable]]). This one
   now prints in `knowledge/status.sh` — every zone, every plane, the percentage —
   so a future session reads "3 of 74" in STATE.md instead of remembering a win.

The inverse is already law for removals: [[retirement-is-not-finished-until-the-routes-are-reread]].
This is the same rule for ADDITIONS, and additions are the easier one to miss,
because a win feels finished the moment it is proven.
