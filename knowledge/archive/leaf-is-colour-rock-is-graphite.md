---
id: leaf-is-colour-rock-is-graphite
kind: procedure
conflict-key: how-are-leaf-strokes-separated-from-rock-strokes
status: superseded
supersedes: []
superseded-by: the-catalogue-decides-what-is-foliage
superseded-on: 2026-08-24
sibling: no-whole-tree-to-segment
applies-when: >
  cutting foliage cards from ink on 葛稚川移居圖 (hinge-foliage --from-ink), or
  any ink painting where leaves carry a colour wash and rock does not. The
  dark strokes that draw a leaf and the dark strokes that draw a rock are the
  same grey ink; where a canopy stands on a rock they touch, and a tone
  threshold fuses them into one card that swings the rock. Ryan saw it in the
  first station reel, 2026-08-21: "You animated the rock right here… The
  leaves are all green or orange. You shouldn't be animating the graphite
  ridges of rocks."
not-when: >
  the thing to separate is FOLIAGE FROM FOLIAGE (which tree a spray belongs
  to) -- colour does not answer that; see the sibling, no-whole-tree-to-segment.
  Nor for the distant nubs, which are class `still` and are not cut at all.
route: >
  hinge-foliage.py --leaf-colour (default on). Classify the MID-TONE wash, never
  the dark strokes: green leaf = Lab a at least 2.5 below the silk's median a;
  orange leaf = hue <= 28 deg at saturation >= 0.34 (the silk sits at hue ~35,
  S ~0.28, a 130; grey cliff wash at a 130; the rock cap UNDER the maples at a
  135 -- warmer than silk, never greener). Grow the wash 5 px to reach the
  strokes drawn over it; keep only ink inside. cycle.json records
  leafColour and inkNotOnLeafPx.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/living/evidence-moved-s-gorge-foreground-BEFORE.png
  - jobs/wang-meng/living/evidence-leafcut-s-gorge-foreground.png
  - jobs/wang-meng/living/evidence-leafcut-s-gorge-big-canopy.png
asked-as:
  - the rock is moving
  - you animated the rock
  - leaves are green or orange
  - graphite ridges should not move
  - how do I tell a leaf stroke from a rock stroke
---

## Three measurements that were wrong before one was right

1. **Saturation** -- the aged silk is itself warm (S ~0.2), so grey ink over it
   measures as "coloured" as a leaf. No separation.
2. **Lab distance from the silk** -- dark ink collapses toward neutral (128,128)
   in Lab, which is 12 units from the warm silk, so the darkest rock strokes
   scored as the most "coloured" thing in the crop. Every card passed.
3. **Direction, on the wash** -- the leaves' colour is in the wash under the
   strokes, and it goes somewhere the silk and the rock never go: the "teal"
   canopies are olive, a = 126 against the silk's 130; the maples are hue
   20-28 at S 0.37+. The rock cap is a = 135: warmer than silk, in the
   opposite direction from every leaf.

Measured on s-gorge-foreground: 40,848 ink px, 3,946 left still (the rock cap
and the cliff below it), the rest cut as before. Side effect worth knowing:
with the rock out of the ink, that tree's p99 stroke half-width fell from 6.1
to 3.7 px, because the rock had been the "thick stroke" the auto branch
radius was measuring. The two rules compound.
