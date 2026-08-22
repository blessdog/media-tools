---
id: space-planes-in-disparity-not-depth
kind: refuted
conflict-key: how-should-depth-levels-map-to-z
status: superseded
scope: >
  render-parallax.py --plane-fit, any plane stack. The MECHANISM is general to
  any renderer whose scale law is z/(z-camZ); the measured 12.3:1 figure is z1's
  10 depth levels over z 1.00..3.70.
supersedes: []
retires: --z-space disparity
mechanism: >
  The hyperbolic scale response is not a defect to be corrected -- IT IS
  PERSPECTIVE. Evenly spaced physical planes genuinely do give a strong
  near-field falloff, because that is what a real camera does. Linearising the
  response makes every plane separate by an equal amount, which reads as a
  DIORAMA rather than a landscape: uniform separation is the signature of flat
  cards at even spacing, exactly the thing depth is supposed to hide. The 12.3:1
  step ratio measured on z1 is therefore the correct number, not the bug. Ryan,
  on the side-by-side: "From that shot, the even in depth actually wins."

verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-AB-zspace-linear-vs-disparity.mp4
asked-as:
  - the foreground pops out too much
  - the background does not move enough
  - depth looks smooth but unnatural
  - how should plane depths be spaced
---

> **REFUTED 2026-08-21, by the A/B it asked for.** Ryan: *"From that shot, the
> even in depth actually wins."* The reasoning below is arithmetically correct and
> aimed at the wrong target -- see `mechanism`. Kept for the measurement and for
> the trap, which is that a mathematically even distribution LOOKED like an
> obvious improvement and was tested only because a rendered A/B was cheap.

**Space depth planes evenly in 1/z, not evenly in z.** Ryan on THE RISE v1,
2026-08-21: *"there were certain scenes where the mountain comes out way farther
and zoom in way closer than the background. Which it's still smooth but it's not
natural."* He diagnosed it correctly and proposed the fix himself — *"mathematical
algorithms that evenly displace, maybe logarithmically."*

**Mechanism.** `z = z_near + (max_depth − depth) · z_step` spaces planes evenly
in z. But perspective scale is `z / (z − camZ)`, a **hyperbola**. Even steps in z
therefore produce wildly uneven steps in scale — the whole differential piles onto
the nearest card while the far planes are effectively glued together.

Measured on z1 at the breath peak (camZ 0.18), 10 depth levels:

| | front step | back step | worst : best |
|---|---|---|---|
| even in z (before) | 0.0588 | 0.0048 | **12.3 : 1** |
| even in 1/z (after) | 0.0213 | 0.0164 | **1.3 : 1** |

And the total near/far differential is **identical either way — 1.1602**. This is
not less depth, it is the same depth distributed evenly. That is what makes it
the right fix rather than a reduction.

**Why 1/z specifically, rather than log.** Scale is `1/(1 − camZ·w)` where
`w = 1/z`, so to first order the scale increment is proportional to the increment
in **disparity**. Linear in disparity linearises the response exactly; log is the
right family and a close approximation. This is the same reason depth buffers and
stereo rigs are parameterised in 1/z.

**Route.** `--z-space disparity`. Default stays `linear` and reproduces every
earlier render **byte-identically** (verified: 0 px differ on frames 0, 635, 1270
of the z1 leg). Endpoints are untouched, so `--z-near` and `--z-step` keep their
meaning and only the interior spacing changes.

**The general lesson.** When an effect is distributed across N elements and the
response law is non-linear, spacing the elements evenly in the INPUT is almost
never what you want — space them evenly in the RESPONSE. "Smooth but not natural"
is the perceptual signature of exactly this: nothing jumps, and yet the budget is
spent in the wrong place.
