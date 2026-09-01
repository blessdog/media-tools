---
id: the-blender-scroll-lane-was-rolled-back
kind: refuted
conflict-key: which-engine-renders-the-scroll-film
status: live
supersedes: []
verified-on: 2026-09-01
mechanism: >
  Blender was adopted for the scroll on 2026-08-25 as a directive and rolled
  back by Ryan on 2026-09-01 after eight days that produced no frame of film.
  It never won a comparison it was adopted to win, and the record says so in
  three separate measurements. (1) The single A/B against the hand-rolled
  renderer was CONFOUNDED: Blender and render-parallax differ by mean 20 at
  FRAME ZERO on z3w, so framing dominated the comparison and neither side was
  measuring parallax (commit 08a67cd). (2) The parallax deficit that motivated
  the whole move was then traced to a PLANNING bug, not a renderer limit --
  z3w's depths 10-13 sit BELOW a 16:9 frame, giving 1.00x landscape against
  1.12x portrait (commit 5d0ac71) -- and that is fixable inside the existing
  renderer by planning planes in frame. (3) The one capability Blender
  uniquely added, real displaced relief instead of a per-pixel warp, was built,
  rendered, and REJECTED by Ryan on 2026-08-26 as invisible at 5x on z3w
  (relief-in-blender-is-geometry-not-a-warp), with the companion verdict that
  flat cards are acceptable on their own. Meanwhile the cost was a full day
  spent on the donut tutorial and the live-socket infrastructure, and PHASE 0
  -- the cut -- was never started. The live routing claim
  depth-comes-from-the-breath never stopped being live throughout.
evidence:
  - archive/blender-scroll-lane/README.md
  - knowledge/relief-in-blender-is-geometry-not-a-warp.md
  - knowledge/depth-comes-from-the-breath.md
asked-as:
  - should we render the scroll in blender
  - which engine renders the film
  - can blender do the multiplane camera
  - why did we stop using blender
  - should I use blender for the parallax
---

Blender is the renderer for 葛稚川移居圖's multiplane camera, parallax and cutout work.

REFUTED — by Ryan, 2026-09-01:

> "The blender route for these scrolls is not the right method. That was an
> experimental detour that needs to be rolled back. But it's a learning lesson…
> we need to go back to actually rendering and stitching the videos with FFMPEG.
> What was working before."

**The live route, unchanged and never retired:**

```
tools/render-parallax.py --plane-fit  →  frames  →  ffmpeg  →  tools/stitch.mjs
```

See `depth-comes-from-the-breath` for the routing, which stayed `live` for the
entire duration of the Blender detour.

**This is a REVERSAL OF A DIRECTIVE, not a failure to follow one.** The
2026-08-25 directive to move into Blender was followed; it was then measured and
withdrawn by the person who issued it. Directive 0 in
`~/.claude/knowledge/directives.json` closes on that basis.

**What is NOT refuted, and must not be swept up with this:**

- Blender remains correct for other jobs in other repos — the molecular lane in
  `media-studio` renders through it and is untouched by this claim. The scope
  here is 葛稚川移居圖's film, nothing wider.
- The measured findings from the detour all survive as data and are indexed in
  `archive/blender-scroll-lane/README.md`. The artefacts are archived and still
  runnable, on Blender 5.2.1 LTS, which is the version every one of those
  numbers was taken on.
- **A hand-authored mark round-trips at 0px error.** That result is real and it
  is the strongest thing the detour produced. It is now homeless: see the cost
  section below.

**THE COST OF THIS ROLLBACK, stated so it is not discovered later.**
`blender-mark-scene.py` was the only live answer to
`how-is-a-region-outline-and-pivot-authored`, and its claim
`marks-are-authored-in-blender` had `supersedes: []` — it retired nothing, so
retiring it leaves that question with **no live answer**. Region outlines revert
to `living/living-polys.json` from the catalogue plus `hinge-foliage.py`'s
automatic cut, which is precisely what PHASE 0 exists to fix. It was also the
only answer this repo had to the still-open directive about an iPad/pencil
authoring surface. PHASE 0's remaining candidates are therefore the two that
need no Blender: scale the branch radius from crown size rather than stroke
width, or skeletonise the ink and cut at junctions rather than at thin necks.
