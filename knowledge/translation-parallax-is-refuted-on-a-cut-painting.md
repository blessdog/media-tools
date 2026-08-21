---
id: translation-parallax-is-refuted-on-a-cut-painting
kind: refuted
conflict-key: can-a-truck-produce-parallax-on-a-plane-stack-cut-from-one-painting
status: live
supersedes: [truck-parallax-must-saturate]
mechanism: >
  The planes are a decomposition of ONE continuous composition, not independent
  cels, so plane B's brushwork is the literal continuation of plane A's and a
  figure stands on a ledge that lives on a different plane. Relative translation
  therefore asserts a geometry the painting does not have, and it is permanent:
  the offset is an accumulated rate with no equilibrium, so it grows with camera
  travel and never returns. Capping it with tanh does not tame the technique, it
  deletes it -- the raw displacement is hundreds of px against a 36px ceiling, so
  every plane saturates within ~2s and the result is a rigid translation plus a
  frozen misregistration held for the rest of the shot (measured: top strip -36px,
  bottom strip -35px, i.e. no differential left at all).
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-AB-pan-vs-truck-0.25.mp4
  - jobs/wang-meng/evidence/2026-08-21-AB-pan-vs-truck-capped36.mp4
  - jobs/wang-meng/evidence/2026-08-21-truck-diff-map.png
asked-as:
  - can I slide the planes to get parallax
  - multiplane truck on the scroll
  - why does moving the planes ruin the painting
  - near planes faster than far planes
---

**Sliding the planes of a painting past each other cannot produce parallax,
because the planes are a DECOMPOSITION of one continuous composition, not
independent cels.** The cliff plane is the literal continuation of the rock
plane's brushwork. Any relative translation is a permanent lie about the
painting's own geometry, and it is legible as damage long before it is legible
as depth. Ryan, at 36px of cap: *"it still really distorts the painting and
fucks it up."*

`render-parallax.py --truck` was built, measured, and is retired. Both of its
failure modes are worth keeping because they look like different bugs and are
the same fact:

**Uncapped (K = 0.25).** A rate difference has no equilibrium. Over a 10s rise
(~1078 output px of travel) the nearest plane finished ~500 px out of register
with the farthest — half the frame height, with the cut lines opening as paper.

**Capped at 36 px (tanh).** Worse in an instructive way: the raw displacement is
hundreds of px against a 36 px ceiling, so nearly every plane saturates within
about two seconds and then holds. Measured band-by-band, pan vs truck:

| frame | top strip | bottom strip |
|---|---|---|
| 00060 | −29 px | −34 px |
| 00120 | −36 px | −35 px |
| 00180 | −36 px | −36 px |
| 00239 | −35 px | −36 px |

Near and far shifted **identically**. The cap converted the parallax into a
rigid translation plus a frozen ±36 px misregistration between plane groups,
held for the rest of the shot. No gaps: 0 pixels became paper, so the damage was
purely positional. A saturating cap does not tame this technique, it deletes it.

**Why a real multiplane camera does not have this problem.** Disney's foreground
cel is a separate painting, authored to sweep past — a branch, a fence post. Its
relationship to the background is not asserted by the artwork. Here it is: a
figure stands ON a ledge that lives on another plane.

**Use instead: depth from z.** Differential scale under `--plane-fit` is a
function of camera POSITION, not accumulated travel: it is exactly 1.000 for
every plane at `camZ = 0`, so the composition is precisely as painted whenever
the camera is at rest, and every departure returns. At `camZ = 0.18` on the z1
stack the nearest plane scales 1.220 and the farthest 1.051 — a 16% differential
— and the same null test passes (0 px at frame 0, ~100% once moving). The slow
z oscillation that spends this without a net push is already in Ryan's own shot
vocabulary: **breathing**.

**The transferable rule:** on a plane stack cut from one image, parallax may
change how big things are relative to each other, never where they are relative
to each other. Scale returns; offset accumulates.
