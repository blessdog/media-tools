---
id: leaves-hold-under-leaves
kind: law
conflict-key: what-does-a-swinging-foliage-card-reveal
status: live
supersedes: []
verified-on: 2026-08-24
evidence:
  - jobs/wang-meng/evidence/2026-08-24-leaves-under-leaves.png
  - jobs/wang-meng/evidence/2026-08-24-leaves-under-leaves.mp4
asked-as:
  - the leaves tear when they move
  - what should be behind a swinging leaf card
  - the trunk looks torn when the foliage moves
  - do I need a clean plate under foliage
  - bare ground shows when the canopy swings
---

## The held under-layer of a moving foliage cel is MORE FOLIAGE

> "The movement of these leaves and the background of the canvas should be the
> same leaves, so it doesn't look like it tears anything like the trunk of this
> tree, but instead it just moves the set of leaves off to the side, so right
> behind it is still a set of leaves." — Ryan, 2026-08-24

`hinge-foliage` swung its cards over a CLEAN PLATE — ground synthesised by
`clean-plate.py`, which under a tree means bare silk and rock. So every card
that rotated off its rest position exposed empty ground, and along the branch
that reads as the trunk being chewed away.

**The fix is to stop making a hole.** Leave the source intact underneath
(`--under hold`) and the sliver a card vacates shows the ORIGINAL leaf strokes,
because they were never removed. This is the cel-animation double layer: a
moving foliage cel is held over another sheet of foliage, so disocclusion
reveals plausible material by construction rather than by inpainting.

Measured on `s-pine-over-bridge`, 20 cards at 6°: the clean-plate version
punches through 31,737 px of card footprint, 10.4% of the crop. The held version
punches through none.

**Why this does not violate [[clean-plate-donor-scope]].** That verdict bans
SYNTHESISING foliage into a foliage-shaped hole — shiftmap once invented two
masses of orange autumn leaves where Wang Meng painted a blue-green pine. A held
under-layer invents nothing: those marks are Wang Meng's own, already in that
exact position, and merely not deleted. **Provenance is the test, not
appearance** — the same distinction that
[[copied-real-ink-over-inks-worse-than-flux]] turned on.

**The cost, stated.** At the swing extremes the same leaf appears twice — once
held, once moved — bounded by the swing angle (6° here). That is a soft doubled
edge against a guaranteed bare-ground reveal, and on this painting the doubling
is invisible while the gap was not.

**The general form:** when a technique needs a hole filled, first ask whether
the hole has to exist. Amplitude and layering are both cheaper than invention.
