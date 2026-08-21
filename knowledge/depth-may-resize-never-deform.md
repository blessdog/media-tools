---
id: depth-may-resize-never-deform
kind: law
conflict-key: what-kind-of-depth-effect-is-allowed-on-this-painting
status: live
supersedes: []
verified-on: 2026-08-21
asked-as:
  - which parallax technique is allowed
  - he says it distorts the painting
  - how do I add depth without wrecking the brushwork
  - warp or cards or breathe
---

**Depth may change how big things are relative to each other. It may never
change where they are relative to each other, and it may never change the shape
of a mark.** Ryan rejected three techniques in one afternoon, 2026-08-21, and
every rejection was the same sentence — *"it really distorts the painting."*

| technique | what it changes | verdict |
|---|---|---|
| multiplane truck (`--truck`) | WHERE things are, and permanently | rejected |
| sheet warp (`render-warp`) | the SHAPE of the brushwork | rejected — *"too extreme"* |
| breathe (differential scale from camZ) | HOW BIG things are, returning to zero | *"kind of cool"* |

**Why the survivor is structurally different, not just gentler.** Under
`--plane-fit`, scale is `z / (z − camZ)`, a function of camera POSITION. It is
exactly 1.000 for every plane at `camZ = 0`, so the composition is precisely as
painted whenever the camera is at rest, and every departure returns. The other
two accumulate or deform: a truck's offset is an integrated rate with no
equilibrium, and a warp's strain has to go somewhere and where it goes it
stretches the brushwork — its own docstring says so.

**The reason this painting is stricter than footage.** 葛稚川移居圖 is built on
散点透視, many local viewpoints rather than one. Its internal geometry is a
composition, not a record of a scene, so any change to it is visible as a change
to the ARTWORK rather than to the camera. Photographic footage forgives a warp
because the viewer has no memory of the true positions; a painting does not,
because the composition IS the subject.

**So the allowed vocabulary for depth on this project is:** differential scale
from `camZ`, spent as a breath (in and back out) or as an approach (in, hold,
out). Nothing else has passed. Before proposing any new depth technique, ask
which column of the table above it lands in — if it is not "how big", it is
already refuted and does not need rendering to find out.

**Corollary on authoring.** `render-parallax`'s `sample()` is piecewise
smoothstep, which eases to ZERO VELOCITY AT EVERY KEY. A breath authored as 21
half-second samples stops and restarts 21 times and reads as a stutter, not as a
technique — Ryan: *"it's so choppy, it looks like you're stuttering through
it."* Author POSES (rest, full breath, rest), never samples.
