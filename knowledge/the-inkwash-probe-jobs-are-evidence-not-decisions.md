---
id: the-inkwash-probe-jobs-are-evidence-not-decisions
kind: verdict
conflict-key: what-are-the-ten-old-inkwash-job-dirs-for
status: live
supersedes: []
scope: >
  The ten non-wang-meng job directories under jobs/ as they stood 2026-08-25.
  An inventory of what each probe was and where its finding went; the per-job
  facts are dated and will drift if the dirs are worked on again.
verified-on: 2026-08-25
evidence:
  - jobs/krea/VERDICTS.md
  - jobs/ryan-portrait/run.sh
  - jobs/sheen-inkwash/renders/contact-sheet.png
asked-as:
  - what is in the old inkwash job folders
  - can I delete dog-inkwash and knife-inkwash
  - what was ryan-portrait for
  - which old jobs carry a real finding
  - is stitch-test still needed
---

## Ten probe dirs, audited — every finding that survives is now typed, and none of the dirs is safe to treat as a decision

Bible §5.8: *a file named `*-test` or `*-probe` is evidence of an experiment,
not of a decision.* Never rebuild a locked creative surface around their outputs.

| job | what it was | where the finding went |
|---|---|---|
| `krea` | 40 Krea-2 renders + 192 lines of dated verdicts | [[a-published-style-lora-is-somebody-elses-style]], [[uso-inkwash-is-the-approved-ink-renderer]], [[a-style-reference-transfers-subject-not-just-technique]] |
| `krea-probe` | hosted `krea-2-medium`/`large` with Ryan's own frames as references | [[a-style-reference-transfers-subject-not-just-technique]] — *came closest of anything that day*, abandoned over subject matter, NOT because it failed |
| `inkwash-flf2v` | 6 first-last-frame clips, LTX 2.3 and 2.5 | [[flf2v-paints-one-image-into-another]], [[style-is-solved-control-is-the-problem]] |
| `ryan-portrait` | **model bake-off** — one photo, the LOCKED swatch as style channel on 11 ref-capable models, so the only variable is the model | manifests + `logs-*.txt` per model; `open-vs-closed.png` and `cmp*.png` are the comparison strips. No single winner is recorded in the repo — do not infer one from file dates |
| `sheen-inkwash` | the first end-to-end lane: transcript → shots → plates → inkwash frames → clips | `renders/contact-sheet.png`, cited as Phase-5 evidence and explicitly whitelisted in `.gitignore` |
| `yakub-inkwash` | single uso-inkwash still, manifest intact | the manifest is the reference SHAPE for a render record — full recipe, sampler, seed |
| `dog-inkwash`, `knife-inkwash` | one source + one output each, no manifest | **probes with no surviving finding.** Kept as before/after pairs only |
| `ryan-ink` | six fresh ink looks × 2 models, `--raw` so no swatch is inherited | **renders no longer on disk; `run.sh` is all that survives.** Its value is the discipline in its header: *"Nothing inherited… Every look below is a CANDIDATE ONLY. Nothing is approved until Ryan says so."* |
| `stitch-test` | stitch-clips over real mixed-source footage | `real-cut.mp4`; note `shots.txt` points OUT of this repo into `mediaStudio/cutwork`, so it is not self-contained |

**Two things this audit found that a filename would not have told you.**
`ryan-portrait` is a controlled bake-off — same source, same swatch, same
instruction, model as the only variable — which makes its manifests genuinely
reusable, but **no verdict was ever written down**, so the winner is not
recoverable from the repo. And `ryan-ink`'s outputs are gone while its script
remains, which is the failure mode
[[an-absence-is-invisible-in-the-output]] describes: the directory looks like a
job and contains no result.
