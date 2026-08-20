---
id: hinge-rest-is-a-noop
kind: law
conflict-key: what-must-a-cutout-rig-guarantee
status: live
supersedes: []
verified-on: 2026-08-20
---

> "this is broken." — Ryan, 2026-08-20, shown a pine with half its paint gone

**A cut-out rig at rest must be BIT-EXACT with the source. Zero degrees is a
no-op, and if it is not, every conclusion drawn about amplitude is measuring the
compositor instead of the wind.**

Three separate leaks were found in one rig, and none of them were visible as
"the compositor is broken" — they were visible as *the animation looks wrong*,
which sent the search to the swing parameter. Measured on
`s-pine-over-bridge`, 72,564px of canopy:

| leak | mechanism | cost |
|---|---|---|
| base was the clean plate | every masked pixel that did not become a card was deleted: the pale wash between leaf strokes, and 197 specks under `--min-px` | **54.2%** of the canopy |
| feather blurred inward | `GaussianBlur` on a binary mask drops alpha below 1 along the INSIDE of every edge, so `base*(1-al)+rgb*al` lerps each cluster's own outline toward a plate that has the ink removed | thinned every spray |
| the hole was the feathered extent | in the ramp band the card's alpha is < 1, so a clean-plate base there mixes plate with ink | the rest |

The fixes are all the same shape — **let the source stand wherever the card is
not certainly covering it**:

- base = SOURCE, with the clean plate substituted only under card footprints
- `al = max(solid, blur(solid))` so the feather ramps OUTWARD only
- vacate only where `solid`, never the ramp

Result: `swing 0` diff went 26,293px changed → 16,392 → **0 pixels, max 0,
mean 0.0000**. Ink loss at 3° went 16.4% → 1.5%.

## The rule this generalises

**Build the identity case before the interesting case.** A rig that transforms
something always has a parameter value at which it must do nothing, and that
value is the cheapest possible test — no rendering, no eyes, no opinion, one
subtraction. It was skipped here because the interesting case *ran*, produced
motion, and produced a number.

Sibling of [[foliage-motion]]; same family as the null-control discipline that
killed the parallax claim on 2026-08-13.
