# Ink-wash in motion — where this actually stands

2026-08-12. Written at the end of a long session. Read this first next time.

---

## The one thing that worked

**A wet ink splatter becomes a finished painting on screen, and the style holds
the whole way.**

`jobs/inkwash-flf2v/clips/A-ink-becomes-painting.mp4` — LTX 2.5 Pro, 6s, 720p.
First frame is a real ink splatter; last frame is an approved inkwash still. The
splat blooms, the man resolves out of the ink mass — glasses and cigarette
emerging from the black — and settles into the painting. No drift to photoreal,
paper grain present throughout, the blue washes arrive as washes.

That is Ryan's "between the paper and the painting" idea, working, on the first
attempt, at default settings.

**The mechanism is one API field.** `last_frame_uri` on LTX's image-to-video:
*"the video will interpolate between the first frame and this last frame."* Give
it ink and a picture, it paints one into the other.

---

## The finding that reframes the project

Across every clip rendered today — one on LTX 2.5, five on LTX 2.3, four of
which failed at what they were asked to do — **not one output drifted to
photoreal.** Every failure was *content* drift: the wrong man, invented reeds,
an unrelated scene. The medium held in all of them, start to finish.

**Style is solved. Control is the problem.**

That kills the plan this session started with. Training a style LoRA teaches a
model a look it already holds. The corpus work, the museum pull, all of it was
aimed at the wrong target.

---

## Verification status

| claim | status |
|---|---|
| FLF2V paints ink → picture, style holds | **PROVEN** — clip A, Ryan watched it |
| Style survives without a LoRA | **PROVEN** — 6 clips, 2 models, zero photoreal drift |
| LTX 2.3 is materially worse than 2.5 at this | **PROVEN** — 4 shots, 2 guide settings, all drifted |
| `frameGuideStrength: 1.0` fixes 2.3's drift | **DISPROVEN** — made it worse (went flat/graphic) |
| LTX 2.5 runnable on a rented box | **UNTESTED** — blocked, see below |
| Museum corpus is useful training data | **REJECTED by Ryan** — wrong look, wrong era |
| Monero prompt discipline transfers | **STRONG** — see "what to prompt" |

---

## THE BLOCKER — one click, only Ryan can do it

`Lightricks/LTX-2.5` on HuggingFace is **`gated: auto`**. Every file 403s until
the account owner accepts the terms. Auto-gating approves instantly; nobody has
to review it.

**https://huggingface.co/Lightricks/LTX-2.5 → "Agree and access repository"**

Verify it opened:

```
node ~/projects/media-tools/tools/preflight-models.mjs --repo Lightricks/LTX-2.5 \
  --path diffusion_models/ltx-2.5-22b-dev-transformer-bf16.safetensors \
  --path text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors \
  --path vae/ltx-2.5-video-vae-bf16.safetensors
```

Exit 0 = safe to rent. Exit 3 = still gated, **do not rent.**

LTX 2.3 and LTX 2 are **not** gated, which is why the existing provisioner works.

---

## What this cost, and the mistake that caused it

| | |
|---|---|
| LTX API | $0.72 — clip A. Exhausted the trial balance. |
| fal.ai | $0 — account already locked at zero |
| CivitAI | 27 blue + 178 green buzz, 5 clips. **9,222 green left** (~230 clips) |
| Vast H100 NVL | **$1.80 — wasted.** Destroyed without rendering a frame. |

**The mistake: I rented the box before checking whether the model could be
downloaded onto it.** One free HEAD request against the HuggingFace URL — token
in hand, path known — would have found the gate instantly. Instead it took a
$2.60/hr rental and forty minutes.

The rule, now enforced in code: **verify you can obtain the inputs before you
rent the compute.** `tools/preflight-models.mjs` exists solely to make this
failure impossible rather than merely remembered. It rents nothing, downloads
nothing, and exits 3 with the exact page to click.

Ryan's standing rule, restated because it was broken today: **a box that is not
computing must not be billing.** Preflight first, rent second, and destroy the
moment it stalls.

---

## What to prompt (this is the transferable part)

The single most valuable artifact found today is not a model — it's
`cutwork/footage/monero/video-plan.json`. Its ink prompts produce beautiful
results on an ordinary hosted model:

> "Black ink blooms outward into the paper fibres from the centre of the mark,
> the wet edge creeping and feathering into the grain, darkening as it spreads.
> **The paper stays still. Only the ink moves.**"

**The rule these encode:** the model has real physical priors for ink meeting
paper — capillary spread, wet edge, granulation, drying. When ink is the
**subject**, it uses them. When ink is only the **style of a depicted scene**,
it falls back on its photographic prior. Same model, opposite results.

This is also why Ryan's concept is technically sound and not just pretty: it
spends most of its screen time in the register the model is genuinely good at.

Corollary, learned the expensive way: **describe positively.** The bongpot
config that produced Ryan's favourite image ends "no red seal stamp, no Chinese
characters" — and the image has a red seal. Its plates carry seals too, painted
in by Qwen and copied forward by FLUX.2 through `input_images`.

**Killed by Ryan this session:** the "outside the painting" / brush-and-easel
shots. His words — "that's pure slop." The camera may go *into* the paper; it
never stands back and looks at the artist.

---

## Where everything is

```
media-tools/
  tools/preflight-models.mjs     NEW — run before every rental
  tools/_ltx.mjs                 api.ltx.io — has last_frame_uri (FLF2V)
  tools/_civitai.mjs             orchestrator — LTX 2.3 22b-dev, buzz
  tools/image-to-video.mjs       4 routes: comfy | ltx | civitai | replicate
  tools/provision/pull-ltx25.sh  LTX 2.5 pull, .part-then-rename hardened
  tools/fetch-artwork.mjs        museum corpus fetcher — PARKED
  tools/crop-tiles.mjs           artwork -> training tiles — PARKED
  jobs/inkwash-flf2v/
    frames/    ink-start.png, painting-end.png (both 1152x640)
    clips/     A (2.5, THE GOOD ONE) · A2/A3/B/C/D (2.3, weak)
    run.sh     the four-shot battery
  corpus/inkwash/raw/            352 museum records — PARKED, not training data
  docs/research/2026-08-12-ltx-lora-training.md   the LoRA research (now moot)
```

`.env` gained `LTX_API_KEY` (exhausted). `CIVITAI_API_TOKEN` is the live one.

---

## Next session, in order

1. **Click the HuggingFace gate.** Nothing else can proceed.
2. **Preflight.** Exit 0 or stop.
3. **Rent, provision, pull, render — in one unbroken run.** The box must not sit
   idle between steps. `pull-ltx25.sh` runs alongside the normal provisioner and
   writes `.part` files, so an interrupted pull resumes instead of corrupting.
4. **Re-shoot A on the box**, then B (painting → ink, the way *out* of a scene)
   and D (scene → scene). Skip C; that was the killed concept.
5. **Then, and only then**, ask whether anything needs training. On today's
   evidence the answer is no — control is a conditioning and prompting problem,
   not a weights problem.

## Do not repeat

- Don't rent before preflight.
- Don't build a corpus for a look the model already produces.
- Don't read a config file's nouns as a description of its output — that is what
  sent this session into Song-dynasty museum archives for an afternoon.
- Don't quote a headline price for a `pro` render; the docs table is the truth,
  and the API's own error message is the final word.
