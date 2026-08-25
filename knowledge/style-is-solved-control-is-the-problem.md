---
id: style-is-solved-control-is-the-problem
kind: verdict
conflict-key: does-the-ink-wash-look-need-a-trained-lora
status: live
supersedes: []
scope: >
  The ink-wash look on hosted i2v and image models as measured 2026-08-12 across
  jobs/inkwash-flf2v (6 clips, LTX 2.3 and 2.5) and jobs/krea (40 renders,
  Krea-2). Holds for a medium the base models have already absorbed; a genuinely
  unseen medium is a different question and was not tested.
verified-on: 2026-08-12
evidence:
  - docs/research/2026-08-12-inkwash-motion-handoff.md
  - jobs/inkwash-flf2v/clips/A-ink-becomes-painting.mp4
  - jobs/krea/VERDICTS.md
asked-as:
  - should we train an ink wash LoRA
  - do we need a style LoRA for the ink look
  - why did the museum corpus work get abandoned
  - does the style drift to photoreal during i2v
  - what is actually hard about the ink wash pipeline
---

## Across every clip rendered, not one output drifted to photoreal — so a style LoRA would teach a model a look it already holds

Measured 2026-08-12: six clips, two models (LTX 2.3 and 2.5), four of which
FAILED at what they were asked to do. **Every failure was CONTENT drift** — the
wrong man, invented reeds, an unrelated scene. **The medium held in all of
them**, start to finish: paper grain present throughout, the blue washes
arriving as washes, no slide toward photographic rendering in any frame.

**This killed the session's own plan.** The day had started on corpus
collection and a museum pull aimed at training a style LoRA. If the base model
already renders the medium correctly in 6/6 outputs, that training target is
already met and the corpus work was aimed at the wrong problem.

The same result arrived independently from the image side. `jobs/krea` spent 40
renders and about $0.30 establishing that two published ink LoRAs run bare are
rejected (see [[a-published-style-lora-is-somebody-elses-style]]), while the
look Ryan actually approves came from a **reference image in a style channel**,
not from a trained style at all — see [[uso-inkwash-is-the-approved-ink-renderer]].

**So spend the effort on control, not on style.** Which man, which scene, which
composition — that is where every failure was, and it is not a thing a style
LoRA addresses.

**One disproven fix, recorded so it is not retried:** `frameGuideStrength: 1.0`
was the obvious answer to LTX 2.3's content drift and **made it worse** — the
output went flat and graphic. LTX 2.3 is materially worse than 2.5 at this task
across 4 shots and 2 guide settings, and no guide setting closes the gap.
