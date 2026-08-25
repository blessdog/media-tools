---
id: a-published-style-lora-is-somebody-elses-style
kind: refuted
conflict-key: can-a-published-style-lora-supply-our-ink-look
status: live
supersedes: []
mechanism: >
  A published style LoRA encodes one person's taste as WEIGHTS, and the model
  exposes no channel through which to supply your own. The only control surface
  left is the trigger phrase, and a phrase cannot carry a look. The route that
  works gives taste its own INPUT -- a reference image in a dedicated style
  channel -- which is why uso-inkwash survived the same day's judging and this
  did not. Rejected by Ryan across 24 bare renders and 16 reference-backed ones.
verified-on: 2026-08-12
evidence:
  - jobs/krea/VERDICTS.md
  - jobs/krea/renders/all.png
asked-as:
  - can we use a published ink wash LoRA
  - should I download a style LoRA from civitai for the ink look
  - did the krea ink LoRAs work
  - why were darkbrush and linen scroll rejected
---

## Somebody else's trained style is somebody else's style, and the odds of it being the one in Ryan's head were never good

**Rejected by Ryan, 2026-08-12:** `krea/Krea-2-LoRA-darkbrush` and
`ilkerzgi/krea-2-chinese-ink-linen-scroll-lora`. His words: *"I actually don't
really like these Lora's"*, clarified to *"I don't like the Lora's raw. Without
giving it any reference style of my own."*

Evidence: 24 renders, 6 subjects × 2 LoRAs × turbo/raw, seed 20260812, strength
0.8, at 1024². A second round of 16 (`renders-ref/`) added Ryan's own reference
images on top and was also rejected: *"I don't like these."*

**SCOPE — this refutes the LoRA driven by TRIGGER PHRASE ALONE, and the
published-LoRA-plus-reference route.** It does NOT refute a LoRA as a component:
the look Ryan does love has `uso-flux1-dit-lora-v1` in the model chain, driven
by a reference image in a dedicated style channel
([[uso-inkwash-is-the-approved-ink-renderer]]). Both parts, together.

**The mechanism, which is why this generalises:** a published style LoRA encodes
a specific person's taste as weights. There is no channel through which to
supply your own taste, so the only control surface is the trigger phrase — and a
phrase cannot carry a look. The route that works gives taste its own INPUT
(an image), which is why it survived and this did not.

**What the run established anyway, and is still true:**

- The stack works — Krea-2 on a rented 5090, 24/24 renders, ~13s each at 1024².
- `darkbrush` held across two faces, a wide landscape, a dim interior, an animal,
  a macro and a suburban garden. Technically sound; Ryan just doesn't want it.
- `linen scroll` ran at 0.8 against a card specifying 1.0–1.25 and came back
  nearly photographic — **under-driven, and never retested.** If this is ever
  revisited that is the fix, but Ryan has seen it and said no.
- **`krea2_raw` does not work for inference with turbo-trained LoRAs** — washed
  out and muddy on both. Consistent with raw being the LoRA-training and control
  substrate rather than a quality tier. Do not reach for it as "the better one".

**Not refuted, because never run:** plain Krea-2 with no LoRA at all, img2img
from Ryan's own footage at denoise <1, any resolution other than 1024², and the
hosted `krea-2-medium`/`large` route with up to 10 style references. Ryan
explicitly rejected the overclaim — *"I wouldn't say the whole Kira surface has
been tested"* — and he was right. This claim covers two LoRAs at one strength,
one resolution, on turbo.
