---
id: truck-parallax-must-saturate
kind: verdict
conflict-key: how-much-multiplane-separation-can-a-cut-up-painting-take
status: live
scope: >
  render-parallax.py --truck on a plane stack CUT FROM A SINGLE PAINTING
  (as opposed to cels painted separately). Measured 2026-08-21 on
  jobs/wang-meng/journey/z1, 13 planes, z 1.00..3.70, a 10s vertical rise.
supersedes: []
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-AB-pan-vs-truck-0.25.mp4
asked-as:
  - the parallax tore the picture apart
  - planes drifted out of register
  - paper gaps opened during the camera move
  - how much truck is too much
---

**A rate difference accumulates, so an uncapped truck destroys the picture on
any long move.** `--truck K` makes near planes translate `w = 1 + K(z_ref/z − 1)`
times faster than far ones. That is a RATE, so the resulting misregistration
grows with total camera travel and has no equilibrium.

Measured at K = 0.25 over a 10s rise: the camera travels ~1078 output px, near
planes run at 1.38x and far at 0.92x, so the nearest plane finishes **~500 px**
out of register with the farthest — half the frame height. Ryan, on the A/B:
*"Multiplane track worked at first, but then totally distorted the image."*
Both halves of that sentence are correct and they are the same fact: it worked
at first because the offset was still small.

**Why a real multiplane camera does not have this problem, and we do.** In a
real scene the depth range is small next to the camera distance, so `z_ref/z`
stays near 1. Here the depth is a fiction laid over a flat painting, `z` spans
1.0–3.7, and the planes are *cut from one image* — every plane boundary is a
cut line through continuous brushwork. Slide them and the cut lines open as
bare paper, and a cliff separates from the rocks that stand on it.

**Fix: saturate, because parallax is a VELOCITY cue.** Depth is read from things
moving at different rates as a move begins, not from where they end up. So ramp
at full differential and asymptote:

    d = TRUCK_MAX · tanh(d_raw / TRUCK_MAX)      # --truck-max, OUTPUT px

`tanh` is exactly linear near zero, so the full rate difference is present at
the start of every move and there is no knee where the clamp becomes visible.
Default 36 px. `--truck-max 0` restores the uncapped behaviour that broke.

**The acceptance test is unchanged and is the reason this is trustworthy:**
render the traverse twice, once with the plane depths and once with every plane
collapsed to one depth, and diff. Capped at 36 px the diff is still 0 px at
frame 0 (composition exactly as painted at rest) and ~100% of pixels once the
camera moves. A cap that killed the parallax would show up as a zero.
