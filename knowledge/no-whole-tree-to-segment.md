---
id: no-whole-tree-to-segment
kind: refuted
conflict-key: can-a-whole-tree-be-masked-automatically
status: live
supersedes: []
mechanism: >
  There is no whole-tree SHAPE in this painting to find. Wang Meng draws a tree
  as separate marks over bare silk -- leaf sprays, twigs, a trunk -- with no
  enclosing contour and no filled silhouette. Every automatic method therefore
  answers a different question than the one asked, and the failures are all
  consistent with that: SAM point prompts return individual leaf SPRAYS (which
  are real objects) and never the tree; a tone threshold plus connected
  components bleeds through the point where the tree's ink touches the rock's
  ink and swallows 47-64% of the crop; the density+compactness canopy detector
  returns a vertical band that includes rock and misses the tree's entire left
  half. A whole-tree mask can only be AUTHORED -- a lasso is a human judgement
  about which marks are one tree, and that judgement is not in the pixels.
verified-on: 2026-08-20
---

## Measured, 2026-08-20

| method | result on s-pine-over-bridge |
|---|---|
| canopy detector (density + compactness) | vertical band incl. rock, misses the left branch entirely |
| tone threshold + connected component from a trunk seed | 124,522–170,258px, i.e. 47–64% of the crop, at every offset tried |
| SAM `facebook/sam-vit-huge`, 3 point prompts | two leaf sprays and a branch line; 91% unclaimed |

evidence: `jobs/wang-meng/living/evidence-whole-tree-mask.png`,
`evidence-tree-component.png`, `_sam-pine2/overlay.png`

**So the whole-tree card is off the table for now**, and the working technique is
per-spray cards hinged at their attachment — see [[hinge-at-the-attachment]].
A whole-tree card remains possible the day someone lassos seven trees by hand;
it is not blocked on cleverness, it is blocked on an authored polygon.

Note the tone read was still the best AUTOMATIC picture of the tree (Ryan:
"what you were doing before SAM looked more effective") -- it follows trunk,
branch and leaves as one structure. What it cannot do is stop at the tree.
