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
verified-on: 2026-08-24
evidence:
  - jobs/wang-meng/evidence/2026-08-24-invented-material-outlined.png
asked-as:
  - how deep can the camera go
  - why does the bridge look like mush up close
  - how much of the frame is inpainted
  - what limits the dolly
  - is the fill quality good enough
  - the ground around the figure looks wrong
  - does the inpainted material look like the painting
  - how much invented brushwork is on screen
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
2. ~~**Fill source**~~ — **REFUTED 2026-08-24, see
   [[copied-real-ink-over-inks-worse-than-flux]].** Copying real ink was tested
   against this exact camera and over-inks +65.5% against its collar where flux
   over-inks +17.6%. Swapping the source does not fix fabricated brushwork; the
   obvious swap makes it worse.
3. **Fill quality** — steps/guidance/resolution on the generative path.

**NOT a lever: `--behind`.** It is already ~16x more than the holes require.

## AMENDED 2026-08-24 — 14.7% is the wrong headline; 1.85% is the number

The first render of this filled every invented pixel solid magenta and Ryan
could not read it (*"a toddler went around with a pink marker"*). Rebuilt as
BOUNDARY OUTLINES with 1:1 crops — see
[[an-overlay-must-not-hide-the-thing-it-measures]] — and re-measured, the frame
splits in two:

| population | % of deepest frame |
|---|---|
| invented and BLANK (silk, wash, empty ground) | **12.86%** |
| invented and CARRYING INK (fabricated brushwork) | **1.85%** |
| total invented | 14.71% |

Ink = darker than its own 31px local median by >12 levels. The reproduction from
the marker stack is exact on the stack figure (2,660,184 / 5,329,050 = 33.3%);
the frame figure moved 14.29 → 14.71 because this pass rendered the marker with
`--fill black` throughout rather than mixing fills.

**And the fill is not timid — it is slightly over-inking.** Against the local
null (a 36px collar of real painting immediately around each invented region,
which controls for the flat robe and empty river that drag a whole-frame
average down): ink density **12.6% inside the fill vs 10.75% right beside it**.
flux is inventing about 17% more brushwork than its own neighbourhood carries.

So the trade is smaller than the headline made it sound and its shape is
different: the risk is not that a seventh of the painting is fake, it is that
~1.85% of the frame is fabricated STROKES, concentrated where the camera is
looking hardest.

## MEASURED 2026-08-24 — the cost curve, and "dolly less" is the weak half of lever 1

Scored at every 15th frame of the same dolly, from renders already on disk
(no new render, no cost). The two populations behave completely differently:

| camZ | total invented, % of frame | invented INK, % of frame |
|---|---|---|
| 0.00 | 0.00 | 0.00 |
| 0.13 | 1.69 | 0.44 |
| 0.21 | 3.50 | 0.90 |
| **0.33** | **7.26** | **1.61** |
| 0.42 | 7.57 | 1.49 |
| 0.55 | 9.58 | 1.51 |
| **0.70** | **14.63** | **1.85** |

**Fabricated brushwork flattens at camZ ≈ 0.33 and never really rises again.**
Going 0.33 → 0.70 DOUBLES the invented area (7.26% → 14.63%) and buys only
**0.24 points** of extra invented ink. Everything the deeper half of the dolly
reveals is blank silk and wash — material with no strokes in it to be wrong.

So "dolly less" costs a great deal of parallax to buy almost nothing: the
expensive population is already fully paid for by camZ 0.33. **What is left of
lever 1 is WHERE, not how far** — the invented material is densest immediately
around Ge Hong, and reframing so the revealed band falls outside the eye's path
is free. Chart: `jobs/wang-meng/evidence/2026-08-24-depth-cost-curve.png`.

**AMENDED AGAIN, same day.** This paragraph originally ended "Lever 2 (fill
source) still dominates for the same reason — real ink copied from elsewhere in
the scroll cannot over-ink." That was a hypothesis stated as a conclusion, and
it was refuted within the hour: see
[[copied-real-ink-over-inks-worse-than-flux]]. **Lever 1, the camera, is what is
left** — the invented material is densest immediately around the protagonist,
which is both the worst place for it and the cheapest thing to change.
