---
id: depth-comes-from-the-breath
kind: procedure
conflict-key: which-renderer-for-a-camera-move
status: live
supersedes: [two-renderers-one-data-source]
sibling: light-parallax-is-011-and-continuous
applies-when: >
  authoring ANY camera move over the wang-meng plane stacks, or choosing a
  renderer for one. render-parallax --plane-fit is the renderer for everything.
  Depth comes from camZ -- a BREATH laid continuously across the leg -- and a
  move that should read as 2.5D must carry one.
not-when: >
  a move that is deliberately flat. A traverse at camZ = 0 is a PAN BY
  CONSTRUCTION, not a weak parallax: measured 2026-08-21, collapsing all 13
  plane depths onto one changed 0 of 2,073,600 pixels. Use that on purpose or
  not at all. And never render-warp on this painting -- Ryan, 2026-08-21: "too
  extreme. It really distorts the painting."
route: >
  render-parallax.py --plane-fit --z-step 0.30 --geometry ... --living ...
  --relief <zone>/relief.json, over a path whose z breathes (cosine, peak 0.18,
  period clamped to the leg, every leg starting and ending at z=0). Authored by
  jobs/wang-meng/film/author-rise.py --breathe; built by film/build-rise.sh.
  --relief only engages when camZ != 0, so the breath is what switches
  within-plane surface shape on.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-BREATHE-smooth.mp4
  - jobs/wang-meng/evidence/2026-08-21-AB-breathe-smooth-vs-relief.mp4
asked-as:
  - cards or warp
  - which renderer should I use
  - how do I give a leg depth
  - the shot looks flat
---

**One renderer, and the depth is in the path.** The retired
`two-renderers-one-data-source` routed traverses to cards and pushes to warp.
Both halves are superseded on this painting:

- **Cards do not give a traverse any parallax.** That claim said cards were
  right for a traverse "because real occlusion is what a traverse reveals."
  Under `--plane-fit` at `camZ = 0` every plane takes the identical scale AND
  the identical sampling offset, so thirteen planes translate as one sheet.
  Measured: flattening every depth changed **0 of 2,073,600 pixels**. Ryan, on
  the result: *"I'm seeing more panning, more of the easy pan shots."*
- **Warp is rejected on this painting**, not merely mis-routed. Its strain has
  to go somewhere and where it goes it stretches brushwork —
  `depth-may-resize-never-deform`.

**So depth is a property of the PATH, not of a renderer choice.** Lay a breath
across the leg: `z` rises and returns on a cosine, peak 0.18, period clamped so
even a short leg contains one full breath, and **every leg starts and ends at
z = 0** so the dissolves cut on the painting exactly as composed.

Ryan's verdict, first approval of any depth technique on this project,
2026-08-21: *"Breathe smooth is looking good… I feel like we're starting to
finally make a little bit of traction,"* and then *"very impressed with breathe
smooth."*

**What survives from the retired claim, and it is the load-bearing part:** ONE
DATA SOURCE. The moment two renderers read different stacks they become two
pipelines and a behaviour difference is a bug in one or both.

**The two failure shapes to check before rendering a leg:**

1. `z` flat across the traverse → a pan, however deep the stack.
2. `z` spiked only inside the approaches → worse, because the spikes become the
   only depth in the shot and therefore read as zooms.
