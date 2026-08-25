---
id: the-2026-08-25-cleanup-pass-is-done
kind: verdict
conflict-key: what-is-the-current-cleanup-task
status: live
supersedes: [handoff-cleanup-pass]
scope: >
  The four-step cleanup the 2026-08-25 HANDOFF ordered, executed the same day.
  The SIZE figures are a snapshot; the two corrections to the handoff's own
  premises are the durable part.
verified-on: 2026-08-25
evidence:
  - jobs/wang-meng/HANDOFF.md
  - knowledge/the-journey-tree-is-mostly-live-input-not-scaffolding.md
  - knowledge/the-inkwash-probe-jobs-are-evidence-not-decisions.md
asked-as:
  - clean everything up
  - what should I clean up
  - is the cleanup pass finished
  - the repo is a mess
  - did the repo get under 10GB
---

## All four steps ran. Two of the handoff's own premises were wrong, and that is the lesson

| step | outcome |
|---|---|
| 1 · reap render bloat | `reap-frames.sh` found **0MB** — `film/frames/` was already clean. The bloat was elsewhere; steps 1 and 2 collapsed into one. |
| 2 · audit `journey/` | 7.4GB reaped. **32GB → 25.8GB.** `git status` clean throughout. → [[the-journey-tree-is-mostly-live-input-not-scaffolding]] |
| 3 · the other ten jobs | Six claims written; **nothing reaped, deliberately.** → [[the-inkwash-probe-jobs-are-evidence-not-decisions]] |
| 4 · re-read the routes | 127 cited paths checked. 2 real breaks, annotated in place. 0 violations, 0 unfindable. |

**The 10GB target was not met and should not be chased.** The repo is 25.8GB
because `journey/z*/living/` is 16.8GB of baked cycle frames that
`render-parallax.py --living` opens at every flight render, named by absolute
path in `living/living-z<zone>.json`. It is a live input, not scaffolding, and
it is baked against a `layers-filled` stack produced by `inpaint-planes --method
flux` — a generative step. Reaping it trades a paid regeneration for disk.

**Correction 1 — a directory name in a handoff is a hypothesis, not a
measurement.** The handoff sent this pass to audit "the 25GB of `layers-*`
stages". All five stages across all nine zones total **794MB**. One `du -sm` on
every child would have redirected the whole pass, and it costs one command.
**Measure the tree before auditing the category you were pointed at.**

**Correction 2 — "reap to evidence" was the wrong instinct for the ten probe
jobs.** They total 390MB, 1.5% of the repo, and every large item in them IS the
evidence the new claims cite. The valuable half of step 3 was writing the claims;
the reaping half would have destroyed their support to recover 1.5%. **When a
cleanup step says both "write the claim" and "then delete", the claim is the
deliverable and the delete needs its own justification.**

**Still open, recorded so it is not mistaken for done:** the handoff's scope note
stands — seven other repos sit under `~/projects` (`anselman`, `bible`,
`freaksource`, `jobcannon`, `promptshark`, `recorder`, `write-on`) and were NOT
touched. If "all our work everywhere" was meant, that is a separate pass and
needs its own handoff. And `jobs/ryan-portrait` is a controlled model bake-off
with **no recorded winner** — a real gap, cheap to close, and only Ryan's eyes
can close it.
