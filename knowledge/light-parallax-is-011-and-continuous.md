---
id: light-parallax-is-011-and-continuous
kind: verdict
conflict-key: how-much-z-and-in-what-shape
status: live
scope: >
  Camera paths over the wang-meng plane stacks, render-parallax --plane-fit
  --z-step 0.30. The NUMBER is specific to this stack (z spans 1.0..3.7); the
  SHAPE — continuous rather than spiked — is general.
supersedes: []
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/film/LEG-LIGHT-z3w.mp4
  - jobs/wang-meng/film/paths/leg-light-z3w.json
asked-as:
  - how much z should a leg use
  - what is the light parallax setting
  - how much depth is too much
  - the parallax reads as a zoom
---

**z ramps to about 0.11 with rotations under 0.08, CONTINUOUSLY across the
whole leg.** `camera-light-parallax` is the law — *"lightly and tastefully"* —
and this is the number it means. The law alone did not stop a 0.18 breathe on
2026-08-21, because "light" is not a quantity.

Every authored path in the project, by peak z:

| path | z max | |
|---|---|---|
| `path-meander`, `path-push-deep` | 0.45 | the deep experiments |
| `leg-slow-z1`, `path-push-ge` | 0.26 | the Ken Burns era, rejected |
| `path-bridge-float`, `gorge-push` | 0.24 | |
| a breathe tried 2026-08-21 | 0.18 | too much |
| `path-bridge-parallax` | 0.14 | |
| **`leg-light-z3w`** | **0.11** | **built to the law, names it in its note** |
| `rise-*` traverses, 2026-08-21 | 0.00 | flat — read immediately as a pan |

**The SHAPE matters more than the number, and is the easier thing to get
wrong.** `leg-light-z3w` ramps z from 0 to 0.11 across a single 26s rise, so
depth is present the whole time and never announces itself. The `rise-*` paths
put z at exactly 0.000 for every traverse and spiked it to 0.10 only inside the
approach moments — absent, then lumpy. That is worse than either extreme: the
traverse is provably flat (collapsing all plane depths changed 0 of 2,073,600
pixels) and the spikes read as zooms because they are the only depth in the
shot.

So: **spread the same small amount of z over the whole leg** rather than
spending it in bursts. Depth felt continuously is invisible; depth delivered in
a spike is a move.

**Authoring, both constraints together.** Keys are POSES, not samples —
`sample()` is piecewise smoothstep and eases to zero velocity at every key, so
`leg-light-z3w`'s 6 keys over 26s (~4.3s apart) is the right density and 21
keys over 10s stutters. And `--relief` only engages when `camZ != 0`, so a leg
with a flat traverse gets no within-plane shape either — another thing the
zero-z traverse silently switched off.

**TWO SHAPES, TWO SETTINGS — verdict 2026-08-21.** The 0.11 above is for a
MONOTONIC RAMP across a long leg (`leg-light-z3w`, 26s). A BREATH — in and back
out over ~10s — carries more without reading as too much: Ryan on the smooth
3-pose breathe at **z 0.18**, *"Breathe smooth is looking good. Now I feel like
we're starting to finally make a little bit of traction."* The same 0.18 had
been rejected an hour earlier at 21 keys, which was the stutter and not the
amplitude. So amplitude is not the whole ceiling; a value that returns to zero
buys more than a value that arrives and stays.

  ramp across a long leg   z -> 0.11, ends at the peak
  breath over ~10-25s      z -> 0.18, returns to 0

**The test that decides it stays Ryan's:** would this move be worth watching if
the living layer were switched off? If yes, it is too much camera.
