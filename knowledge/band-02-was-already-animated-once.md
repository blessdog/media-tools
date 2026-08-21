---
id: band-02-was-already-animated-once
kind: verdict
conflict-key: what-already-exists-for-the-ge-hong-bridge-scene
status: live
supersedes: []
scope: >
  The Ge Hong / deer / trestle-bridge scene, master box roughly
  [901, 10604, 2585, 13599]. Facts about assets on disk as of 2026-08-21.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-band02-bridge-proto.mp4
  - jobs/wang-meng/living/regions-proto.json
  - jobs/wang-meng/film/BAND02-approach.mp4
asked-as:
  - is the bridge scene already animated
  - what exists for ge hong
  - has anyone animated the bottom of the scroll
  - what is bridge-proto
  - can I reuse the ge hong cycle
---

## There is a finished 73-frame cycle of this scene, and it is NOT the deliverable

`jobs/wang-meng/living/cycles/bridge-proto/` — 73 frames, 720x1280, of exactly
the scene: Ge Hong with his fan on the trestle bridge, the pack animal with the
red-tipped bundle, the red-tipped tree, the stream with ripples, two porters
below. **Measured: 4.67% of the frame moves, loop seam 0.81 levels** — a real,
closed loop.

Provenance: commit `3146018`, salvaged from `living-both-final` and located in
the master by `locate-crop` at score 0.9576. Recorded in
`living/regions-proto.json` as `bridge-living-proto`, master box
`[901, 10604, 2585, 13599]`.

**Why it cannot ship, and this is the part that matters.** It is a **BAKED
720x1280 tile at k=2.34**. Three consequences:

- covering 1684 master px of width in 720 px, it upscales ~2.7x to fill a 1920
  frame — soft, and the file's own note says proto shots must render at k >= 2.34
  so it is never upscaled;
- water, figure and tree are fused into one tile, so nothing in it can be
  re-timed, re-gusted or turned off individually;
- it is `class: wave`, a single region, and carries no per-element cycles.

**So it is PROOF, not product.** It proves the scene reads as alive and it is the
reference for what "right" looks like. The native-res replacement was built
2026-08-21: z1 masks -> cycles -> register, giving 18 patches over 8 planes
including `trestle-bridge-ge`.

**What is still missing at native res:** the FIGURES. `g-ge-fan` and `g-deer`
exist in `regions.json` and NOT in `living-polys.json`, which is the file the
builder reads — see [[merge-the-two-region-catalogues-into-one]]. Their puppet
masks survive (`motion/mask/gehong/`, four parts: fan, sleeve, hem, head) but
their FRAME SEQUENCES do not — only `gh-fan.mp4`, `gh-walk.mp4` and
`deer-walk.mp4` remain, so the cycles must be re-rendered from the rigs through
`walk-figure.py`.

**One thing already settled and worth not re-deriving:** `walk-figure.py`'s
docstring records that a walk for Ge Hong invents nothing, because his robe
reaches the ground and his legs are never drawn — a robed walk in cel animation
IS the hem swinging, the body bobbing and the figure travelling. The warning
that a walk would require inventing a far leg is wrong for this figure.
