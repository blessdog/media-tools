---
id: canopy-read-distant
kind: verdict
conflict-key: how-to-find-a-canopy-distant
status: superseded
supersedes: []
superseded-by: a-percentile-cannot-reject-a-region
superseded-on: 2026-08-24
scope: >
  DISTANT ridges only -- the summits, master y < ~3850, verified on z6w. NOT
  valid near; the compound uses canopy-read-near, which is a different rule for
  the same job at a different distance.
verified-on: 2026-08-20
evidence:
  - jobs/wang-meng/living/evidence-summit-dark-accents.png
  - jobs/wang-meng/living/evidence-summit-darkness-map.png
asked-as:
  - mask trees on a distant ridge
  - find canopies on the summits
---

The darkest 2-3% of the box, closed into coherent masses, specks dropped, grown
a little for the feather. Implemented as `canopyRule: "dark-accent"` in
`jobs/wang-meng/living/regions.json`, selected per class so the near rule is
untouched.

At this distance Wang Meng paints trees as the darkest accents on a mid-tone
slope. One region went from 71,580 px of claimed "canopy" to 11,615 px.

Note what this record does NOT authorise: the summit masks it produces are
correct, and nothing up there animates anyway. See `what-moves`. The rule is
kept because it is a real finding about distant foliage, not because it is in
use.

---
RETIRED 2026-08-24. The masks were correct; the RULE was not doing the work.

Measured over the 160 catalogued boxes of the summit band, the darkest-3%
selector claims 7.0% of a box the catalogue calls a TREE and 6.6% of a box it
calls ROCK. The best possible single threshold on that fraction scores 61.9%,
which is exactly the accuracy of always guessing "tree" -- no cut beats chance.

So the rule has no discriminative power at this distance. What made
`s-summit-crest-left` go from 71,580 px to 11,615 px was not the rule finding
trees; it was a human having already drawn the polygon around one. The polygon
did all of the work, and the number above was read as the rule's success.

See a-percentile-cannot-reject-a-region for the mechanism, and
the-catalogue-decides-what-is-foliage for what to do instead.
