---
id: canopy-by-texture-statistics
kind: refuted
conflict-key: can-texture-separate-tree-from-rock-at-distance
status: live
supersedes: []
mechanism: >
  At distance Wang Meng's 牛毛皴 (hemp-fibre texture strokes) covers rock and
  forest alike, so the ridge shoulder genuinely IS a dense, compact,
  high-contrast field of ink. No LOCAL TEXTURE STATISTIC can separate them,
  because the painter was not drawing them differently. What separates them is
  plain TONE.
verified-on: 2026-08-20
asked-as:
  - separate trees from rock
  - tell forest from cliff
---

Three discriminators tried on `s-summit-crest-left`, all failed. This is the
tabu list -- do not retry these.

    density + compactness, tuned window     36-46% of the crop, whole shoulder
    high-pass texture energy, plate res     0.64% -> 0.63% of plate: no effect
    high-pass texture energy, master res    45.9% of crop: no better
    local contrast, master res              44.8% -> 29%: still the shoulder

The resolution hypothesis was also wrong and worth recording: the summit tree
ribbon is ~50 master px tall and the plate is a 2.34x downsample, so "the
analysis window is bigger than the feature" looked like a complete explanation.
Running the identical read at master resolution changed nothing.

Superseded approach, not a superseded claim: `canopy-read-distant` solved it
with tone.
