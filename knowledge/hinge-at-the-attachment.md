---
id: hinge-at-the-attachment
kind: verdict
conflict-key: where-does-a-foliage-card-pivot
status: live
supersedes:
  - verdict-foliage-pivot-and-stir
scope: >
  Cut-out foliage cards in ink painting, where leaves are drawn as separate
  sprays hanging off visibly thinner twigs. Verified on s-pine-over-bridge at
  swing 5 deg; Ryan's verdict 2026-08-21 on the r3/r5/r7 comparison: branch
  radius 5, swing as is -- now the `foliage` class in regions.json
  (branchRadius 5, attachMax 14) and therefore every leaf-visible tree the
  builder makes. Not tested on the compound canopies, where the sprays are
  smaller than the branch strokes and the fallback may dominate; those are
  class `still` today so the question is moot until one is promoted.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/living/evidence-attachment-pivot.png
  - jobs/wang-meng/living/AB-PINEBRIDGE-foot-vs-attach.mp4
asked-as:
  - where should a leaf card pivot
  - the leaves slide off the branch
  - leaves detached from the tree
  - which branch radius
  - what did Ryan decide about the foliage rig
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
    r=5  15,851px          <- Ryan's pick, 2026-08-21 ("looks good")
    r=7   8,219px

Until 2026-08-21 the zone builder never passed `--branch-radius`, so every
zone build silently used the tool's default of 3 while the evidence image
showed 5. The class in regions.json is the only place the number lives now.

The pivot is then the cluster pixel nearest a branch pixel; a cluster further
than `--attach-max` from any branch is genuinely free-floating and falls back to
its foot. This is the same morphological read as `--keep tophat`, which
separates ripple arcs from rock in water — thin-versus-thick, applied to a
different question.

## The motion A/B, 2026-08-21 -- the still overlay was not the proof

The rig was adopted on the strength of the pivot overlay alone; the
"not acceptable" it answered was a 15-degree foot pivot BEFORE de4941f fixed
three compositor leaks. Rendered side by side on the same hold -- foot pivot
6 deg (5cc32e8) left, attachment r5 right, living halves only -- Ryan:
**"The right one is slightly better."** Slightly. The fixed compositor did most
of the work; the hinge placement is a real but small gain on the pine, and
nothing here says it is a large gain on trees whose branch ink is thinner
(see branch-radius-scales-with-the-tree). A still overlay is a claim about
where a card WILL pivot; only the clip is evidence of how it moves.

## The mechanism worth carrying

**When a defect does not scale with the parameter you are tuning, the parameter
is not the defect.** Three amplitude passes produced three images with the same
structural failure at different sizes. That invariance was the diagnostic, and
it was visible in the very first sweep.
