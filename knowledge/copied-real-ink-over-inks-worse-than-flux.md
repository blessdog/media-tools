---
id: copied-real-ink-over-inks-worse-than-flux
kind: refuted
conflict-key: does-copying-real-ink-beat-generating-it-for-disocclusion-fill
status: live
supersedes: []
mechanism: >
  Patch synthesis chooses donors by TEXTURE MATCH, and a hole beside dense
  hatching matches dense hatching. Shiftmap therefore has no notion of how much
  ink BELONGS in the band it is filling -- it stamps the neighbourhood's densest
  weave across the whole reach and repeats it. Copying real strokes guarantees
  every mark is one Wang Meng painted; it guarantees NOTHING about how many
  marks there are. Provenance and density are independent properties, and the
  hypothesis collapsed them.
verified-on: 2026-08-24
evidence:
  - jobs/wang-meng/evidence/2026-08-24-fill-AB-flux-vs-shiftmap.png
  - jobs/wang-meng/evidence/2026-08-24-invented-flux.json
  - jobs/wang-meng/evidence/2026-08-24-invented-shiftmap.json
asked-as:
  - should we copy real ink instead of using flux
  - can shiftmap replace the generative fill
  - is real ink better than flux for the holes
  - how do we stop the fill inventing brushwork
  - which fill method invents less ink
---

## "Real ink cannot over-ink" was the hypothesis. It over-inks nearly four times worse.

Written into [[a-deep-dolly-reveals-invented-material]] on 2026-08-24 as the
dominant lever, and tested the same day on z1's 12 planes at `--behind 100`
under the same `ab-ge-corrected` dolly, scored by the same arithmetic
(`journey/measure-invented.py`):

| | stack invented | invented INK, % of deepest frame | density in fill | 36px collar beside it | over-ink |
|---|---|---|---|---|---|
| flux-fill-pro | 33.30% | **1.85%** | 12.58% | 10.70% | **+17.6%** |
| shiftmap (real ink only) | 30.39% | **2.81%** | 19.46% | 11.76% | **+65.5%** |

Shiftmap invented **less area** and put **52% more fabricated brushwork on
screen**. It is not close, and the direction is the opposite of the one the
claim predicted.

## Why this was predictable, and was predicted twice already one level down

This is the third time on this painting that a texture statistic has been
trusted to carry a judgement it cannot make:

- [[clean-plate-donor-scope]] — shiftmap copied a TREE into the hole where a
  tree had been, and its own texture-energy metric (16.28 vs 16.35) read that as
  success.
- [[canopy-by-texture-statistics]] — no local texture statistic separates 牛毛皴
  on rock from 牛毛皴 on forest, because the painter did not draw them
  differently.
- here — texture match cannot tell "the right weave" from "far too much of the
  right weave".

**The general form: a donor rule fixes WHERE the marks come from and says
nothing about HOW MANY there should be.** Any fill judged by texture similarity
will bias toward the denser side of its neighbourhood, because a dense patch is
a better match for a busy context than a sparse one is.

## What this does NOT refute

flux is still inventing brushwork — 1.85% of the deepest frame, at +17.6%
against its own collar. This claim says only that swapping the fill SOURCE does
not fix it, and that the obvious swap makes it worse. The remaining levers are
camera (dolly less, or frame so the revealed band is out of the eye's path) and
fill quality, not fill provenance.

## Cost of the test, for whoever repeats it

159s to build the shiftmap stack (12 planes, local CPU, no API), ~4 min per
stack to render and score. No money. The flux stack was measured from the copy
already on disk.
