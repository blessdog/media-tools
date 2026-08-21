---
id: hinge-at-the-attachment
kind: verdict
conflict-key: where-does-a-foliage-card-pivot
status: live
supersedes: []
scope: >
  Cut-out foliage cards in ink painting, where leaves are drawn as separate
  sprays hanging off visibly thinner twigs. Verified on s-pine-over-bridge at
  swing 5 deg. Not tested on the compound canopies, where the sprays are
  smaller than the branch strokes and the fallback may dominate.
verified-on: 2026-08-20
evidence:
  - jobs/wang-meng/living/evidence-attachment-pivot.png
---

## The axis was in the wrong place, so no amplitude could be right

The rig hinged each leaf cluster at "the centroid of its lowest rows" -- the
foot of its own bounding mass. A leaf spray hanging off a twig does not pivot
there; it pivots where it JOINS THE TWIG. Hinged at its foot, the whole spray
swings sideways and slides off the branch, and Ryan saw it at 6 degrees, 5
degrees and 3 degrees alike:

> "We've got to update our technique or solve this another way. These are not
> acceptable." — Ryan, 2026-08-20

Amplitude was searched three times before the axis was questioned. The tell was
that the defect did not scale with the parameter: at 3 degrees the sprays were
already detached, which a displacement problem cannot do.

## Finding the attachment

**Thickness separates branch from leaf**, because Wang Meng paints trunk and
branch with a loaded brush and leaves with a fine one. An opening by a disk of
radius r keeps only ink at least 2r wide:

    r=3  23,189px of 34,400 ink is branch
    r=5  15,851px          <- used
    r=7   8,219px

The pivot is then the cluster pixel nearest a branch pixel; a cluster further
than `--attach-max` from any branch is genuinely free-floating and falls back to
its foot. This is the same morphological read as `--keep tophat`, which
separates ripple arcs from rock in water — thin-versus-thick, applied to a
different question.

## The mechanism worth carrying

**When a defect does not scale with the parameter you are tuning, the parameter
is not the defect.** Three amplitude passes produced three images with the same
structural failure at different sizes. That invariance was the diagnostic, and
it was visible in the very first sweep.
