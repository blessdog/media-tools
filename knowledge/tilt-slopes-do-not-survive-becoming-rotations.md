---
id: tilt-slopes-do-not-survive-becoming-rotations
kind: refuted
conflict-key: can-render-parallax-tilt-values-be-reused-in-blender
status: live
supersedes: []
verified-on: 2026-08-26
mechanism: >
  geometry.json's tiltX/tiltY are PER-PIXEL SLOPES, consumed by render-parallax
  as a 2D shear over the image. blender-multiplane.py reinterprets the same
  numbers as REAL 3D ROTATIONS via atan(tilt * plate_dimension). That is a
  change of model, not a port, and the values do not transfer: on z3w they come
  out as 12.7 to 34 degrees. A plane rotated 34 degrees projects to cos(34) =
  83% of its height, stops covering the frame, and the void behind it renders
  as a black wedge. Measured on z3w frame 1 -- 0.00% black with no geometry.json,
  5.47% black with it, before the camera has moved at all.
evidence:
  - jobs/wang-meng/evidence/2026-08-26-blender-tilt-breaks-frame-zero.png
  - tools/blender-multiplane.py
asked-as:
  - why is there a black wedge in my multiplane render
  - can I reuse geometry.json in blender
  - do the plane tilts transfer to the blender renderer
  - frame zero does not match the painting
  - the cliff wall is leaning too far back
  - why does the plate not fill the frame
---

## The numbers were tuned for a different model, so they mean something else here

`layers.json` states the contract: *"frame zero must render byte-identical to
the source stack."* With `geometry.json` applied, 5.47% of z3w frame 1 is black
before any camera movement. The tilts break the contract on their own.

| plane | tiltX | tiltY | becomes rot Z | becomes rot X |
|---|---|---|---|---|
| gorge-cliff-nose | -0.00008 | -0.00020 | -12.7° | **-34.0°** |
| left-cliff-wall | -0.00008 | -0.00020 | -12.7° | **-34.0°** |
| gorge-wall-right | -0.00008 | 0.00020 | -12.7° | **34.0°** |
| resting-ledge | -0.00022 | 0 | **-31.8°** | 0° |
| upper-stream-rocks | -0.00012 | 0 | -18.7° | 0° |

**Overscan does not rescue it.** Dividing each axis by the cosine of its own
tilt is the obvious fix and was tried: 5.47% → 4.78%. It fails because a plane
rotated about its centre under PERSPECTIVE produces a keystone, not a uniform
shrink — the far edge contracts more than the near edge grows. A uniform scale
cannot invert a homography. Worse, scaling the plane scales the ARTWORK, so
even a working overscan would break frame zero a different way.

**What is actually true:** parallax comes from DEPTH SEPARATION between planes,
not from tilt. Tilt is a second-order refinement — it makes a plane turn as you
pass it. Flat planes in Blender give a correct frame zero AND real parallax.

**So: run the Blender lane without `--geometry` until the tilts are re-derived
IN THE 3D MODEL** — authored as degrees against a render, not carried over as
slopes. Re-deriving is the open work; reusing is refuted.

This is [[a-verdict-is-a-hypothesis-about-everything-else]] with a measurement
attached: a value proven inside one renderer is a HYPOTHESIS about any other.
