---
id: plan-planes-at-shot-scale
kind: verdict
conflict-key: at-what-scale-are-depth-planes-planned
status: live
supersedes: []
scope: >
  Planning a depth-plane stack for a camera that will be CLOSE to the surface.
  Measured on z1. The finding is about the ratio between shot framing and
  planning framing, so it transfers to any zone whose camera pushes in.
verified-on: 2026-08-17
evidence:
  - jobs/wang-meng/journey/z1/points.json
  - jobs/wang-meng/motion/pan/report/zoom-to-flight.html
asked-as:
  - how many depth planes do I need
  - the parallax looks flat
  - not enough planes
  - plan the plane stack
---

**Plan the planes at SHOT scale, not at scroll scale.** The same region planned
from the whole scroll yields 3 planes with depth σ 0.098; planned at the scale
the shot actually frames, it yields 13 planes with σ 0.394 — four times the
depth spread from the same painting.

A stack planned at the wrong scale is not slightly worse, it is flat, because
the camera is close and the planes are far apart in the plan and adjacent on
screen. Run a density check (planes-per-frame, depth σ) per zone before
rendering.

Migrated from `STATE.md` LAW 2.
