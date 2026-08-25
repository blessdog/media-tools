---
id: uso-inkwash-is-the-approved-ink-renderer
kind: verdict
conflict-key: which-renderer-produces-the-approved-ink-look
status: live
supersedes: []
scope: >
  The ink-wash look Ryan has approved for this repo, as of 2026-08-12. The
  RECIPE is exact and was rendered at loraStrength 1.0 for bongpot's
  keyframes-v10 on 2026-06-10; media-tools' styles/inkwash/style.json later
  raised it to 1.35 for a different job, so the strength is a per-job choice,
  not part of the verdict. The THREE-CHANNEL architecture is general to any
  USO/Flux style transfer.
verified-on: 2026-08-12
evidence:
  - jobs/krea/VERDICTS.md
  - jobs/krea/references/
  - jobs/yakub-inkwash/yakub-inkwash.png.json
asked-as:
  - which renderer makes the ink wash look Ryan likes
  - what is uso-inkwash
  - how is the ink style actually produced
  - what checkpoint and lora make our ink frames
  - how do I separate style from subject in a prompt
---

## The look Ryan loves came from a reference IMAGE in a dedicated style channel — never from a style LoRA

> "I love this whole set. It was so quirky and unique. Really, really love this."
> — Ryan, 2026-08-12, on the four references he picked for this project

After a full day of Krea-2 rendering, **the only ink-wash look Ryan has
responded to positively is the one `uso-inkwash` produces** — and that renderer
was already in this repo. Graph builder: `tools/_uso.mjs` (`buildUsoGraph`).

```
provider      comfy (ComfyUI on a rented box — NOT a hosted API)
checkpoint    flux1-dev-fp8.safetensors
lora          uso-flux1-dit-lora-v1.safetensors        @ 1.0
model patch   uso-flux1-projector-v1.safetensors
clip vision   sigclip_vision_patch14_384.safetensors
dims          1152 x 640 (16:9) · guidance 3.5 · steps 20
              euler/simple · cfg 1.0 · denoise 1.0
```

**Three channels, and the separation IS the trick** (bible §5.8 — content,
identity and style are different inputs and must not be fused into one prompt):

| channel | input | wiring | what it controls |
|---|---|---|---|
| **style** | face-free texture swatch | `CLIPVisionEncode` → `USOStyleReference` | patches the MODEL — the medium is swappable without touching anything else |
| **identity** | photoreal plate | `VAEEncode` → `ReferenceLatent` → `FluxKontextMultiReferenceLatentMethod` | rides the CONDITIONING |
| **content** | short text, nothing about the medium | prompt | what happens |

**Why the style channel patches the model and not the prompt is the whole
point.** Swapping the swatch changes the medium and leaves subject and identity
untouched. A prompt that fuses them means changing one changes all three.

This is the same mechanism as Krea's style-reference route and **the opposite of
the published-LoRA route Ryan rejected** the same day
([[a-published-style-lora-is-somebody-elses-style]]). Note the LoRA is still in
the chain — what was rejected was a LoRA driven by a trigger phrase with no
reference channel at all.

**The locked swatch is an asset, not a sentence.** `styles/inkwash/style.json`
resolves it; job manifests record the full recipe per render (see
`jobs/yakub-inkwash/yakub-inkwash.png.json` for the shape). Never re-derive the
look from whichever render is newest on disk.
