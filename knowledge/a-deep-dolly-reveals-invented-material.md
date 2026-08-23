---
id: a-deep-dolly-reveals-invented-material
kind: verdict
conflict-key: what-limits-how-deep-the-camera-can-dolly
status: live
supersedes: []
scope: >
  jobs/wang-meng/journey/z1, 12 planes inpainted at --behind 100 with
  flux-fill-pro, under ab-ge-corrected (dolly 0.70 through a stack 3.30 deep,
  ending at fov 1.70). The PERCENTAGES are specific to this stack and this
  camera; the mechanism is general to any layered-depth stack with generative
  fills.
verified-on: 2026-08-23
evidence:
  - jobs/wang-meng/evidence/2026-08-23-a-seventh-of-the-frame-is-invented.png
asked-as:
  - how deep can the camera go
  - why does the bridge look like mush up close
  - how much of the frame is inpainted
  - what limits the dolly
  - is the fill quality good enough
  - the ground around the figure looks wrong
---

## The fill works. That is the problem.

Measured by flagging every pixel `inpaint-planes` invented — the alpha of
`layers-filled` minus the alpha of `layers-pinned` — tinting it, and rendering
the same camera:

| frame | camZ | invented pixels ON SCREEN |
|---|---|---|
| 0 | 0.00 | **0.00%** — the frame-zero invariant, nothing invented is visible at rest |
| 168 | ~0.44 | 7.03% |
| 335 | 0.70 | **14.29%** — 296,367 px |

**33.3% of the whole z1 stack is synthesised** (2,660,184 px against 5,329,050
painted). At the deepest dolly a seventh of what is on screen is flux output
rather than Wang Meng, and at fov 1.70 it is being shown at native scale.

**This supersedes nothing but it reframes
[[disocclusion-is-solved-the-boundary-tone-is-not]]:** holes are 0.026% of the
frame and invented material is 14.29%, a ratio of about 550:1. The fill is not
failing — it is succeeding, and its success is what you are looking at. What
was described as "a tonal halo at plane boundaries" is in fact large contiguous
invented regions: the river at upper left, the ground under and behind Ge Hong,
and the trestle bridge, which is exactly the "mush" seen at close range.

**So the limit on dolly depth is not geometry, it is generated-content
fraction.** Every extra unit of z buys parallax and spends painting. That is a
taste trade and it belongs to Ryan with the picture in front of him, not to a
threshold in a tool.

Three levers, and they are not exclusive:

1. **Camera** — dolly less, or frame so that revealed area falls outside the
   eye's focus. Currently the invented material is densest immediately around
   the protagonist, which is the worst possible place for it.
2. **Fill source** — `inpaint-planes`' own docstring says *"the source of
   patches matters more than the algorithm."* Copying real ink from elsewhere in
   the painting beats inventing it, bounded by
   [[clean-plate-donor-scope]].
3. **Fill quality** — steps/guidance/resolution on the generative path.

**NOT a lever: `--behind`.** It is already ~16x more than the holes require.
