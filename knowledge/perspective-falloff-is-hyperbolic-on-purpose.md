---
id: perspective-falloff-is-hyperbolic-on-purpose
kind: law
conflict-key: how-should-depth-levels-map-to-z
status: live
supersedes: [space-planes-in-disparity-not-depth]
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-AB-zspace-linear-vs-disparity.mp4
asked-as:
  - how should plane depths be spaced
  - should I even out the parallax
  - the foreground moves more than the background
  - it looks like a diorama
---

**Space depth planes evenly in z. The uneven scale response that produces is
PERSPECTIVE, not a defect.** `--z-space linear` is and stays the default.

Under `--plane-fit` the scale law is `z / (z − camZ)`, a hyperbola, so evenly
spaced planes give a strong near-field falloff: on z1's 10 levels the front step
is **12.3×** the back step. That ratio looks alarming written down, and it is
exactly what a real camera does — near things sweep, far things sit.

**Measured attempt to "fix" it, 2026-08-21.** Spacing the planes evenly in
disparity (1/z) linearises the response to 1.3:1 for an *identical* total near/far
differential — same depth, distributed evenly. Rendered as a 53s A/B against the
original. Ryan: *"From that shot, the even in depth actually wins."*

**Why the even version loses.** Equal separation between every plane is the
signature of **flat cards at even spacing — a diorama**, which is precisely what
depth is supposed to conceal. The falloff is the cue. Removing it removes the
thing that made the stack read as space rather than as layers.

**The trap, which is the transferable part.** A mathematically even distribution
is enormously persuasive on paper: it has a clean derivation, a named
justification (depth buffers and stereo rigs really are parameterised in 1/z),
and a table showing 12.3:1 → 1.3:1 at no cost. Every one of those statements is
true. The proposal was still wrong, because **"even" was never the goal — the
goal was "looks like distance,"** and nobody had checked whether those were the
same objective. Arithmetic cannot tell you which target you are aiming at. The
A/B took twelve minutes and settled it.

**What the original complaint actually points at.** Ryan's report was *"there were
CERTAIN SCENES where the mountain comes out way farther... than the background."*
Certain scenes, not the whole film. That is a per-plane ASSIGNMENT problem — a
mass put on a nearer card than it belongs on — and it is diagnosed by looking at
which planes those shots use, never by changing the global spacing law. See
[[plan-planes-at-shot-scale]].

`--z-space disparity` is REFUTED and must never be the default; it remains in the
tool only so the refutation stays reproducible.
