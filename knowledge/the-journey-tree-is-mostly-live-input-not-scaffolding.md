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
  - does rebuilding the living cycles cost money
  - will phase 0 invalidate the baked cycles
  - how do I free disk space on wang-meng
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

**`living/` is a live render input, and reaping it costs TIME, not money.**
`jobs/wang-meng/living/living-z<zone>.json` names every patch by ABSOLUTE path
into `journey/<zone>/living/<plane>__<region>/`, and `render-parallax.py --living`
opens those PNGs at every flight render. Delete them today and rendering breaks
until they are rebuilt.

**CORRECTED 2026-08-25 — the earlier version of this claim said reaping `living/`
"trades a paid generative regeneration for disk". That was wrong**, and the error
was conflating the cycles with the stack they were rendered against:

| | size | made by | costs |
|---|---|---|---|
| `journey/z*/layers-filled` | 171 MB | `inpaint-planes --method flux` | **paid GPU** |
| `journey/z*/living` | 16.3 GB | `hinge-foliage.py` → `build-zone-living.py` | **CPU only** |

Verified: both cutters import only `numpy`, `cv2` and `PIL` — **zero torch
imports**. The flux-generated artifact is the 171MB `layers-filled`, and nothing
in this cleanup or in PLAN.md Phase 0 touches it. The 16GB sitting on top of it
is pure CPU output. **One cost is recoverable with time and the other is not, so
the distinction decides what you are allowed to delete.**

**And the number that reframes the whole question: 98.5% of the cache is foliage,
and Phase 0 re-cuts every foliage card.**

```
foliage   17.25 GB   98.5%   510 region dirs   <- PHASE 0 re-cuts every one
water      0.25 GB    1.4%    24
figure     0.02 GB    0.1%     5
```

(Measured over 539 region dirs / 16.31 GB on disk; `sum-*` summit regions are
trees and count as foliage.) PLAN.md Phase 0 changes the branch-radius basis
**across all 170 regions**, so it does not preserve any foliage cut — it replaces
them wholesale. Only ~0.3GB of water and figure cycles survives it.

**So this was never a preservation question, and it should not be audited as
one.** The disk problem and the Phase 0 problem are the SAME problem: nobody
should spend a session carefully auditing 17GB that the next real piece of work
regenerates. **The order is: fix the cut, rebuild the cycles, and the disk
resolves itself because the rebuild overwrites.**

**One number nobody has, and it should not be guessed:** wall-clock for a full
scroll cycle rebuild. It has been done — commit `a0be4d0`, *"the whole scroll
rebuilt on the catalogue: moving leaf 19.4% -> 67.9%"* — so it is a known
quantity to somebody, just not measured here. **Time the first zone before
committing to all five.**

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
