---
id: the-fov-floor-comes-from-the-focus-point
kind: law
conflict-key: how-is-a-shots-framing-bounded
status: live
supersedes: []
verified-on: 2026-08-24
evidence:
  - jobs/wang-meng/film/author-shots.py
  - jobs/wang-meng/film/check-holes.py
asked-as:
  - there is a cream bar at the edge of the frame
  - how close should a shot be framed
  - the frame runs off the edge of the plate
  - what fov should this shot use
  - background showing at the side of the shot
---

## A cream bar is arithmetic, not taste — compute the floor, never eyeball it

`render-parallax`'s scale equals fov exactly — measured 2026-08-24, a stated fov
of 0.96 produced 0.9607 screen px per plate px. So the visible window is
`width / fov` plate px across, and at fov ≈ 1 that is the WHOLE plate width. Any
focus point off centre therefore runs off the edge and fills the frame with
background. Measured on the first cut of the subtle reel: **400 px of cream on
the left of one shot, 624 px on the right of another** — a fifth to a third of
the frame, against PLAN.md's own benchmark of "no black frame or cream bar."

**The floor, from the focus point and nothing else:**

    fov >= width  / (2 * min(cx, W - cx))
    fov >= height / (2 * min(cy, H - cy))

take the larger, add a safety factor (1.08 in use). A subject near the plate
edge FORCES a tight shot, and that is honest: no wider framing of it contains
only painting.

**And a ceiling, because magnification is not free.** The plate is the master
downsampled by `k` (2.34 on this scroll), so a fov above `k` upscales past the
painting's own resolution. `author-shots.py` REFUSES such a shot rather than
rendering it soft — which is how `focus-trees` was caught needing fov 3.10 and
replaced with a subject that sits further inside the plate.

The general form: **when a framing constraint can be written as an inequality,
it belongs in the authoring tool, not in the reviewer's eye.**
