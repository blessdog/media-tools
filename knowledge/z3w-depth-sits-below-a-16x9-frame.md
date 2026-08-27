---
id: z3w-depth-sits-below-a-16x9-frame
kind: verdict
conflict-key: why-does-the-z3w-dolly-read-as-a-zoom-not-parallax
scope: >
  jobs/wang-meng/journey/z3w/layers-filled, measured 2026-08-26 on both
  renderers. The MECHANISM -- a portrait plate framed by width into a landscape
  render cannot show a depth stack distributed down the plate -- applies to
  EVERY zone and should be checked per zone before any camera work.
status: live
supersedes: []
verified-on: 2026-08-26
evidence:
  - jobs/wang-meng/evidence/2026-08-26-z3w-depth-is-below-the-frame.png
  - jobs/wang-meng/evidence/2026-08-26-z3w-blender-vs-handrolled.mp4
asked-as:
  - why does my dolly look like a zoom
  - where did the parallax go
  - why do both renderers look the same
  - is there any depth in z3w
  - the multiplane has no depth
  - what aspect ratio should the render be
---

## The near planes are not in the picture, so there is no parallax to have

The plate is **2815 × 3368 — portrait**. `blender-multiplane.py` frames the
nearest plane BY WIDTH, and `render-parallax` does the same (fov 1.0 = "the
framing that fits the output width"). Into a 1920×1080 render that leaves a
visible band of only `2815 / 1.778 = 1584` px — **47% of the plate height**,
plate y 892…2476.

| plane | depth | y-range | in frame |
|---|---|---|---|
| gorge-cliff-nose | 9 | 1727–2135 | 100% |
| gorge-wall-right | 9 | 1964–2458 | 100% |
| left-cliff-wall | 9 | 0–3368 | 47% |
| upper-stream-rocks | 10 | 2580–3157 | **0%** |
| resting-ledge | 11 | 2813–3293 | **0%** |
| left-bank-rocks | 12 | 3023–3368 | **0%** |
| pine-over-bridge | 13 | 2943–3368 | **0%** |

**Only depth 9 is on screen — three planes at the SAME depth.** A dolly across a
single depth level is a zoom. That is what both renderers were faithfully doing.

**Measured, by isolating one plane at a time** (blanking the other PNGs to zero
alpha, leaving `layers.json` untouched so `dmin`/`dmax` and therefore every
plane's scale and distance stay identical):

| output | near grows | far grows | differential |
|---|---|---|---|
| 1920×1080 | *near plane is off-screen* | 1.2422× | ≈ **1.00×** (a zoom) |
| 1080×1920 | **1.3913×** | 1.2422× | **1.1200×** |

**So the aspect ratio is not a delivery decision, it is the parallax dial.** This
is the measured form of the canvas-aspect / 高遠 lever already suspected on this
painting. Before any camera work on a zone, check which depths fall inside the
frame; a zone whose stack is stacked VERTICALLY cannot show its depth in
landscape.

**Corollary for the renderer question.** Blender vs `render-parallax` could not
be told apart on z3w in 16:9 — correctly, because neither was being asked to
produce parallax. Any renderer comparison run in a framing that excludes the
depth measures nothing. See [[null-before-the-metric]] and
[[tilt-slopes-do-not-survive-becoming-rotations]], found the same day.
