---
id: leaf-marks-are-the-second-scale
kind: verdict
conflict-key: why-does-animated-foliage-read-as-a-blob
status: live
supersedes: []
scope: >
  Cut-out foliage on 葛稚川移居圖, and by the same mechanism any painting whose
  leaves are drawn as separate marks (most Chinese landscape, most cel
  backgrounds). NOT valid where foliage is a continuous wash with no internal
  marks -- there is nothing to split and the card is the only atom available.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-leaf-marks-pinebridge.png
  - jobs/wang-meng/evidence/AB-leafmarks-s-pine-over-bridge.mp4
  - jobs/wang-meng/living/marks-ab.sh
asked-as:
  - the leaves move as one green blob
  - how do I make individual leaves shimmer
  - the whole canopy tilts instead of the leaves moving
  - the foliage looks like a slab on a hinge
  - make the leaves twinkle
---

## A blob on a hinge can only tilt

Ryan, 2026-08-21, after picking 12 deg off the swing ladder: *"Okay, but I see
the entire leaf structure is one green blob. I would like to make the individual
leaves kind of twinkle and shake. move around leaf not entire tree."*

**The mechanism.** `hinge-foliage` cut cards as CONNECTED COMPONENTS of ink. Any
spray whose leaf marks touch each other is therefore one component -- one card,
one pivot, one rigid body. A rigid body on a hinge has exactly one degree of
freedom, so however the angle is tuned it can only tilt. Shimmer is not a
smaller tilt; it is a different motion that the rig could not express at all.

**The technique, named before the tool.** In cel practice a canopy carries two
scales at once: the spray swings on its branch (PRIMARY), and each leaf moves
smaller, faster and out of phase with its neighbours (SECONDARY ACTION, also
called overlapping action). The flash a real canopy gives off is a leaf turning
EDGE-ON -- which for a flat ink mark is a narrowing along one axis. Rotation
alone reads as wobble; the narrowing is what reads as light.

**The atoms already exist in the ink.** Wang Meng draws each leaf as its own
outlined mark, so nothing has to be invented -- only separated. Touching blobs
of similar size are separated by DISTANCE-TRANSFORM WATERSHED, the same
classical routine used to split touching cells or coins.

**Seed spacing is read from the ink, never fixed.** The median distance-transform
value over a card's ink IS the typical mark half-width. This is the same
mechanism as [[branch-radius-scales-with-the-tree]]: Wang Meng paints leaves at
near-constant real size, so a distant tree is the same drawing with smaller
marks, and one fixed spacing splits one tree while fusing the next.

**Compose the two transforms, warp once.** The mark matrix is multiplied into
the card's hinge matrix and applied as a single affine. Warping by the hinge and
then again by the mark resamples every leaf twice and visibly softens it.

Measured across z3w's seven near trees:

    region                  cards   leaf marks   marks/card
    s-great-trees-upper        74          963         13.0
    s-gorge-foreground         88          464          5.3
    s-pine-over-bridge         21          433         20.6
    s-left-pines-z2            35          366         10.5
    s-gorge-big-canopy         65          301          4.6
    s-left-clifftop-pine       10          286         28.6
    s-right-rust-tree          13           40          3.1   <- weakest split

306 cards -> 2,853 marks, at no measurable cost (4.5s rendered both halves of
the A/B). `s-right-rust-tree` is the honest outlier: its leaves are the smallest
in the zone (p90 card radius 31px) and barely separate, so it is the one tree
where the blob critique may still stand.

**The general lesson, and the reason this is a verdict and not a note:** an
amplitude ladder can be the wrong question. Three angles of one rigid blob were
three sizes of the same defect. When tuning a parameter produces only bigger and
smaller versions of the same complaint, the missing thing is a degree of freedom,
not a value -- the same shape as
[[a-defect-that-does-not-scale-is-not-the-parameter]].
