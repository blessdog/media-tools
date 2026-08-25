---
id: the-catalogue-decides-what-is-foliage
kind: procedure
conflict-key: how-are-leaf-strokes-separated-from-rock-strokes
status: live
supersedes: [leaf-is-colour-rock-is-graphite]
sibling: no-whole-tree-to-segment
verified-on: 2026-08-24
applies-when: >
  deciding WHICH INK IS FOLIAGE anywhere on 葛稚川移居圖, and by the same
  mechanism on any painting where the classes are drawn rather than
  photographed. Always, now -- not only for whole-plate passes.
route-also: >
  AND IT DECIDES THE CARD TERRITORY, not only which ink inside a card may move.
  build-zone-living's canopy_mask was a FOURTH answer to WHERE -- a
  density+compactness texture read -- running after the catalogue and SAM had
  already answered pixel-exactly. Measured 2026-08-24 across all five zones:
  the authored polygons enclose 91.4% of the catalogued leaf ink and canopy_mask
  handed 36.0% to the cutter, discarding 60% of leaf we had already located.
  Set classes.foliage.canopyRule = "catalogue". On cat-broadleaf-great-right
  that took leaf under the cards 29,919 -> 62,910 px and off-leaf ink under them
  7,641 -> 787 (purity 79.7% -> 98.8%), and the rendered cycle went from 14.6%
  to 70.3% of its leaf visibly moving. Density stays as the fallback for a
  region the catalogue never saw, which is what it was written for.
not-when: >
  deciding which pixels inside a foliage region are painted MARK. That is the
  ink cut and it is a threshold question, correctly. The catalogue answers WHAT,
  SAM answers WHERE, the ink cut answers WHICH. Do not ask any of the three to
  do another's job.
route: >
  tile-image.py over the uncatalogued band -> a SUB-AGENT LOOKS AT EACH TILE and
  writes catalogue/tNNN.json (id, name, kind, box normalised to the tile, motion,
  leavesVisible, depth, note) -> refine-mask-sam.py --boxes --kinds tree turns
  each box into a pixel-exact mask -> composite-tile-masks.py merges to one
  master-px foliage mask -> journey/master-mask-to-plate.py crops and scales it
  into the zone's plate space, unioning the bands -> hinge-foliage --leaf-mask.
  catalogue/sam-z1lower.sh is the worked example.
evidence:
  - jobs/wang-meng/evidence/2026-08-24-catalogue-vs-colour.mp4
  - jobs/wang-meng/catalogue/foliage-master-z1lower.png
  - jobs/wang-meng/journey/z1/leaf-mask.png
asked-as:
  - how do I tell leaves from rock
  - which ink is foliage and which is rock
  - the rock is moving
  - what should decide what a leaf is
  - how do I build a foliage mask
  - can a colour threshold find the leaves
---

## Which ink is foliage: a catalogue says so, not a threshold

**Which ink is foliage is a question about MEANING, and a threshold cannot
answer it.** Put a mind on it.

Ryan, 2026-08-24, after the colour gate animated stone across the whole plate:
*"we need a better way to id the foliage. there are ai models that do this. you
yourself know the dif. this is a solved problem."* And then the shape of the
fix: *"instead of running another model, we just create a sub-agent that
properly labels everything in this painting. cleanly, mathematically."*

**Measured, same plate, same cards, same swing — only the decider changed.**
Leaf ink as a share of each plane's own ink:

| plane | catalogue | colour gate |
|---|---|---|
| water | **0.0%** | 88.5% |
| left-bank-rocks | **0.0%** | 51.2% |
| resting-ledge | **0.0%** | 42.1% |
| left-cliff-wall | **0.0%** | 32.9% |
| bank-path | **2.1%** | 60.2% |
| foreground-rock-mass | **9.5%** | 64.0% |
| great-trees-knoll | 68.0% | 89.1% |
| gorge-wall-right | 63.4% | 63.9% |

And in motion: ink moving on the rock, water and bridge planes fell **125,270 →
41,730 px (-67%)**, foreground-rock-mass alone **-85%**, while leaf ink that
moves ROSE to **246,501 of 269,561 catalogued leaf px — 91%**. Better on both
axes at once, which is the signature of a right answer rather than a trade.

## Why colour could never have worked, in the labellers' own words

Four agents catalogued the scroll's bottom independently. **Three of them named
the same decoy without being told it existed**: a warm ochre/pink wash on stone
whose 牛毛皴 hemp-fibre strokes fan out like a clump of needles. One wrote the
test it used — *"every stroke follows the dome of the boulder and terminates
dead on its contour line, and there is no green in the passage anywhere."*

Three judgements that no threshold on this painting can reach:

- **点苔 moss dotting on rock** is dark, granular and clustered, and reads as
  distant shrubs at tile scale. It is stone.
- **Dark-ink leaf clusters carry NO colour wash at all**, so a green rule drops
  them — but the glyphs are repeated, paired and stalked, so they ARE foliage.
  The colour gate fails in *both* directions, not one.
- Some boxes are **search regions, not masks**: leaves drawn as a transparent
  veil in front of ochre boulders, where roughly half of every box is rock.
  Those were flagged as such in their own notes. SAM is what makes them usable.

## What the retired claim got right, and its real scope

[[leaf-is-colour-rock-is-graphite]] correctly identified that colour lives in the
mid-tone WASH and never in the strokes, and it worked on the hand-authored crops
it was verified on. It fails as a general decider because **its reference is a
single global silk median**, and silk tone drifts across a 15,000px scroll
(measured: local a from 124 to 140). Correcting that locally was tried and moved
the leak only 66.7% → 61.3% while destroying a third of the real foliage — so
the mechanism is not the reference either. The mechanism is that "is this a
leaf" was never a colour question.

Keep colour only as a within-region tiebreak where a human has already drawn the
fence, never as the thing that draws it.

## The general form

**When a threshold is answering a question about MEANING, the fix is not a
better threshold — it is to put something that can see in that position, and let
the geometry tools do geometry.** Vision models were probed here first and are
committed in `tools/segment-foliage.py`; they were set aside because a sub-agent
that can zoom, check the neighbouring tile, and say "I am unsure" beat both.
