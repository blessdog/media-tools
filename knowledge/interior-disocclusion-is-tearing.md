---
id: interior-disocclusion-is-tearing
kind: verdict
conflict-key: why-does-a-swinging-canopy-tear-the-painting
status: live
scope: >
  hinge-foliage cut-out cards over a clean plate, on 葛稚川移居圖. Measured
  2026-08-21 on z1's four foliage regions at swing 6 deg. The DENSITY figure is
  specific to this painting's leaf grammars; the edge-vs-interior rule is general
  to any cut-out canopy.
supersedes: []
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-why-sparse-canopies-tear.png
asked-as:
  - the leaves tear the painting when they move
  - why does one tree look worse than another
  - holes open up in the canopy
  - the clean plate shows through
---

**Disocclusion at a card's EDGE reads as movement. Disocclusion in a card's
INTERIOR reads as tearing.** Ryan, 2026-08-21, comparing two trees in the same
leg: *"On the first tree with the smaller leaves, I noticed it does more tearing
away of the painting. But on this tree up top, that's more like a pom frond
leaf, it just moves without showing any different color differentiation
behind it."*

**The one signal that separated them: ink density inside the moved area.**

| region | leaf grammar | ink density | ink that left bare ground | reads as |
|---|---|---|---|---|
| s-great-trees-lower | round cluster | 61.1% | 19% | **tearing** |
| s-great-trees-upper | round cluster | 59.6% | — | tearing |
| s-left-pines-z2 | needle fan | 72.9% | — | — |
| s-pine-over-bridge | needle fan | **81.8%** | 10% | clean |

At ~82% the neighbouring fronds are touching, so a swinging card can only expose
ground along its outline — a fringe, which the eye reads as the frond moving. At
~61% there is 39% bare silk interleaved THROUGH the mass, so every card opens a
hole in the middle of the canopy, and the eye reads that as the painting coming
apart.

**Two plausible explanations that the measurement killed, and both were mine:**

- *"the clean plate is worse behind the sparse tree."* Refuted: `s-pine-over-bridge`
  has the LARGEST plate-vs-source difference inside its moved area (54.9 mean
  levels, vs 44.1 for the tearing tree) and the largest vacated area (44,487px vs
  15,477px). The plate is not the variable.
- *"the card tip travels further than the gap to its neighbour."* Refuted: the
  clean pine has the HIGHEST travel/gap ratio of the four (0.52 vs 0.39). Gap
  size is not the variable either.

Both were arithmetically fine and aimed at the wrong quantity — see
[[perspective-falloff-is-hyperbolic-on-purpose]] for the same failure shape on a
different question.

**The control.** Interior disocclusion scales with how far a card leaves its own
footprint, so a low-density canopy needs a SMALLER swing than a dense one for the
same apparent liveliness. Density is measurable before anything renders:

    inked = (clean_plate.mean() - source.mean()) > 18
    density = inked[moved].mean()

Below roughly 0.70 the holes open in the interior. That is a per-region property
of the leaf grammar the painter used, not a global setting — the same reason
branch radius had to become per-tree
([[branch-radius-scales-with-the-tree]]).
