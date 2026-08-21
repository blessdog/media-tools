---
id: depth-is-authored
kind: verdict
conflict-key: where-does-depth-come-from
status: live
supersedes: []
scope: >
  Whole-painting depth on 葛稚川移居圖 and, by the same mechanism, any painting
  built on 散点透視 rather than a single vanishing point. It does NOT apply to a
  FIGURE at native crop, which is the measured exception.
verified-on: 2026-08-17
evidence:
  - jobs/wang-meng/motion/pan/report/depth-on-silk.html
asked-as:
  - can I use a depth model
  - estimate depth from the image
  - monocular depth on a painting
  - how do I get the depth map
---

**Depth is AUTHORED, never estimated.** Monocular depth on this painting scores
R² 48.9–55% against the image ROW — it is reading height-on-page, which in a
Chinese landscape is a compositional convention, not a distance. A model that
explains half its variance with "how far up the picture is this" has not seen
depth at all.

The exception is measured and narrow: **a figure at native crop has real
volume.** Ge Hong's relief is 0.0698 against a 0 null, and corr(depth, ink) is
−0.064 — near zero, meaning the model is completing SHAPE rather than tracing
darkness. So figures get model relief via `compose-depth --figure`; planes get
clicked depths from a human.

Migrated from `STATE.md` LAW 1.
