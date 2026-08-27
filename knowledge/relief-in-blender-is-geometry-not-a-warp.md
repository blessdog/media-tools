---
id: relief-in-blender-is-geometry-not-a-warp
kind: verdict
conflict-key: how-does-relief-work-in-the-blender-multiplane-lane
status: live
supersedes: []
sibling: tilt-slopes-do-not-survive-becoming-rotations
verified-on: 2026-08-26
scope: >
  tools/blender-multiplane.py --relief, measured on z3w's five relief maps at
  1080x1920. The TRADE-OFF is general to any depth map turned into geometry;
  the specific numbers are z3w's.
evidence:
  - jobs/wang-meng/evidence/2026-08-26-z3w-relief-vs-flat.png
  - tools/blender-multiplane.py
asked-as:
  - can blender use the depth maps
  - why are we feeding flat images into blender
  - how do I use relief in the blender renderer
  - does the grayscale depth data help blender
  - the card edges are wavy
  - relief changes frame zero
---

## The depth maps were being thrown away, and wiring them in is not free

Ryan, 2026-08-26: *"you're running a raw image in when we have the 3D data, the
grayscale. Wouldn't that help Blender to parse apart the layers?"* He was right:
`render-parallax.py` has taken `--relief` since 2026-08-23 and the Blender port
had no such flag. Five z3w planes carry relief maps that the Blender lane
ignored entirely.

**Now wired**: each relieved plane is built as a subdivided grid
(`--relief-subdiv`, default 192 per side) with a **Displace** modifier driven by
its relief PNG. `mid_level = 128/255` and `strength = band × 255/127/2` reproduce
render-parallax's `dz = (map−128)/127 · band/2`. Local Z is the plane normal and
points at the camera after the 90° rotation, so bright moves toward the viewer.

**A Displace modifier can only move vertices that EXIST.** On the default
four-vertex image plane it produces a flat quad at a slight angle and looks like
nothing happened. The grid is the whole fix.

**The trade-off, measured on z3w at rest (frame 1, no camera movement):**

| | flat | relief |
|---|---|---|
| pixels changed at rest | — | **24.69%** (mean 6.98) |
| pixels changed after the dolly | — | 32.72% (mean 9.52) |
| self-motion across the shot | 32.95 | 33.04 |

**Two costs, both structural, neither a bug:**

1. **Frame zero is no longer the painting.** render-parallax makes displacement
   identically zero at camZ=0 *specifically* to honour `layers.json`'s "frame
   zero must render byte-identical to the source stack". Real geometry cannot:
   a bump toward the camera is a bump when the camera is still.
2. **Card EDGES displace too**, so a cut boundary stops matching its neighbour —
   visible as a wavy bottom edge in the evidence. Between adjacent planes that
   is a seam risk, not just a silhouette change.

**And relief adds almost nothing to the AMOUNT of motion** at z3w's authored
bands (32.95 → 33.04). Its value is within-card shape, not parallax budget —
so it does not rescue [[z3w-depth-sits-below-a-16x9-frame]].

**Unit ambiguity, unresolved:** the bands (0.278) were authored against
render-parallax's z units, whose default `--z-step` is 0.035 while this tool's is
0.30. Whether 0.278 means the same distance in both is UNMEASURED; `--relief-scale`
is the dial until someone measures it. Do not treat the current look as tuned.
