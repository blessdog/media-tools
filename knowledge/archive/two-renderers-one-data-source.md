---
id: two-renderers-one-data-source
kind: procedure
conflict-key: which-renderer-for-a-camera-move
status: superseded
supersedes: []
retires: depth-comes-from-the-breath
sibling: plan-planes-at-shot-scale
applies-when: >
  choosing between render-parallax and render-warp for a segment. TRAVERSES --
  lateral or vertical moves across the surface -- go to render-parallax
  --plane-fit on the sealed+pinned+filled card stack, because real occlusion is
  what a traverse reveals and cards give it.
not-when: >
  a PUSH straight into the surface. A push opens disocclusion holes a card stack
  cannot fill, so it goes to render-warp, where one sheet deforms and objects are
  held rigid by a stiffness map. Choosing cards for a push is how you get holes;
  choosing warp for a traverse is how you get strain in the wash.
route: >
  render-parallax.py --plane-fit --geometry ... (traverse) | render-warp.py
  (push). Both read the SAME plane stack -- one data source, two renderers, never
  two pipelines. A/B per segment and let Ryan's eyes pick; the template is
  jobs/wang-meng/motion/pan/CARDS-VS-WARP.mp4.
verified-on: 2026-08-17
asked-as:
  - cards or warp
  - which renderer should I use
  - holes appear when the camera pushes in
  - the wash stretches
---

> **SUPERSEDED 2026-08-21 by depth-comes-from-the-breath.** Both halves of
> the routing were measured wrong on this painting: cards give a traverse ZERO
> parallax at camZ=0 (flattening all 13 depths changed 0 of 2,073,600 px), and
> render-warp is rejected outright -- Ryan: "too extreme. It really distorts
> the painting." What survives is ONE DATA SOURCE, carried into the new claim.

Migrated from `STATE.md`'s SYNTHESIS PLAN, which Ryan asked for as "put it all
together". The load-bearing part is ONE DATA SOURCE: the moment the two
renderers read different stacks they become two pipelines, and a behaviour
difference between them becomes a bug in one or both (bible §5.1, convergence
over divergence).

The life pass — `animate-strokes` water, `hinge-foliage` foliage,
`walk-figure` figures — runs on the LOCKED camera, after the renderer is chosen.
Note that this ordering is now inverted by the MOTION BEFORE CAMERA law: living
cycles are authored first and the camera comes last. Kept here because the
renderer CHOICE is still per-segment and still A/B'd.
