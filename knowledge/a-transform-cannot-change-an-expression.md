---
id: a-transform-cannot-change-an-expression
kind: verdict
conflict-key: what-kind-of-animation-does-a-face-need
status: live
supersedes: []
scope: >
  Character animation on a painted or drawn source. The MEASUREMENTS are from
  葛稚川移居圖's Ge Hong at native crop; the DISTINCTION is general to any 2D
  character work, including the podcast-animation style Ryan sent on 2026-08-22.
verified-on: 2026-08-22
evidence:
  - jobs/wang-meng/evidence/2026-08-22-transform-cannot-wink.png
asked-as:
  - can I make the character wink
  - is a laugh just a transform of the existing art
  - how do the kill tony animations get those faces
  - do I have to draw every frame
  - how much drawing does a mouth need
  - can existing ink be transformed into a new expression
---

## Four techniques, and only one of them is free

I told Ryan a wave was "existing ink transformed, same as the Kill Tony rig."
**That was overselling and he called it.** The rig half is right; the expressions
are drawn.

| technique | what it does | costs | Ge Hong today |
|---|---|---|---|
| **rigid transform** | moves pixels already painted — rotate, slide, scale | free, preserves brushwork exactly | ✅ the fan. `swing-card`, `walk-figure` |
| **deformation / warp** | stretches painted pixels — squash and stretch | distorts brushwork; banned on this painting by [[depth-may-resize-never-deform]], NOT banned on a new project | ✗ |
| **replacement** | a LIBRARY of separately drawn pieces, swapped per frame | one drawing per variant | ✗ nothing to swap to |
| **straight-ahead** | every frame drawn | most drawing, most life | ✗ |

**The measurement that settles it.** Ge Hong's whole face is 145×120 px and his
visible eye is a single tapered stroke about 30×12 px. Rotate that stroke and it
is still an open eye — see the middle panel of the evidence. **No transform of an
open eye produces a closed one, because the closed-eye ink does not exist
anywhere in the painting.** A wink needs exactly one new drawing.

Podcast-style animation (Kill Tony, Brad Neely) is **rigid transform for the
body and replacement for the face**: head tilts and hand moves are puppet
transforms, while the cartoon laugh and the phoneme mouths are drawn variants
swapped against the audio. Both, not one.

**The good news, and it is counter-intuitive:** crude is CHEAPER *and* is the
style Ryan prefers. Limited animation — few drawings, long holds, deliberate
stiffness — is the Brad Neely look. Polish is the expensive part and he does not
want it. A phoneme set is ~8-10 mouths (Preston Blair); a laugh is 4-6 drawings
on twos.

**What the toolbox owes this:** cutting the parts, the clean plate behind them,
rigid motion, and compositing at depth all exist. The missing piece is a
**replacement track** — swap drawing N at frame T — which is a small tool, not a
research problem. Drawing the variants is Ryan's half, and
[[invented-ink-is-allowed-in-the-painters-hand]] already permits it.
