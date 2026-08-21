---
id: perception-needs-a-boundary-model-too
kind: verdict
conflict-key: is-clipseg-alone-enough-to-cut-foliage
status: live
supersedes: []
scope: >
  CLIPSeg (CIDAS/clipseg-rd64-refined) as the SOLE decider of which ink is
  foliage on 葛稚川移居圖, at plate resolution, measured on the seven near trees
  of z3w on 2026-08-21. It says nothing about CLIPSeg as a PROPOSER feeding a
  boundary model, which is untested and is the next step.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/living/evidence-thresholds-vs-vision-model.png
  - jobs/wang-meng/living/evidence-semantic-veto.png
asked-as:
  - is clipseg good enough
  - can a vision model cut the foliage masks
  - the model called a tree a rock
  - why is the semantic mask not used
---

## Right family of tool, not yet accurate enough alone

[[perception-is-a-model-not-a-threshold]] is correct about WHO should answer
"is this a leaf" -- and a model asked in words immediately found canopies five
hand-tuned thresholds missed. But CLIPSeg decodes at 352px and draws blobby
envelopes, and at this scale that costs more than it buys, in both directions:

    mode   what it does                       measured on z3w
    keep   move only ink the model calls leaf  s-pine-over-bridge 21 cards -> 16,
                                               s-great-trees-upper 74 -> 52.
                                               Real crowns stop moving.
    veto   hold ink the model calls rock       s-gorge-foreground: 19,014 ink px
                                               vetoed vs the colour gate's 6,063 --
                                               and the picture shows the vetoed mass
                                               IS the orange maple. A whole tree
                                               classed as bare grey rock.

The two methods also disagree about where rock is: on s-great-trees-upper they
agree on only 370 px of the colour gate's 4,938, so their intersection leaves
rock moving -- the exact defect being fixed.

**Verdict: `semantic: false` in regions.json's foliage class for now**, with the
masks built and the tool wired, because the deciding question is which mask is
better on the screen and today the threshold gate wins that. Shipping the worse
mask because the method is more modern is the same error as shipping the wrong
tool because it runs.

**What unblocks it:** the missing stage is BOUNDARY. The model is a good
proposer (what and roughly where) and a bad delineator; SAM is a good delineator
and knows nothing about what. `facebook/sam-vit-huge` is already local
(knowledge/sam-environment.md). The chain to build and re-measure:
CLIPSeg or an authored catalogue box -> SAM mask -> ink cut inside it. Flip the
flag when that beats the colour gate on the same seven trees, by picture.
