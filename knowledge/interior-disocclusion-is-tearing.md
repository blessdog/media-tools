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

**FOUR CONTROLS MEASURED 2026-08-21, ALL FOUR REFUTED.** The tearing is real and
the edge/interior distinction above holds, but nothing tried so far removes it:

| tried | reasoning | measured on s-great-trees-lower at the gust peak |
|---|---|---|
| **smaller swing** | less travel, less disocclusion | 6 deg tears 16.9% of the tree's ink; 2 deg still tears 8.2%. 3x less rotation buys half the tearing, and the curve saturates — the holes are already open at 1.6 deg. |
| **`--ink-close` 3, 5, 8** | seal the lace so a card is opaque | 15.8 / 16.5 / 16.5%. And it destroys the decomposition: 7 cards -> 3 -> 1. On a sparse canopy the gaps WITHIN a spray and the gaps BETWEEN sprays are the same size, so one close does both jobs. |
| **`--whole-mask` (opaque cel)** | a real cel is opaque inside its outline, so it carries its own negative space | **17.3% — worse than `--from-ink`**, and still 90% interior. |
| **tone-matching the plate to the silk** | the exposed ground reads as a different colour | the systematic cast is only 5.6 levels and the per-pixel scatter is 13, so a global shift cannot reduce it; correcting the measured cast OVERSHOT to -8.1. Confined correctly (0 px outside the vacated footprint changed) — it just does not help. |

The null holds throughout: at swing 0, **0 px** of ink goes bare, so this is
caused by movement and not by orphan ink the decomposition failed to carry.

**What is left standing.** Comparing the two plates side by side
(`evidence/2026-08-21-the-plate-is-the-wrong-colour.png`), the pine's clean plate
is genuinely bare silk while the great trees' plate still holds a ghost of
canopy structure. That points at the PLATE'S CONTENT rather than its colour or
the card geometry — untested. Density remains the best available PREDICTOR of
which canopies will tear; it is not yet established as the cause, and the
`density < 0.70 -> use a smaller swing` rule stated here on the morning of
2026-08-21 is withdrawn as measured-false.
