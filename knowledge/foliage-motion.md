---
id: foliage-motion
kind: procedure
conflict-key: how-to-move-foliage
status: live
supersedes:
  - foliage-motion-by-displacement
sibling: water-motion
applies-when: >
  a painted mass UNCOVERS GROUND when it moves, or it has INTERNAL STRUCTURE
  THAT MUST STAY PUT. Either test alone is sufficient. Foliage answers yes to
  both: a canopy reveals cliff behind it, and its trunk and branches are mass
  that must not travel with the leaves.
not-when: >
  the mark is a thin stroke that quivers in place, uncovers nothing, and has no
  structure to protect. That is water — use the sibling, water-motion.
route: >
  clean-plate.py --method shiftmap (synthesise the ground behind the canopy,
  ONCE) -> hinge-foliage.py --from-ink --branch-radius auto --attach-max 14
  --leaf-marks (cut one card per ink cluster, pivot WHERE IT JOINS A BRANCH --
  see hinge-at-the-attachment -- rotate on a gust envelope delayed by position
  along the wind, AND split each card into its individual leaf marks so each one
  moves on its own phase -- see leaf-marks-are-the-second-scale, without which a
  spray of touching marks is one rigid blob that can only tilt) ->
  render-parallax (composite at depth). Implemented as the
  foliage-motion entry in jobs/wang-meng/living/build-zone-living.py's
  TECHNIQUES table. NOT cut-stroke.py first: hinge-foliage cuts its own cards,
  because the card decomposition is what decides crown-sway vs leaf-flutter and
  therefore belongs to the tool that swings them.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/living/evidence-warp-blurs-lift-does-not.png
  - jobs/wang-meng/evidence/AB-leafmarks-s-pine-over-bridge.mp4
asked-as:
  - make the leaves move
  - animate a tree
  - foliage in wind
---
## The route, in one line

**To make the leaves move, animate a tree, or put foliage in wind:** cut the
canopy into cards, hinge each card where it joins its branch, split each card
into its leaf marks, and swing the whole thing on a gust envelope over a clean
plate. The tool is `hinge-foliage.py`; the ground behind it comes from
`clean-plate.py` first.

**Why not a displacement field.** A field cannot hold part of its own region
still, so it moves trunk, branch and leaves together — the lollipop-on-a-stick
tell. Ryan's word for the result was *"a weird mush"*. The full measurement that
killed it is narrative, and lives in
`docs/journal/2026-08-20-why-displacement-fields-cannot-hold-a-trunk-still.md`
rather than in this claim, because a claim carrying its own history stops being
findable — see [[three-layers-claim-narrative-status]].

**The hinge is not new work.** `walk-figure.py --limbs` has swung the deer's
legs since 2026-08-16 with `getRotationMatrix2D` about each limb's own pivot.
`hinge-foliage.py` is that mechanism with a gust envelope in place of a gait.
