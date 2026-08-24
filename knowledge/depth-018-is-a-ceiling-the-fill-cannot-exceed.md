---
id: depth-018-is-a-ceiling-the-fill-cannot-exceed
kind: verdict
conflict-key: how-much-camera-depth-can-this-plane-stack-take
status: live
supersedes: []
scope: >
  camZ on the 葛稚川移居圖 plane stacks at --z-step 0.30, all zones. A ceiling on
  the PEAK only; it says nothing about how much of a leg should sit near it,
  which is the separate and opposite failure recorded below.
verified-on: 2026-08-24
evidence:
  - jobs/wang-meng/evidence/2026-08-24-AB-canyon-depth.mp4
asked-as:
  - how much parallax can I push before it breaks
  - why did the painting tear when I increased depth
  - what is the maximum camZ
  - the canvas ripped when I pushed the camera
---

**camZ peak 0.18 is a ceiling. 0.45 tears the painting.**

Raised to 0.45 to buy visible parallax and measured immediately: check-holes
found 2 of 16 sampled frames holed, largest 4,198 px. Ryan, on the A/B: *"the
before on the left is way better, it's the only way to do it. Whatever you did
to the right tore the canvas, tore a huge asshole in the canvas."*

MECHANISM. Depth separation is what opens disocclusion: the further the near
plane travels relative to the far one, the wider the band of ground behind it
that was never painted. The inpainted band in layers-filled has a finite reach,
so past some separation the camera exposes territory the fill does not cover and
the frame shows flat ground where painting should be. The ceiling is therefore a
property of THE FILL WIDTH, not of taste, and raising it requires re-filling the
stack, not re-authoring the path.

AND THE OPPOSITE FAILURE IS REAL TOO, so do not read this as "less is safer".
The shipped breath was a raised cosine from 0 to 0.18 that passed THROUGH zero
once per period, and per frame 13-31% of every leg sat at camZ < 0.02 -- which
is a pan by construction (see depth-comes-from-the-breath: collapsing all 13
plane depths onto one changed 0 of 2,073,600 px). Ryan on that render: *"no
parallax, just boring ass, single pan ken burns shot... that was a solved
problem. We didn't need to engineer this entire project for over two weeks."*

THE ANSWER IS TIME AT DEPTH, NOT MORE DEPTH. Keep the 0.18 peak and raise the
FLOOR so the breath never settles mid-leg, tapering to 0 only across the ~2.5s
seam where consecutive legs dissolve:

    peak camZ      mean camZ    frames at camZ<0.02
    0.18 to 0      0.085              13-31%      shipped, reads as a pan
    0.45 floored   0.251               4-10%      TEARS
    0.18 floored   0.107               7-16%      both problems avoided

Same maximum plane separation that has always been safe, 26% more mean depth,
and the flat stretches cut roughly in half.
