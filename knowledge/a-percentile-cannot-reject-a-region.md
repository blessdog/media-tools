---
id: a-percentile-cannot-reject-a-region
kind: refuted
conflict-key: how-to-find-a-canopy-distant
status: live
supersedes: [canopy-read-distant]
verified-on: 2026-08-24
mechanism: >
  A percentile is defined relative to its own input, so it ALWAYS returns
  something -- give it a blank sky and it returns the darkest 3% of the blank
  sky. It can rank pixels within a region; it can never reject the region. So
  it cannot decide WHAT a region contains. Measured on the summit band, the
  darkest-3% selector claims 7.0% of a catalogued tree box and 6.6% of a
  catalogued rock box, and no threshold on that fraction beats always guessing
  the larger class. The earlier good result came from the authored polygon,
  not the rule: testing a WHAT-rule only on regions that already contain the
  right answer cannot fail.
evidence:
  - jobs/wang-meng/catalogue/evidence-dark-accent-cannot-discriminate.png
asked-as:
  - find canopies on the summits
  - mask trees on a distant ridge
  - can I use the darkest pixels to find foliage
  - why did my threshold claim part of every region
---

Selecting "the darkest N%" of a region finds foliage on a distant ridge.

REFUTED. Measured across the 160 catalogued boxes of the summit band, master
y 0-4712:

    catalogued TREE boxes   n=99   darkest-3% claims  median 7.0%  (1.0-10.2)
    catalogued ROCK boxes   n=61   darkest-3% claims  median 6.6%  (4.7-11.9)

    best possible single threshold on that fraction   61.9%
    always guessing the larger class                  61.9%

No cut beats chance. The rule has zero discriminative power between stone and
leaf at summit distance.

MECHANISM, and it generalises past this painting. A percentile is defined
relative to its own input, so it ALWAYS returns something -- give it a blank
sky and it returns the darkest 3% of the blank sky. It answers "which pixels
here are darkest", and it is structurally incapable of answering "is there
anything here at all". Any selector of that shape can only rank within a
region; it can never reject one. So it cannot be the thing that decides WHAT a
region contains, no matter how good its output looks.

AND THE GOOD OUTPUT IS THE TRAP. The retired claim recorded a real measurement
-- one summit region went from 71,580 px of claimed canopy to 11,615 px -- and
read it as the rule working. It was the authored POLYGON working: a human had
already drawn a boundary around a tree, and inside that boundary any dark-ink
selector looks like a tree-finder. Testing a WHAT-rule only on regions that
already contain the right answer cannot fail, which is why it did not.

THE CONTROL THAT SETTLES IT is cheap and should be run on any classifier of
this shape: hand it a region of the class you want AND a region of the class
you fear, and compare the fractions. Equal fractions mean the enclosing box is
your classifier.

WHAT TO DO INSTEAD: the-catalogue-decides-what-is-foliage. Something that has
looked at the picture says WHAT is there; SAM says exactly WHERE; the ink cut
says WHICH pixels. On this band that division is not a preference -- three
independent labellers reported that the darkest things on the summits are 点苔
moss curtains on shaded cliffs, moss-capped pinnacles, and the colophon
calligraphy, which is the blackest ink in its tile.
