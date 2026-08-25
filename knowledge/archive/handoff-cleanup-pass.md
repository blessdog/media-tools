---
id: handoff-cleanup-pass
kind: open
conflict-key: what-is-the-current-cleanup-task
status: superseded
supersedes: []
superseded-by: the-2026-08-25-cleanup-pass-is-done
proven: false
verified-on: 2026-08-25
evidence:
  - jobs/wang-meng/HANDOFF.md
asked-as:
  - clean everything up
  - what should I clean up
  - the repo is a mess
  - where is the handoff
  - how do I consolidate the work
  - what is the cleanup pass
---

## READ `jobs/wang-meng/HANDOFF.md` — the cleanup pass, in order

Ryan, 2026-08-25: *"clean everything up and get all of our everything, all the
work we've done into one coherent place."*

**First check you are in the right place.** If the SessionStart banner says
"THIS PROJECT HAS NO KNOWLEDGE STORE", the session was opened at `~/projects`
instead of in this repo — **stop and reopen.** That happened on 2026-08-25 and
hid all 60 claims for a whole session. See [[repo-root-is-the-session-root]].

**Measured 2026-08-25:** 32GB total, 25GB in `journey/`, 57,879 PNGs (7.2GB),
504 MP4s (1.7GB), 2,473 tracked files, **0 untracked**. Nothing is at risk of
being lost; this is bloat, not loss.

Four steps, in order:

1. **Reap render bloat** — `jobs/wang-meng/film/reap-frames.sh` (dry run first).
   Done when the repo is under 10GB and `git status` is clean.
2. **Audit `journey/`** — the 25GB of `layers-*` stages. A stage whose output is
   fully contained in a later stage is scaffolding; prove it with `grep`, never
   guess. `layers-filled` is what `blender-multiplane.py` reads.
3. **The other ten jobs** — old inkwash probes. Do NOT delete. For each: is its
   finding already a claim? If not, **write the claim first**, then reap to
   evidence.
4. **Re-read the routes** — moving files breaks claims that cite them. Run
   `check-knowledge.py` and `check-retrieval.py`.

**Scope:** media-tools only. Seven other repos sit under `~/projects`. If Ryan
meant everything everywhere, that is a separate pass — ASK, do not assume.

Related: [[rise5-is-the-current-plan]], [[archive-never-delete-a-failed-approach]].
