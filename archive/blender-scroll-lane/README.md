# The Blender scroll lane — rolled back 2026-09-01

**Status: RETIRED as the route. KEPT as data.**

Ryan, 2026-09-01:

> "The blender route for these scrolls is not the right method. That was an
> experimental detour that needs to be rolled back. But it's a learning lesson.
> We can genuinely keep mechanisms in the future, or the ability to know about
> this experiment and what worked, but we need to go back to actually rendering
> and stitching the videos with FFMPEG. What was working before."

This reverses the directive of 2026-08-25 ("move the multiplane camera /
parallax / cutout work into Blender"). Archived rather than deleted under LAW
#0.6 — the store keeps the CLAIM, this folder keeps the ARTEFACT, so any of it
can be RE-RUN when a premise changes (a new Blender, a new add-on). *"This
failed on Blender 5.2.1"* is not *"this fails."*

---

## What the live route is again

Unchanged and never retired — `knowledge/depth-comes-from-the-breath.md` stayed
`live` the whole time and still says *"render-parallax --plane-fit is the
renderer for everything."*

```
tools/render-parallax.py --plane-fit   →  frames
ffmpeg                                 →  a clip
tools/stitch.mjs                       →  the film
```

Authored by `jobs/wang-meng/film/author-rise.py`, built by
`jobs/wang-meng/film/build-rise.sh`.

`render-parallax.py`'s own docstring already carries the reason it wins, and it
is not a preference: *"THE CAMERA IS A REAL PINHOLE, not a stack of sliding
cards. Each plane sits at its own z, and screen scale is f/(z - camZ)."* The
depth model was never the thing Blender was needed for.

---

## What is in here

| file | was |
|---|---|
| `tools/blender-multiplane.py` | the multiplane renderer — built the plane stack headless and rendered camera moves |
| `tools/blender-mark-scene.py` | built a Grease Pencil scene for marking regions by hand |
| `tools/blender-read-marks.py` | read those strokes back as polygons in MASTER px |
| `tools/snap-mark-to-ink.py` | snapped a drawn loop to the existing ink boundary |
| `tools/blender-live.py` | a socket into a RUNNING Blender, with checkpoint/diff/screenshot |
| `kit-blender-live/` | the donut recipes that exercised the live socket |

---

## What was MEASURED — the part worth keeping

Kept because a dead end is data, and because each of these transfers to any
future 2.5D lane regardless of renderer.

| finding | measurement | where it lives |
|---|---|---|
| **Relief is not free, and not visible here** | z3w's five relief maps as real displaced geometry, judged at 5x. Ryan: not worth enabling | `knowledge/relief-in-blender-is-geometry-not-a-warp.md` |
| **Flat cards are acceptable on their own** | the relief verdict was "no difference", NOT "both broken" | commit `2c6a98e` |
| **The A/B was confounded and never showed a winner** | Blender vs hand-rolled on z3w differ by **mean 20 at FRAME ZERO** — framing, not parallax, dominated the comparison | commit `08a67cd` |
| **The flatness was a FRAMING bug, not a renderer limit** | z3w depths 10–13 sit BELOW a 16:9 frame: **1.00x landscape vs 1.12x portrait** | commit `5d0ac71` |
| **Tilts do not survive becoming 3D rotations** | 34° of lean, 5.47% black at frame zero | commit `57b2b74` |
| **Blender 5.x broke actions and EEVEE** | slotted actions killed `action.fcurves`; `EEVEE_NEXT` is `EEVEE` again | `knowledge/blender-5x-broke-actions-and-eevee.md` |
| **register() is not working** | two add-ons passed `register()` and failed on first real call | `knowledge/registering-is-not-working.md` |
| **Frame By Plane cannot run headless** | **63 of 353** operators register in `-b`, **zero** importers | `knowledge/frame-by-plane-importers-are-gui-only.md` |
| **A hand mark round-trips exactly** | drawn loop → polygon in MASTER px at **0px error** | commit `9d0a3f8`-adjacent, 2026-08-25 |

**The honest summary of the detour:** Blender never won a clean comparison
against `render-parallax.py`. The one A/B run was confounded by framing, and the
one capability Blender uniquely added — real displaced relief — was measured and
rejected by Ryan on 2026-08-26. The parallax deficit that motivated the move was
traced to depth planes sitting below the frame, which is a **planning** bug
fixable in the existing renderer.

---

## What rolling this back COSTS — read before celebrating

**The hand-authoring surface goes with it.** `blender-mark-scene.py` was the
only answer this repo ever had to the still-OPEN directive *"get an authoring
surface (iPad / pencil) into the workflow for cutting bushels and setting
pivots"*, and it was the third and most promising candidate for PHASE 0's cut
fix (*"let a click define the bushel and skip the automatic cut entirely"*).

Its claim `marks-are-authored-in-blender` had `supersedes: []` — it retired
nothing — so removing it leaves the conflict-key
`how-is-a-region-outline-and-pivot-authored` **with no live answer**. Region
outlines revert to `living/living-polys.json` as produced by the catalogue plus
`hinge-foliage.py`'s automatic cut, which is exactly the thing PHASE 0 exists to
fix (147 cards on `s-great-trees-upper`, 113 hinged on nothing).

So PHASE 0's remaining candidates are the two that do not need Blender:

1. scale the branch radius from crown size / card area rather than stroke width
2. skeletonise the ink and cut at junctions rather than at thin necks

and the browser option that was rejected for a reason that still holds
(*Roboflow / V7 / Label Studio have no concept of a PIVOT and would not land
marks in this repo's own `living-polys.json`*).

---

## How to re-run any of this

Nothing here was edited on the way in. Restore a file to `tools/` and it runs as
it did, against **Blender 5.2.1 LTS** — the version every measurement above was
taken on. Check that first; several of the findings are version-specific by
construction.
