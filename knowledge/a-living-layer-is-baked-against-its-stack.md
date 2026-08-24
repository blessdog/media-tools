---
id: a-living-layer-is-baked-against-its-stack
kind: verdict
conflict-key: can-a-living-layer-be-moved-to-a-different-plane-stack
status: live
supersedes: []
scope: >
  jobs/wang-meng's living cycles and any patch cycle produced by
  build-zone-living.py. Measured 2026-08-24 moving z1's living layer from the
  12-plane stack onto a 4-plane merge of the same painting. The MECHANISM is
  general to any cel cycle rendered over a synthesised plate.
verified-on: 2026-08-24
evidence:
  - jobs/wang-meng/living/living-z1-coarse4.json
  - jobs/wang-meng/journey/remap-living.py
asked-as:
  - can I reuse the living layer on a different plane stack
  - move the cycles onto merged planes
  - why does the patch stamp paper over the painting
  - the living patches are in the wrong place
  - do I have to rebuild the cycles after changing planes
---

## A patch carries its plane's texture, not just its ink — so it cannot be relocated by arithmetic

The offsets look like the whole problem and are not. A patch's box is relative
to its plane's layer image, so moving it to a merged card is a shift of
`offset(member) - offset(merged)`. That much is true, and getting it wrong is
its own bug: **the living boxes are relative to the FILLED stack, not the pinned
one**, and `inpaint-planes --behind 100` moves a plane's offset by up to 100 px
(measured on z1: `left-bank-rocks` `[-100, -96]`, `right-hill-front-trees`
`[-97, -95]`). Reading the source offset from the pinned stack put every patch
that far off.

**Fixing the arithmetic did not fix the picture.** Checking each remapped patch
against the pixels it lands on, **12 of 21 sat on different painting** — and
some with an IDENTICAL box, which no offset correction can explain
(`left-cliff-wall__w-gorge-fall`, box `[551, 19]` in both stacks, mean absolute
difference 10.4 levels).

**The mechanism.** A cycle is rendered over its plane's own texture INCLUDING
that plane's inpainted band — `clean-plate` synthesises the ground behind the
ink so the ink has somewhere to move. Those pixels are opaque and they are
specific to the stack that produced them. On a differently-cut card the same
coordinates hold real painting, so the patch stamps one stack's clean plate over
another stack's brushwork. The result reads as a cream hole and is measured as
one, though nothing is actually transparent.

**So a living layer is an output of its plane stack, not an asset that sits
beside it.** Change the cut and the cycles must be REBUILT
(`build-zone-living.py`), never re-keyed. `remap-living.py` remains correct for
the offsets and is not sufficient by itself.

**Corollary that caught a second bug.** `render-parallax` pasted patches with no
mask, relying on the comment "patches carry the plane's own alpha, so pasting
them cannot change the plane's footprint." True only while a patch sits on the
plane it was cut from; a merged card broke it and the patch's transparent border
erased painting. Now pasted through its own alpha — verified byte-identical on
the 12-plane stack (0 of 2,073,600 px differ), so the invariant is enforced
rather than assumed.
