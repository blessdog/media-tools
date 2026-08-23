---
id: disocclusion-is-solved-the-boundary-tone-is-not
kind: verdict
conflict-key: what-is-actually-wrong-at-a-plane-edge-when-the-camera-moves
status: live
supersedes: []
scope: >
  jobs/wang-meng/journey/z1's 12-plane stack, inpainted at --behind 100, under
  the ab-ge-corrected path (dolly 0.70 through a stack 3.30 deep -- deeper than
  any camera the film has shipped). Says nothing about a stack that has NOT been
  through inpaint-planes.
verified-on: 2026-08-22
evidence:
  - jobs/wang-meng/evidence/2026-08-22-holes-at-deepest-dolly.png
asked-as:
  - the plane edges are opening when the camera moves
  - do I need a bigger behind for a deeper dolly
  - how wide are the disocclusion holes really
  - what is that halo around the figure
  - is disocclusion still a problem
  - why does the fill look like mush
---

## The holes are 6px. The visible defect is something else entirely.

**Predicted and wrong.** Reasoning from `inpaint-planes`' recorded measurement (a
0.45 dolly opened holes over 6.0% of the last frame), I predicted a 0.70 dolly
would need roughly 160px of fill against the 100px that exists — the differential
goes 1.45x to 2.27x. **Measured at the deepest frame: widest hole run 6px, 545
px total, 0.026% of the frame.** Wrong by a factor of 25. The existing
`--behind 100` is about 16x more than this camera needs, and no rebuild of the
fills is required for a deeper dolly.

**How the measurement was made**, because the first attempt was wrong in an
instructive way: render the SAME camera twice changing only `--fill`
(paper vs black) and diff. Pixels that differ ARE gaps — no threshold, so dark
ink can never be mistaken for a hole.

**The first run reported 59% holes and it was measuring the PILLARBOX.** At
fov 0.40 the frame is wider than the plate, so the off-canvas surround differs
between the two fills exactly like a gap does. The tell was in the trend, not
the number: holes shrank monotonically as the camera pushed in, and disocclusion
does the opposite. Restricting to frames where the frame is fully inside the
painting — which is also where the dolly is deepest — gives the real figure.

**The rule that generalises: restrict a difference measurement to the region
where the defect is POSSIBLE.** A difference measured outside it is a different
phenomenon wearing the same signature. Having a null ([[null-before-the-metric]])
was not enough; the null was correct and the REGION was wrong.

## What is actually wrong

With the holes marked magenta the frame shows them as scattered single dots —
nothing structural. What IS visible, and what "the edges are opening" actually
refers to:

- **a tonal halo around each filled plane**, with a hard step where the plane's
  footprint ends — the fill does not match the plate behind it. See the existing
  `evidence/2026-08-21-the-plate-is-the-wrong-colour.png`, i.e. this was already
  seen once and not connected to camera movement.
- **visible inpaint texture** where a large hidden region was synthesised (the
  trestle bridge reads as mush at close range).

So the next fix is **boundary tone matching and fill quality**, not more fill
width. Those are different tools: `clean-plate` donor scope and `inpaint-planes
--method`, not `--behind`.
