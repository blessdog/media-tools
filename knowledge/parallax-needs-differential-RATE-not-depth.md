---
id: parallax-needs-differential-RATE-not-depth
kind: verdict
conflict-key: what-actually-produces-parallax-on-a-traverse
status: live
scope: >
  render-parallax.py with --plane-fit, on any plane stack, for any TRAVERSE
  (a camera move where z stays constant). Measured 2026-08-21 on
  jobs/wang-meng/journey/z1, 13 planes at depths 9..18, z 1.00..3.70.
supersedes: []
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-AB-pan-vs-truck-0.25.mp4
asked-as:
  - why does the parallax look like a pan
  - the plane stack is not doing anything
  - how do I get 2.5D on a vertical rise
  - it looks like the same flat camera move
  - multiplane camera
---

**Building a deep plane stack does not produce parallax. Making the planes
translate at DIFFERENT RATES does.** Under `--plane-fit` at `camZ = 0`, every
plane gets the identical scale *and* the identical sampling offset, so a
thirteen-plane stack translates as one sheet. That is a pan, however much depth
the stack has.

Proven by the null, and the null is the whole point: render the same traverse
twice, once with `--z-step 0.30` and once with **every plane collapsed to one
depth** (`--z-step 0.0`).

| | frame 0 | frame 120 | frame 239 |
|---|---|---|---|
| before (`--truck 0`) | 0 px differ | **0 px differ** | **0 px differ** |
| after (`--truck 0.25`) | 0 px differ | 2,072,801 px (100%) | 2,071,983 px (99.9%) |

Zero of 2,073,600 pixels. The depth separation contributed *nothing*, and no
amount of authoring more planes would have changed that.

**Mechanism.** `screen_scale()` returns `fov * (z_rest / (z_rest - camZ))`. At
`camZ = 0` that is `fov` for every plane, by design — `--plane-fit` exists so
depth separation costs nothing at rest. But the sampling offset
(`cx = camX - (W/2)/s - ox`) was equalised along with it. The docstring's
promise that separation "shows up as differential motion once the camera moves"
is true only of motion in **z**. A traverse moves in x and y, so it got none.

**Rate is what carries a truck; scale is what carries a dolly.** That is the
distinction the renderer was missing, and it is the multiplane camera (Disney,
1937, *The Old Mill* — already this project's reference look). Physically
separated planes; when the camera trucks past them, near planes cross the frame
faster than far ones. Scale correct, rate different.

**The fix**, `render-parallax.py --truck K`, anchored at the path's first key so
the composition is exactly as painted at rest:

    w(z)   = 1 + K * (z_ref / z_plane - 1)      z_ref = median plane depth
    camX_p = camX0 + (camX - camX0) * w(z)      same for camY

`K = 0` reproduces every earlier render byte-identically. `K = 0.25` on the z1
stack gives 1.38x near and 0.92x far. **0.15–0.35 is the useful band on a stack
whose z spans 1.0–3.7**; above that the near planes tear away from the far ones
and the gaps at the plane edges start to show.

**The general lesson, which is why this is a verdict and not a bug report:**
a null test that a system passes *by doing nothing* is the only way to catch an
effect that was never applied. "It has thirteen planes at real depth" was true
the whole time and completely irrelevant. Before believing any depth effect,
flatten the depth and diff the pixels.
