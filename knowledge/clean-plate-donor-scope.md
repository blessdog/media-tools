---
id: clean-plate-donor-scope
kind: verdict
conflict-key: what-may-clean-plate-copy-from
status: live
supersedes: []
scope: >
  Any clean-plate fill whose hole is SURROUNDED BY MATERIAL OF THE SAME KIND as
  the thing being removed. Proven on a canopy at z5w s-compound-canopies. It
  does NOT apply to the figure-sized holes clean-plate was verified on in
  2026-08-19, where the surroundings were bare ground and ground was the only
  thing available to copy.
verified-on: 2026-08-20
evidence:
  - jobs/wang-meng/living/evidence-cleanplate-invented-foliage.png
asked-as:
  - the inpaint invented something
  - clean plate copied the wrong thing
  - fabricated detail in the fill
---

## Shiftmap will copy a tree into the hole where a tree was

`clean-plate.py --method shiftmap` fills a hole with the best-matching patches
found ELSEWHERE IN THE IMAGE. Removing one canopy from a crop that contains six
other canopies means the best match for the hole's context is other foliage, so
the synthesis copies it in. Measured on `s-compound-canopies`: the blue-green
pine at the top left was replaced with **two invented masses of orange autumn
leaves**, painted material Wang Meng never put there.

Zero fabrication is the one thing this project sells itself on. This is a
fabrication, produced silently by a tool whose own quality metric passed.

**The metric passed because the metric could not see it.** clean-plate reports
texture energy inside the hole against texture energy in the ring around it —
16.28 vs 16.35 — and reads a match as success. Copied foliage produces exactly
that match. A texture statistic cannot distinguish "the right weave" from "the
wrong content with the right weave", and the number was quoted as evidence
before anyone looked. Third time in two days that a texture statistic has been
believed over a picture; see [[canopy-by-texture-statistics]].

## The rule

**Every pixel of the same CLASS as the thing being removed must be masked, not
just the one being filled.** A masked pixel cannot be a donor, so masking all
the foliage in the crop leaves only ground for the synthesis to copy — which is
the only thing that is actually behind a tree.

In `build-zone-living.py`'s `foliage-motion` entry this means clean-plate gets
`--masks` for EVERY foliage region overlapping the crop, and the hinge then
takes its cards from just the one being animated.

## What this does not license

Growing the exclusion until nothing is left to copy. If masking the class leaves
too little ground in the search box, the honest answer is that the hole cannot
be synthesised from this picture, and the card should not swing far enough to
open it. Amplitude is cheaper than invention.
