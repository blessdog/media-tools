---
id: frame-zero-is-not-byte-exact-under-plane-fit
kind: verdict
conflict-key: how-to-check-that-a-fill-painted-nowhere-visible
status: live
supersedes: []
scope: >
  render-parallax --plane-fit over a stack that has been through
  inpaint-planes --behind N. Measured on jobs/wang-meng/journey/z1, 12 planes,
  --behind 100, both flux and shiftmap fills. The MECHANISM is general to any
  renderer that resamples a plane whose box has been grown.
verified-on: 2026-08-24
evidence:
  - jobs/wang-meng/journey/check-frame-zero.py
asked-as:
  - frame zero is not identical after filling
  - did the inpaint paint somewhere visible
  - how do I know the fill did not leak
  - the frame zero control fails
  - is the disocclusion fill visible at rest
---

## The byte-exact control has never been byte-exact, and that hid its own blind spot

`inpaint-planes`' docstring: *"FRAME ZERO MUST COME OUT BYTE-IDENTICAL. If it
does not, the tool painted somewhere it had no business."* Measured against the
pre-fill stack through the actual render path:

| comparison | differing px | % of frame | components | largest |
|---|---|---|---|---|
| pinned vs flux-filled | 39,210 | 1.89% | 22,162 | 49 px |
| pinned vs shiftmap-filled | 40,130 | 1.94% | 22,342 | 49 px |

**Both fills differ by the same amount, so the cause is the fill EXISTING, not
which fill.** `--behind` grows each plane's layer box, `--plane-fit` resamples
on the shifted grid, and silhouette edges land on a different subpixel phase.
The differing pixels are on edges: median |grad| **35.9** against **0.0** at
randomly chosen pixels; 69.1% sit above |grad| 20 against a 29.5% baseline.

**Nothing leaked. The problem is that the test could no longer tell.** 39,210 px
of edge shimmer is a comfortable hiding place for a genuine leak of a few
thousand pixels, and a byte-exact assertion that fails every single time gets
read as noise and then ignored — which is how a control dies.

## The restatement, which the render path can actually satisfy

Edge shimmer is thousands of tiny components; a leak is contiguous. So threshold
on **component area**, never on the total:

    leak = any connected difference component >= 200 px

200 is CHOSEN, at about 4x the largest edge artifact MEASURED here (49 px).
`journey/check-frame-zero.py` implements it, reports, and exits 0
([[checks-start-in-observation]]); `--strict` arms it.

**Why area and not a gradient mask.** Masking out strong-gradient pixels would
also have blinded the check to any leak that happened to land on an edge — which
is exactly where a plane's fill band lives. Area separates the two populations
without discarding a region of the picture.

Both z1 stacks pass the restated check: **0 leak components.**
