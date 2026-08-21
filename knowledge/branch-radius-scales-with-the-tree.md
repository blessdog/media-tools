---
id: branch-radius-scales-with-the-tree
kind: verdict
conflict-key: how-is-the-branch-radius-chosen
status: live
supersedes: []
scope: >
  hinge-foliage's branch/leaf split on 葛稚川移居圖, and by the same mechanism any
  painting where trees are drawn at near-constant real size so a far tree is the
  same drawing made smaller. Verified on the seven near trees of z3w. The RATIO
  0.55 is Ryan's pine choice expressed in the tree's own units. Judged by eye
  2026-08-21 on the pine, the great-trees knoll (r=3) and the big gorge canopy
  (r=2) holds -- Ryan: "very nice. right one is subtle and beautiful in all."
  The left pines, clifftop pine, gorge foreground and rust tree are built on
  the same rule and have not had their own hold in front of him.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/living/evidence-branch-radius-sweep.json
  - jobs/wang-meng/living/evidence-branch-pivots-z3w.png
  - jobs/wang-meng/living/AB-HOLD-greattrees.mp4
  - jobs/wang-meng/living/AB-HOLD-bigcanopy.mp4
  - jobs/wang-meng/living/evidence-stroke-width-z3w.json
asked-as:
  - which branch radius for the other trees
  - the hinge only works on the pine
  - leaves fall back to the foot pivot
  - how thick is a branch
---

## A number chosen on one tree is in that tree's units

Ryan chose branch radius 5 on s-pine-over-bridge. Rolled out as a fixed
number across the seven near trees it hinged 18 of 23 pine cards at a branch
and **1 of 68** on the big gorge canopy, 4 of 29 on the left pines, 2 of 15 on
the rust tree -- every other card fell back to the foot pivot he had rejected.

    tree                   p99 stroke half-width   attached at r=5   attached at auto
    s-pine-over-bridge     9.17px                  18/23             18/23  (r=5)
    s-gorge-foreground     6.14px                   9/82             58/82  (r=3)
    s-left-pines-z2        4.78px                   4/29             19/29  (r=3)
    s-great-trees-upper    4.65px                  19/70             54/70  (r=3)
    s-left-clifftop-pine   4.23px                   2/11              8/11  (r=2)
    s-right-rust-tree      3.69px                   2/15             15/15  (r=2)
    s-gorge-big-canopy     3.28px                   1/68             61/68  (r=2)

**Mechanism.** Wang Meng paints a tree at near-constant real size, so a tree
further up the scroll is the same drawing made smaller, and its trunk stroke is
thinner by the same ratio. An opening by a disk of radius 5 keeps only ink at
least 10px wide; the smaller trees have none, so they have no branch to hinge
on. The defect is not the radius, it is the UNIT: pixels, when the quantity
that matters is "this tree's thick stroke versus its thin one".

**Rule.** `--branch-radius auto`: r = 0.55 x the tree's own 99th-percentile
stroke half-width (distance transform of its ink mask). 0.55 is 5 / 9.17 -- the
pine choice, carried over. The builder passes it from the `foliage` class in
regions.json; cycle.json records the radius that was actually used.

**Caveat, seen in the pivot overlay.** On a broadleaf canopy at r=2 the thickest
leaf blobs also pass the width test, so a few pivots sit inside a leaf mass
rather than at a twig. The attached COUNT cannot see this; only the overlay
can. That is why the builder now writes `pivots.png` per tree.
