---
id: rigid-cards-preserve-the-brushwork
kind: law
conflict-key: why-does-animated-foliage-read-as-a-blob
status: live
supersedes:
  - leaf-marks-are-the-second-scale
scope: >
  Every animation of an existing painting or drawing in this repo -- foliage,
  robes, water, anything cut from someone else's brushwork.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/AB-leafmarks-s-pine-over-bridge.mp4
  - jobs/wang-meng/evidence/2026-08-21-leaf-marks-pinebridge.png
asked-as:
  - the animation deforms the aesthetic
  - the leaves look too aggressive
  - should I animate individual leaf marks
  - the foliage is one green blob
  - how big should a foliage card be
---

## Move the drawing. Never redraw it.

Ryan, 2026-08-21, having asked for per-leaf twinkle that morning and seen it by
afternoon: *"This new method of cutting out the leaves is a little too
aggressive. It deforms the aesthetic. What we had before was actually looking
good. I think if we just cut out little chunks, bushels of branches, and wave
those around, like how we were doing before, that's a better method."*

**The mechanism, and it is the whole law.** A CARD is moved by a rigid transform,
so every brushstroke inside it arrives at the new position unchanged -- the same
ink, the same taper, the same dry-brush edge, just somewhere else. Rotating and
narrowing each leaf MARK deforms each stroke individually. That is not animating
the painting; it is **redrawing** it, several times a second, in a hand that is
not Wang Meng's.

The theory that produced the mistake was not wrong. A real canopy does carry two
scales of motion, secondary action IS why foliage shimmers, and the
distance-transform watershed found the leaf atoms cleanly (433 marks from 21
cards on the pine). Every step was sound and the result still failed, because
the goal here is not a physically plausible tree. **The goal is this painting,
in motion, still looking painted by the person who painted it.**

**So the unit of motion is the BUSHEL: a chunk of branch with its leaves on it.**
Big enough that its internal brushwork is carried intact, small enough that
neighbouring bushels can move out of phase and the crown does not read as a slab.
The card decomposition already does this; nothing below the card is ours to move.

**What survives from the retired verdict:** swing 12 (his ladder verdict), the
attachment pivot, and the watershed itself, which is still the right tool for
finding leaf atoms should something ever need them -- `--leaf-marks` stays in
`hinge-foliage` as an off-by-default flag whose docstring now records that it is
NOT for animating existing brushwork.

**The general form, worth carrying to any project that animates found artwork:**
when a technique is theoretically correct and the output still looks wrong, check
whether the technique is modifying the SOURCE MATERIAL rather than moving it.
Fidelity to the medium beats fidelity to the physics. A cel animator cutting a
tree out of a background painting cuts along the branches for exactly this
reason -- the cut is free, the redraw is not.
