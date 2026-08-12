# Training an ink-wash LoRA on LTX-2.5

Research report — 2026-08-12. Nothing here has been run. No GPU was rented.

**Question asked:** can LTX-2.5 be customised to the ink-wash style, and how.

**Short answer:** yes, and it is a first-class supported path, not a hack.
Lightricks ships the trainer themselves and documents style LoRAs explicitly.
The blocker is not tooling and not GPU access — it is that we do not have a
dataset, and the vendor's own sizing guidance says the dataset needs to be
about 20x bigger and far more varied than what we have.

---

## Verification status

| Claim | Status | Source |
|---|---|---|
| Official trainer ships with LTX-2, supports LoRA / full-finetune / IC-LoRA | VERIFIED | `Lightricks/LTX-2` README, `packages/ltx-trainer/` |
| Trainer supports LTX-2.5 | VERIFIED | LTX-2 README ("LoRA functionality is supported for LTX-2.5") |
| Image-only datasets supported (frame count 1) | VERIFIED | `docs/dataset-preparation.md` — "supports videos, single images, or a mix of both" |
| Broad style LoRA needs "low hundreds" of clips | VERIFIED | ltx.io "Build the dataset" chapter |
| i2v is the recommended default for a style LoRA | VERIFIED | ltx.io "Decide what to train" |
| Rank 32–64 for a style | VERIFIED | ltx.io "Set up the training run" |
| 80GB+ VRAM for the standard config; 32GB via low-vram config w/ INT8 | VERIFIED | `packages/ltx-trainer/README.md` |
| Wall-clock / cost of an actual run on our hardware | **UNMEASURED** | third-party blog cites 3–5h on a 4090 for LTX-2.3, mid-size dataset. Not ours, not 2.5. Treat as unknown until measured. |
| LTX-2.5 IC-LoRA catalogue | THIN — only `LTX-2.5-22b-IC-LoRA-Pixel-Spatial-Upscaler` published so far | HuggingFace org listing |

---

## What the trainer actually is

`Lightricks/LTX-2` → `packages/ltx-trainer/`. Two scripts:

```bash
# 1. encode clips + captions into cached latents (one pass per bucket set)
uv run python scripts/process_dataset.py dataset.json \
    --resolution-buckets "1280x704x1" \
    --model-path /path/to/ltx-2.5-22b.safetensors \
    --text-encoder-path /path/to/gemma-root \
    --lora-trigger "INKWSH" \
    --decode          # writes the cropped/resized frames so you can eyeball them

# 2. train
uv run python scripts/train.py configs/i2v_lora.yaml
```

Dataset is a JSON/CSV/JSONL list. Images go in the `video` column:

```json
[
  { "caption": "INKWSH ...", "video": "stills/shot-03.png" }
]
```

Preprocessing writes `dataset/.precomputed/{latents,conditions,...}`; training
writes `checkpoints/lora_weights_step_*.safetensors`, which loads in ComfyUI as
an ordinary LoRA. Nothing exotic.

### Shipped configs

`a2a_ic_lora · a2v_lora · audio_extend_lora · audio_inpainting_lora ·
audio_suffix_lora · av2av_ic_lora · i2v_lora · t2a_lora · t2v_lora ·
t2v_lora_low_vram · v2a_lora · v2v_ic_lora · video_extend_lora ·
video_inpainting_lora · video_outpainting_lora · video_suffix_lora`

Note there is **no `i2v_lora_low_vram.yaml`** — if we end up on a 32GB card the
`acceleration:` block from `t2v_lora_low_vram.yaml` has to be ported into
`i2v_lora.yaml` by hand.

### Defaults (from `configs/t2v_lora.yaml`, verbatim)

```yaml
lora:
  rank: 32
  alpha: 32
  dropout: 0.0
  target_modules: ["to_k", "to_q", "to_v", "to_out.0"]
optimization:
  learning_rate: 1e-4
  steps: 2000
  batch_size: 1
  enable_gradient_checkpointing: true
acceleration:
  mixed_precision_mode: "bf16"
checkpoints:
  interval: 250
  keep_last_n: -1        # set this; the default discards early checkpoints
```

---

## What the vendor says about style LoRAs specifically

Five things from the official guide that change what we do:

1. **Mode: use `i2v_lora.yaml`, not t2v.** i2v training uses each clip's first
   frame as an occasional guide (a probability, not every step). The resulting
   LoRA works *either way* at inference — from a prompt or from a start image.
   That is exactly our pipeline (USO still → i2v), so it is the safe default.

2. **Dataset size: a broad visual style needs "into the low hundreds."**
   Narrow one-shot effect = 25–50. Simple motion = ~50. Broad style = low
   hundreds. Earlier this session I put the number at ~50 for our case; that is
   too low by the vendor's own guidance.

3. **Vary everything that is not the style.** Their warning verbatim: if every
   clip has the character in the same kitchen, "the LoRA will quietly learn the
   kitchen as well as the character." Vary settings, shot distance and angle so
   the only constant the model can latch onto is the brushwork itself. Isolate
   on white, never black.

4. **Rank 32–64 for a style, alpha = rank.** Attention-only `target_modules`
   is enough for a style; the feed-forward layers only need adding when an
   *identity* has to hold. We explicitly do not care about identity here, so
   the shipped defaults are correct as-is.

5. **Captions are where most of the quality comes from.** Dense and concrete.
   Describe the constant (the medium) with the *same phrases every time*, and
   the variable (subject, setting, action) differently every time. That
   contrast is how the model learns what it is allowed to change.

**Trigger word:** pass `--lora-trigger` once at preprocessing and it is
prepended to every caption automatically. Pick a made-up token the base model
has no priors about. `"ink wash"` and `"watercolor"` are exactly the wrong
choice — LTX already has strong associations there and the LoRA will fight
them. `INKWSH` or similar.

---

## Sequence-length budget

Cost per clip = `(W/32) × (H/32) × ((F-1)/8 + 1)`. Aim ~8,000, hard ceiling
15,000; past that "previews turn to mush and the run stops learning."

| Bucket | Seq len | Note |
|---|---|---|
| `1280x704x1` | 880 | a still. Very cheap. |
| `960x544x1` | 510 | cheaper still. |
| `1280x704x33` | 4,400 | ~1.3s of video |
| `960x544x121` | 8,160 | 5s — the motion bucket |
| `1280x704x81` | 9,680 | their stated healthy default |

Constraints: `frames % 8 == 1` (1, 9, 17, 25 … 121), width and height each a
multiple of 32.

---

## The plan that follows

### Phase A — stills-only style LoRA (no video corpus required)

This is the one worth doing, and it is not GPU-blocked in any expensive way.

The failure we actually saw on 2026-08-12 was an *appearance* failure: Hunyuan
propagated the existing painted pixels faithfully for all 5 seconds, and only
the **newly-synthesized** smoke came out CG. A stills-trained style LoRA
teaches appearance. That is the right instrument for the observed defect.

1. **Build the corpus with the tool we already have.** `generate-image
   --provider comfy --style inkwash` at 40 s/still, measured. 200 stills ≈
   2.2 GPU-hours ≈ **under $2 of render** on a 24GB card. The corpus is the
   deliverable, not the shots.
   - 200 prompts spanning wildly different content: landscapes, single objects,
     interiors, crowds, animals, machinery, hands, weather. Close-ups through
     wides. The Sheen shots are 9 frames of one man in one wardrobe — that is a
     *counter-example* of a style dataset, not a seed for one.
   - Cull hard. Anything with a photoreal face or an airbrushed gradient in it
     teaches the model to make those.
   - Hold back 3–5 to test generalisation after training.
2. **Caption them.** Constant phrasing for the medium, varying phrasing for
   content. Trigger `INKWSH` prepended by the preprocessor.
3. **Preprocess** at `1280x704x1` with `--decode` and look at the decoded PNGs
   before spending a training hour.
4. **Train** `i2v_lora.yaml`, rank 64, alpha 64, `keep_last_n: -1`. Judge by
   validation samples, not the loss curve. Stop when samples stop improving.
5. **Test on the held-back prompts.** If it only reproduces what it trained on,
   the dataset lacked variety — fix the data, not the hyperparameters.

**Known limit of Phase A:** stills cannot teach how ink *behaves over time* —
bleed, bloom, brush drag, paper absorption. It teaches what a frame looks like.
If motion still reads wrong after Phase A, that is Phase B.

### Phase B — motion, only if Phase A leaves motion broken

Needs real ink-wash animation footage cut to ~5s single-action clips, which we
do not have and would have to source. Mixed run: `--resolution-buckets
"960x544x1;1280x704x81"` with `batch_size: 1`. Defer.

### Phase C — IC-LoRA, not now

Style transfer *is* explicitly listed as an IC-LoRA-trainable
reference-to-target transformation, and IC-LoRAs stack with concept LoRAs. But
sizing is several hundred paired clips minimum, and Lightricks' own
scene-conditioning IC-LoRA took ~2,000 pairs at rank 128. Out of proportion to
the problem.

---

## What this does not solve

FLF2V and a populated negative prompt remain the per-clip locks and are free
today. The LoRA is the permanent lock. They compose; neither replaces the other.

## Open questions requiring a rented box

- Training throughput and therefore cost per LoRA on an 80GB card — unmeasured,
  goes in `tools/benchmarks.json` once measured.
- Whether LTX-2.5 at bf16 plus the Gemma text encoder plus training state fits
  an 80GB card at all, or wants a B200's 180GB.

## Sources

- https://github.com/Lightricks/LTX-2
- https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-trainer/README.md
- https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-trainer/docs/dataset-preparation.md
- https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-trainer/docs/training-guide.md
- https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-trainer/docs/training-modes.md
- https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-trainer/configs/t2v_lora.yaml
- https://ltx.io/blog/when-to-train-a-lora (6-chapter series; all chapters read)
