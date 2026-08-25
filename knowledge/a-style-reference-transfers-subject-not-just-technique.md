---
id: a-style-reference-transfers-subject-not-just-technique
kind: verdict
conflict-key: what-does-a-style-reference-image-carry-across
status: live
supersedes: []
scope: >
  Reference-image style channels on hosted and local diffusion models, measured
  2026-08-12 on Krea-2's style-reference route (jobs/krea/renders-ref, 16
  images) and the hosted krea-2-medium/large probe (jobs/krea-probe). The
  MECHANISM is general to any image-as-style-input route, USO included.
verified-on: 2026-08-12
evidence:
  - jobs/krea/VERDICTS.md
  - jobs/krea/references-clean/
  - jobs/krea-probe/compare.png
asked-as:
  - does a style reference image leak the subject
  - why did the wrong clothes appear in my render
  - how do I stop the red seals coming through
  - what does a reference image actually transfer
  - should I crop my style references
---

## The reference channel carries the look far more faithfully than a trigger phrase — and it carries the SUBJECT too

Measured 2026-08-12 on 16 reference-driven renders. **What transferred
correctly:** the corner ink vignette, the cream paper and the muted palette all
carried onto entirely new subjects. That is the reference channel doing its job,
and doing it better than any trigger phrase managed.

**What ALSO transferred, uninvited:**

- the doorway figure came out wearing **the paisley shirt from `s05`**
- **`s06`'s teal** bled into the water and into a washing-machine drum

**This is the same mechanism that would have copied the red seals** off a
Chinese painting used as a reference, which confirms Ryan's instinct about them
exactly. A style reference is not a technique extractor — it is an image, and
the model takes what it finds in it.

**The fix is mechanical, not prompt-side: crop the reference.** Corner-cropping
at 7% removes the seals automatically; `jobs/krea/references-clean/` holds
seal-free versions of all seven. Choose face-free, subject-poor swatches — which
is exactly why `uso-inkwash`'s style channel is specified as a *face-free
texture swatch* ([[uso-inkwash-is-the-approved-ink-renderer]]) rather than a
finished picture.

**A prompt cannot undo this.** `jobs/ryan-portrait`'s instruction spells out
*"Take only the painting technique from the second image — never its subject,
figures, scenery or composition"* and the leakage is a property of the channel,
not of the wording. Control the pixels you feed it.

**Unspent option, recorded so it is not re-derived:** the clean-reference run
(`jobs/krea/run-ref2.mjs`) was written and never executed — three reference sets
including the kontext-pro frames, all seal-free. One box-hour away if it is ever
worth answering. The hosted `krea-2-medium`/`large` route with up to 10
references (`jobs/krea-probe`) **came closest of anything that day and was
abandoned over subject matter, NOT because it failed.**
