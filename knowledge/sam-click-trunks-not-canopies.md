---
id: sam-click-trunks-not-canopies
kind: procedure
conflict-key: how-to-prompt-sam-on-this-painting
status: live
supersedes: []
sibling: no-whole-tree-to-segment
applies-when: >
  prompting SAM with points on 葛稚川移居圖 or any ink painting with the same
  construction. Click TRUNKS, not canopies. Size the window to the feature, not
  to the picture. Wash has no contour -- leave it unclaimed and let
  complete-planes seal it by proximity.
not-when: >
  the target genuinely is one leaf spray or one figure, where a canopy click is
  the correct click. And never conclude a plane FAILED without checking overlap
  first: a later, nearer mask can erase an earlier one, which looks identical to
  SAM having missed it.
route: >
  ~/.venvs/media-tools/bin/python tools/segment-points.py --image IMG
  --points pts.json --window <feature-sized> ; points carry x, y, depth, window,
  name and pick (whole|best|tight). See knowledge/sam-environment.md for the
  interpreter -- bare python3 has no torch.
verified-on: 2026-08-13
asked-as:
  - how do I click points for SAM
  - SAM returned the wrong thing
  - where should I click on a tree
  - segment a tree with SAM
---

Migrated from `STATE.md` LAW 7 (2026-08-17), where it read:

> **SAM tricks:** click TRUNKS not canopies; window sized to the feature; wash
> has no contour — leave it unclaimed for sealing; a "failed" plane may have
> been ERASED by an overlapping leak, check overlap before blaming the point.

## Why it is being written down properly now

On 2026-08-20 SAM was prompted with three points on the pine over the bridge:
one near the fork and **two on leaf sprays**. It returned leaf sprays, 91% of
the crop unclaimed, and the conclusion drawn was that SAM cannot cut a tree
here. The recorded technique says click trunks. Two of the three points
violated it.

The refutation in [[no-whole-tree-to-segment]] therefore carries a caveat: it
was reached without cleanly testing the documented method, and a trunk-only
prompt has not yet been run. A refuted claim that is itself wrong is worse than
no claim, so that one stays open to revision until a trunk-only pass is
measured.

Second re-derivation of a written-down law in a single day; the first was
[[rest-is-a-noop]].
