---
id: the-pink-grid-is-splat-lattice
kind: verdict
conflict-key: what-is-the-pink-grid-diagnostic
status: live
supersedes: []
scope: >
  probe-parallax.py --marks on any image+depth pair. The GRID is a property of
  forward splatting and appears at any zoom; the SOLID magenta patches are real
  disocclusion and are what the instrument is actually for.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/evidence/2026-08-21-pink-grid-reproduced.png
  - jobs/wang-meng/evidence/2026-08-21-pink-grid-reproduced.mp4
  - tools/probe-parallax.py
asked-as:
  - the pink grid image how was it made
  - what is the magenta grid diagnostic
  - how do I see the displacement field
  - which tool made the pink lattice picture
  - how do I check whether a depth map has real parallax
---

## Nothing drew a grid

Ryan, 2026-08-21, holding a screenshot: *"Are you able to find how this picture
was created with the pink grid? Because that's when we were really cooking."*

    python3 tools/probe-parallax.py \
      --image jobs/wang-meng/motion/shot-real.png \
      --depth jobs/wang-meng/motion/pan/depth-authored.png \
      --marks --out probe.mp4

**The grid is not drawn.** `probe-parallax` FORWARD-SPLATS every pixel far-to-near
through a z-buffer instead of resampling. As the image expands, splatted pixels
spread apart and leave a regular one-pixel gap between them. Every gap counts as
a hole, `--marks` paints holes magenta (255, 0, 200), and that lattice of gaps IS
the pink grid. It is an artifact of the method, exposed on purpose.

**Why that makes it a good instrument.** The lattice WARPS around depth edges, so
the displacement field becomes a thing to look at rather than a number to trust.
Solid magenta patches are real disocclusion -- ground a near object uncovered
that the painting never contained.

**The trap the tool guards.** It reported `holeFractionFinal 0.2837` on the
reproduction, and roughly 24.8 points of that is splat lattice at zoom 0.18, not
tearing. Quote it without running `--null` and subtracting and you will report
catastrophic tearing where the real disocclusion is under one point. See
[[null-before-the-metric]].

**Provenance note.** This image is the one named in
[[evidence-lands-in-the-repo]] as the diagnostic that evaporated with its
session. The FILE was lost; the tool and its inputs were committed, so the
picture was reproduced exactly three days later. Recovery key: pickaxe the
distinctive constant (`git log -S`, `grep '255, 0, 200'`), not the filename.
