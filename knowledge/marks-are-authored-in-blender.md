---
id: marks-are-authored-in-blender
kind: procedure
conflict-key: how-is-a-region-outline-and-pivot-authored
status: live
supersedes: []
sibling: no-whole-tree-to-segment
verified-on: 2026-08-25
applies-when: >
  deciding WHICH INK IS ONE THING on 葛稚川移居圖 -- one bushel, one tree, one
  fall -- and WHERE IT HINGES. Any time a mark has to be pointed at precisely:
  authoring a new region, correcting a bad cut, or saying which thing in a
  render is wrong. The judgement is human; this is the route it travels.
route: >
  /Applications/Blender.app/Contents/MacOS/Blender -b --python
  tools/blender-mark-scene.py -- --plate jobs/wang-meng/journey/<zone>/plate.json
  --seed-from jobs/wang-meng/living/living-polys.json --out
  jobs/wang-meng/marks/<zone>-marks.blend
  · open it, pick the Grease Pencil layer named for the class, draw. ONE STROKE
  = ONE REGION. Taps on the `pivot` layer attach to whichever region contains
  them. Then:
  Blender -b <zone>-marks.blend --python tools/blender-read-marks.py --
  --out jobs/wang-meng/marks/<zone>-polys.json --simplify 6
route-also: >
  The transform is stored IN the .blend as scene['mark_transform'] and the
  reader takes it from there, so a scene rebuilt at a different --span still
  resolves. Verified 2026-08-25: 765 points round-tripped master -> Blender ->
  master with a worst error of 0 master px. Output is shaped like
  living-polys.json (polys[] with points in master px) and merges straight in.
not-when: >
  cutting the cards. This authors OUTLINES and PIVOTS; hinge-foliage.py still
  does the cutting, from these outlines. And not for tightening a mark to the
  ink -- that is SAM's job, downstream of a mark that already exists.
evidence:
  - tools/blender-mark-scene.py
  - tools/blender-read-marks.py
  - jobs/wang-meng/evidence/2026-08-25-blender-mark-roundtrip.png
asked-as:
  - how do I mark which leaves are one bushel
  - how do I tell you which tree I mean
  - where do pivots come from
  - author a region by hand
  - the cut is confetti not bushels
  - how do I point at something in the painting
---

## The judgement is not in the pixels, so it needs an input device — not a better classifier

[[no-whole-tree-to-segment]] is refuted from five directions now: SAM point
prompts return leaf sprays, tone thresholding swallows 47–64% of the crop, the
density detector misses half the tree, and two classifiers on 2026-08-25 scored
73.6% and 54.2% — the second worse than guessing. Wang Meng draws a tree as
separate marks over bare silk. There is no enclosing contour to find.

**So stop trying to compute it and draw it.** Ryan: *"my eyes can easily define
these bushels… I could tell you exactly what trees and where the pivot points
are. That would fix everything and it would take five minutes."*

**A drawn mark has no interpretation step.** "The big tree above the bridge, not
the pine" is a sentence I have to resolve, and the failure is invisible until a
render comes back wrong — which is the mechanism behind
[[an-absence-is-invisible-in-the-output]]. A stroke is a polygon in master px.
The ambiguity never forms.

**Blender, not a web page.** The pen (or the mouse — this needs position and
click, not pressure) drives the same pointer stream in any app, so the device
does not choose the tool. Blender wins because the plane stack, the multiplane
camera and the render already live there, so a mark can be checked against the
thing it will affect without a round trip. It also closes the standing directive
[[a-directive-is-a-decision-not-a-suggestion]].

**The trap, which looks identical while you are drawing.** Use a **Grease Pencil
object**, never the **Annotate** tool. Creating annotation strokes via Python is
unavailable in Blender 4.3+ (issue #147732) and this is 5.2.1; Grease Pencil
strokes read back through `drawing.attributes`. `blender-mark-scene.py` builds a
scene that can only be drawn on the readable way, and deletes the default layer
named `Layer`, because a stroke on it would read back as a region of class
"Layer".

**What the scene gives you on open:** the plate as a non-selectable image empty,
one coloured Grease Pencil layer per class plus `pivot`, top orthographic view
framed on the plate, and the existing 181 polys seeded on locked `ref-*` layers
as context. The reader skips `ref-*`, so seeded reference cannot be
double-counted as new marks.

**Simplification runs in master px, not viewport units.** A hand-drawn loop is
hundreds of points; `--simplify 6` runs Ramer–Douglas–Peucker at a real distance
on the painting, so the tolerance means the same thing at any zoom. Measured: a
200-point loop became 74 points at 6 master px.
