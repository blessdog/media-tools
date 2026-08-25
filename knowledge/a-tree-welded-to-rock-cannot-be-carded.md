---
id: a-tree-welded-to-rock-cannot-be-carded
kind: law
conflict-key: which-trees-may-be-cut-and-swung
status: live
supersedes: []
verified-on: 2026-08-25
evidence:
  - jobs/wang-meng/evidence/2026-08-25-broadleaf-vs-ridge-pine.png
asked-as:
  - the mountain tops are moving
  - the mountains move when the trees move
  - which trees are allowed to be animated
  - the ridge is swaying and it should not be
  - are the pines different from the other trees
  - why does the summit look wrong when the foliage moves
---

## A tree whose ink is continuous with the rock has no card boundary

> "That's not a pine. Pines have needles. Those are leaves. The pines are the
> ones that are little sticks drawn up straight with tiny other straight sticks
> coming out of them that are tight to the mountains. **When you move those,
> those literally move the mountains.**" — Ryan, 2026-08-25

Two objects in this painting are both called trees and must never be treated the
same way. Open the evidence image; the distinction is obvious once seen and
invisible in every region name we wrote.

| | BROADLEAF | RIDGE PINE |
|---|---|---|
| how it is drawn | round leaf clusters on its own trunk | straight sticks with straight little branches |
| what is behind it | bare silk | the rock itself |
| its ink | its own | continuous with the ridge's 牛毛皴 |
| a connected component of that ink is | the tree | the tree **plus mountain** |
| verdict | card it and swing it | **HOLD IT** |

**The mechanism.** `hinge-foliage` cuts a card from a connected component of
ink. That is sound exactly when the component's boundary is the object's
boundary. A broadleaf standing on silk satisfies this. A ridge pine does not:
the painter drew its trunk with the same brush, the same tone, and often the
same stroke as the texture of the rock it stands on, so the component runs
straight out of the tree into the mountain. Rotating the card rotates the
mountain, which is precisely what Ryan saw.

**This is not a masking problem and no better mask fixes it.** The card boundary
does not exist in the picture. Compare [[no-whole-tree-to-segment]], which found
that a whole-tree mask can only be AUTHORED because a tree here is separate
marks over silk; this is the harder neighbouring case, where even an authored
lasso cannot separate tree ink from rock ink because they are the same strokes.
[[canopy-by-texture-statistics]] is the same wall from the other side: at
distance the painter was not drawing rock and forest differently.

**What this retires.** Summit moving-leaf coverage was being driven UP as the
goal — 19.4% to 67.9% on 2026-08-24, with the remaining gap at the summit
(52.3%) logged as the thing to close. On the summit that metric was counting the
defect. [[a-card-that-exists-moves-fine]] stays true inside its stated scope
(the z1 plate, near broadleaf) and must not be generalised past it; this is the
case [[a-verdict-is-a-hypothesis-about-everything-else]] warns about, met in the
wild.

**What moves at the summit instead:** parallax between ridge planes, water, and
the mist passages. Distant rock with still trees on it is what a distant ridge
actually looks like.

**The general form:** before cutting anything out of a painting, ask what the
painter drew it ON. A cut-out technique assumes the object was drawn as an
object. Where the painter drew it as part of its ground, the technique has no
subject and the tool will happily return one anyway.
