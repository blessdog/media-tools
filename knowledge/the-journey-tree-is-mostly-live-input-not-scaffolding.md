---
id: the-journey-tree-is-mostly-live-input-not-scaffolding
kind: verdict
conflict-key: what-in-the-journey-tree-can-be-reaped
status: live
supersedes: []
scope: >
  jobs/wang-meng/journey as it stood on 2026-08-25, audited by grep over
  tools/ and jobs/wang-meng/ for every directory over 40MB. The per-stage
  verdicts hold until build-zone.sh's chain changes; the METHOD -- prove a
  reader with grep before calling a stage scaffolding -- is general.
verified-on: 2026-08-25
evidence:
  - jobs/wang-meng/journey/build-zone.sh
  - jobs/wang-meng/living/living-z3w.json
  - jobs/wang-meng/film/reap-frames.sh
asked-as:
  - can I delete the layers-cut and layers-sealed stages
  - what in the journey tree is safe to reap
  - why is jobs/wang-meng 25GB
  - is the living directory scaffolding or an input
  - which journey directories are read by a live tool
---

## The 25GB was never the `layers-*` stages — it is the baked living layer, which is a live input

The 2026-08-25 handoff sent the next session to audit "the 25GB of `layers-*`
stages." **All five `layers-*` stages across all nine zones total 794MB.** The
25GB was `living/` (16.8GB), probe frame dumps (3.7GB), `measure-work` (2.7GB)
and `living-work` (886MB). Auditing the named directory would have freed under
3% of the target while the actual bloat sat untouched.

**Every `layers-*` stage has a live reader**, proved by
`grep -rn "<stage>" --include="*.py" --include="*.sh" tools jobs/wang-meng`:

| stage | size | read by | verdict |
|---|---|---|---|
| `layers-cut` | 181MB | `build-zone.sh`, `gen-geometry.py` | LIVE |
| `layers-heal` | 47MB | `build-zone.sh` only | **contained** — see below |
| `layers-sealed` | 165MB | `build-zone.sh` (pin step) | LIVE (chain input) |
| `layers-pinned` | 163MB | 7 files inc. `remap-living.py`, `motion/pan` probes | LIVE |
| `layers-filled` | 174MB | 13 files inc. `build-rise.sh`, `blender-multiplane.py` | LIVE — the deliverable stack |

`layers-heal` is the only genuine containment case: `build-zone.sh:101`
`shutil.copy`s every healed plane INTO `layers-cut`, so `layers-cut` is a strict
superset. It is 47MB and re-running the chain without it costs a re-segment, so
it is kept as a chain input, not reaped. **The category is not where the space
is, so the containment rule bought nothing here.**

**`living/` is a live render input and must not be reaped.**
`jobs/wang-meng/living/living-z<zone>.json` names every patch by ABSOLUTE path
into `journey/<zone>/living/<plane>__<region>/`, and `render-parallax.py --living`
opens those PNGs at every flight render. It is 16.8GB and it is not scaffolding.
It is also not cheaply rebuildable: `layers-filled` is produced by
`inpaint-planes --method flux`, a generative step, and the cycles are baked
against that specific stack (see
[[a-living-layer-is-baked-against-its-stack]]). Reaping it trades a paid
regeneration for disk.

**What WAS scaffolding, and was reaped 2026-08-25 (7.4GB, nothing tracked lost):**

- `journey/z*/_ab/*/` — A/B probe frame dumps (`living`, `living-6/12/20`,
  `static`). Zero readers; `grep -rn "_ab" knowledge/ docs/` returns nothing.
  The findings survive as claims whose evidence is the ENCODED mp4/json in
  `living/` — [[branch-radius-scales-with-the-tree]] cites five files, all of
  which still exist. The `path.json` beside each dump is kept.
- `journey/z*/measure-work/` — 2.7GB, already gitignored as reproducible from
  `measure-invented.py`.
- `journey/z*/living-work/**/*.png|mp4` — the cutting floor; `cycle.json`
  manifests are the record and are kept.

**The rule this leaves behind: measure the tree before auditing the category a
handoff names.** `du -sm` on every child costs one command and would have
redirected the whole pass. A directory name in a handoff is a hypothesis about
where the bytes are, not a measurement.
