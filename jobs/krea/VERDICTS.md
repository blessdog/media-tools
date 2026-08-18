# Verdicts — krea lane

Ryan's judgements, in this lane, dated. Nothing else counts as one.

---

## 2026-08-12 — the style-reference route: ALSO REJECTED

> "I don't like these."

`renders-ref/` — 16 images. Krea-2 turbo + `krea2_style_reference` LoRA, driven
by reference images Ryan picked himself, with and without a second style LoRA
stacked. Two reference sets (three bongpot frames blended; his own
seedream-5-pro portrait), two subjects, seed 20260812.

So two Krea routes are rejected: **LoRA alone**, and **reference image with
LoRA**.

### CORRECTION — that is NOT "the whole Krea surface"

I wrote that first and Ryan called it: *"I wouldn't say the whole Kira surface
has been tested."* Correct. What was actually tested is **two published ink
LoRAs, at one strength (0.8/1.0), at one resolution (1024²), on turbo** — bare,
then with a reference. Everything below is untouched:

**Never rendered at all**
- Krea-2 with **no LoRA in the chain**. All 40 renders had a style LoRA or the
  style-reference LoRA. Plain Krea-2 has literally not been seen.
- **img2img from Ryan's own footage** (denoise <1) — his original goal, and the
  one thing the hosted API could not do.
- Any resolution or aspect other than 1024².

**On the box, barely exercised**
- `krea2_softwatercolor` — only ever stacked on a reference, never alone.
- `krea2_raw` — only with turbo-trained LoRAs at GUESSED step counts. Never with
  correct settings, never with the reference route, and never for its actual
  purpose: LoRA training and control conditioning.

**Not pulled**
- Seven more first-party Krea LoRAs (dotmatrix, sunsetblur, vintagetarot, …).
- Three more community ink LoRAs: `krea-2-misty-ink-wash`,
  `krea-2-monochrome-ink-wash`, `krea-2-expressive-sumi-brush`.

**Strength never varied.** Linen scroll's card specifies 1.0–1.25; it ran at 0.8
both times and may have been under-driven in both.

**Whole routes untouched**
- Hosted `krea-2-medium`/`krea-2-large` with `style_reference_images` — **up to
  10 references** against the 3 the local node accepts, plus `creativity` and
  `moodboard`. The single early test on that route (Ryan's own frames as
  references, `jobs/krea-probe/`) came closest of anything all day. It was
  abandoned over the bongpot subject matter, NOT because it failed.
- Training a Krea LoRA on frames approved in this lane — `fal-ai/krea-2-trainer`
  or locally on raw.
- Krea's hosted Wan: reference-guided video, Animate, video restyle.

### What the run proved technically, regardless

- The reference channel **does** transfer the look far more faithfully than a
  trigger phrase — the corner ink vignette, cream paper and muted palette all
  carried onto entirely new subjects.
- It also transfers **subject**, not just technique. The doorway figure came out
  wearing the paisley shirt from `s05`, and `s06`'s teal bled into the water and
  the washing-machine drum. This is the same mechanism that would have copied
  the red seals, and it confirms Ryan's instinct about them exactly.
- Corner-cropping references at 7% removes seals automatically —
  `references-clean/` holds seal-free versions of all seven.

### Where that leaves it

After a full day, **the only ink-wash look Ryan has responded to positively is
the one `uso-inkwash` produces** — and that renderer is already in this repo
(`tools/_uso.mjs`), already proven, and is what made the frames he keeps
returning to.

Krea 2 may simply not be the tool. That is a legitimate finding, not a failure:
it cost about $0.30 and one evening to establish, and the alternative was
building a pipeline on it first.

**Unspent option:** the clean-reference run (`run-ref2.mjs`) was written and
never executed — three reference sets including the kontext-pro frames, all
seal-free. It is one box-hour away if it is ever worth answering.

---

## 2026-08-12 — REFERENCES PICKED (the first approval in this lane)

Ryan picked these **here**, for this project. That is what makes them count —
not that three of them came out of bongpot. Copied to `references/`.

| file | what it is |
|---|---|
| `s05-SCENE-uso-inkwash-v1.png` | paisley-shirt man, clothes rack, breeze-block wall |
| `s06-FORESHADOW-uso-inkwash-v1.png` | the teal gravel pile inside a shipping container |
| `s37-INSERT-uso-inkwash-v1.png` | insert shot |
| `seedream-5-pro.png` | Ryan's own portrait, black ink — hosted seedream-5-pro, today |

> "I love this whole set. It was so quirky and unique. Really, really love this."

### THE MODEL BEHIND THAT SET — `uso-inkwash`

Ryan asked for this to be noted. Every frame in `keyframes-v10` is named
`*-uso-inkwash-v1.png`, and the recipe is bongpot's
`supabase/functions/_shared/creative.js` STYLE_RECIPES entry:

```
provider      comfy (ComfyUI on a rented box — NOT a hosted API)
checkpoint    flux1-dev-fp8.safetensors
lora          uso-flux1-dit-lora-v1.safetensors  @ 1.0
              (media-tools' style.json later raised this to 1.35 for a
               different job — keyframes-v10 was rendered at 1.0 on 2026-06-10)
model patch   uso-flux1-projector-v1.safetensors
clip vision   sigclip_vision_patch14_384.safetensors
dims          1152 x 640  (16:9)
guidance      3.5 · steps 20 · euler/simple · cfg 1.0 · denoise 1.0
```

Three channels, which is the whole trick:

- **style** — a face-free texture swatch → `CLIPVisionEncode` → `USOStyleReference`.
  Patches the MODEL, so the medium is swappable without touching anything else.
- **identity** — a photoreal plate → `VAEEncode` → `ReferenceLatent` →
  `FluxKontextMultiReferenceLatentMethod`. Rides the CONDITIONING.
- **content** — short text, nothing about the medium.

Graph builder already in this repo: `tools/_uso.mjs` (`buildUsoGraph`).

**Why this matters now:** the look Ryan loves was never produced by a style
LoRA. It came from a **reference IMAGE in a dedicated style channel** — which is
the same mechanism as Krea's style-reference route, and the opposite of the
published-LoRA route he just rejected. His instinct that "reference image + LoRA
might be the ticket" points straight back at this architecture.

---

## 2026-08-12 — the published ink LoRAs RUN BARE: REJECTED

> "I actually don't really like these Lora's."
> — clarified: *"I don't like the Lora's raw. Without giving it any reference
>   style of my own."*

**Scope of this rejection: LoRA ALONE.** Not LoRA in combination with a style
reference. The 24-render swath gave the LoRAs no reference channel at all —
they were driven by trigger phrase and text only — so what was rejected is the
published-style-on-its-own route, not the LoRA as a component.

That distinction matters because the look Ryan does love (`keyframes-v10`) came
from a reference image in a style channel, with a LoRA in the model chain. Both
parts, together. See the recipe note below.

**Rejected:** `krea/Krea-2-LoRA-darkbrush`, `ilkerzgi/krea-2-chinese-ink-linen-scroll-lora`

Evidence: `renders/all.png`, 24 images, 6 subjects × 2 LoRAs × turbo/raw, seed
20260812, LoRA strength 0.8, turbo at 8 steps (Krea's own template settings).

### What the run established anyway

These are mechanical findings, still true regardless of the aesthetic verdict:

- **The stack works.** Krea-2 on a rented 5090, 24/24 renders, ~13s each at
  1024². Graph is `tools/_krea.mjs`, built from Krea's official ComfyUI
  template, every input name confirmed against the live server.
- **darkbrush holds across subject types** — two faces, wide landscape, dim
  interior, animal, macro, suburban garden. It did not break on any of them,
  and it did not make a laundry room look heroic. Technically sound; Ryan just
  doesn't want it.
- **linen scroll was under-driven at 0.8** and came back nearly photographic.
  Its card specifies 1.0–1.25; I used Krea's template default for both. If it is
  ever revisited, that is the fix — but Ryan has seen it and said no.
- **raw does not work for inference with turbo-trained LoRAs.** Washed out and
  muddy on both. Consistent with raw being the control/LoRA-training substrate
  rather than a quality tier.

### What it rules out

The published-LoRA shortcut. Somebody else's trained style is somebody else's
style, and the odds of it being the one in Ryan's head were never good.

### Untested routes that do NOT require guessing his taste

1. **Local style-reference images.** ComfyUI ships
   `image_krea2_turbo_int8_image_style_reference.json` — the same channel that
   worked on Replicate, self-hosted. Needs reference images Ryan picks.
   (`api_krea2_style_reference.json` is NOT this — it uses `Krea2ImageNode`,
   which calls Krea's paid cloud, not the box.)
2. **Two untested first-party LoRAs** already in `Comfy-Org/Krea-2/loras/`:
   `krea2_softwatercolor.safetensors` and `krea2_style_reference.safetensors`.
3. **Train a LoRA on this lane's own approvals.** `krea2_raw_fp8_scaled` is
   already on the box for exactly this. Blocked until something is approved.

All three are blocked on the same input: **images Ryan likes.** Not inherited,
not guessed.
