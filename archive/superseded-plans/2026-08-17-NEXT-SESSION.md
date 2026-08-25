> **ARCHIVED 2026-08-25, NOT DELETED — LAW #0.6.** A third document competing
> with `STATE.md` (generated) and `PLAN.md` (the SSOT) to say what is current.
> Its own header already said *"the section below is history"*.
>
> **What is dead in it:** the MASKED MOTION technique and its "working recipe
> (four runs to find it)". Masked displacement was superseded by cut-out cards —
> see `knowledge/foliage-motion.md` and the refuted
> `evidence-warp-blurs-lift-does-not.png`: warping blurs the brushwork, lifting
> a rigid card does not.
>
> **Why it is kept:** the 2026-08-17 depth-dot handoff records Ryan's approvals
> on `pick.html` (zero typing, click order = depth order) which are still the
> live design of the picker, and the measurement-discipline section is a clean
> statement of bible §4.7 applied to this job.

# Wang Meng — next session

> **READ `STATE.md` FIRST.** It is the always-current record of the whole
> project (capability chain, measured laws, where we are). This file keeps
> the masked-motion recipe and the 2026-08-17 handoff history.

## 2026-08-17: manual depth-dot pass DONE — labelling pass since COMPLETED
## (see STATE.md; the section below is history)

(Work happened in the wrong chat; state handed off here. Ryan's approvals
and instructions below are real — don't re-ask.)

- `pick.html` REDESIGNED and approved: zero typing, click order = depth
  order (1 = nearest → 20 = farthest), fixed warm→cool ramp, double-click
  returns a dot to the queue. Export schema unchanged for segment-points.py.
- `points.json` = Ryan's manual 20-dot pass (mode `manual-dots`, names
  empty). Old model pass backed up at `points-v1-model.json`; `points-v2.json`
  untouched.
- **Labelling pass still to do** (Claude fills name/window/why, merges
  same-plane dots, renders overlay for Ryan's eyes before segmentation).
  Ryan's instructions for it:
  1. His dots mostly follow the LEFT pathway. The **right-side hillside
     with trees growing out of its top and sides is unlabelled** — it
     genuinely starts around dot 5's plane and the mountain cuts back
     through dots 6–10's planes. Add points for it in that depth range
     (export depths ~15 down to ~10; sharing depth values is fine).
  2. **Tree size is the depth cue** for the unlabelled masses — Wang Meng
     paints trees near-constant real size, so rendered size ≈ distance.
- Top quarter of the scroll (y < ~0.24, the far peaks) has no manual dots;
  decide during labelling whether the flight needs them.

---

# Previous: the MASKED MOTION test

Read this first. Everything below was measured on 2026-08-13/14, not guessed.

## The one question this session answers

**Can motion be confined to a region?**

Mask a region (the waterfall), animate ONLY those pixels with the phenomenon
named in the prompt, composite back over a locked plate.

### Why this is the fork that matters

Ryan's original brief was *"moving waterfalls and the trees gently blowing in
the breeze."* We then proved you **cannot ask for those**:

> Naming any physical substance in a motion prompt — water, mist, leaves — is a
> request for FOOTAGE of that substance, because that is what dominates the
> model's training. At cfg 6 the words overpowered the conditioning image and
> the painting was replaced by a photographic waterfall in ~2 seconds.

So the two things he most wants are the two things the prompt channel cannot
deliver. Masking is the way out: inside a crop containing only water, the word
"water" is safe, because Ge Hong is not in the frame to be dissolved.

- **If it works:** the grammar opens up — locked shot with running water, slow
  push with stirring trees, figures moving while the landscape holds.
- **If it fails:** every shot is a still painting with a camera move over it,
  and the "living world" half of the brief needs different technology.

## The working recipe (four runs to find it — do not re-derive)

| | value |
|---|---|
| model | HunyuanVideo 1.5 I2V 720p fp16, ComfyUI native nodes |
| positive | **camera only.** `"the camera pushes slowly and steadily forward, a smooth dolly move deeper into the scene. nothing else changes."` |
| negative | `photograph, photorealistic, real water, video footage, live action, cinematic lighting, film grain, 3d render, depth of field, motion blur, morphing, texture dissolving` |
| cfg | **2–3.** cfg 6 lets the text overrule the painting. This is the volume knob. |
| frames | 73 (3s @ 24fps) proven. Longer is UNTESTED — the one 5s run is confounded with the bad prompt. |

For the masked test the positive prompt is the ONE place this changes: inside
the mask you may name the substance, because nothing else is in frame.

## Infrastructure that already exists

- `tools/gpu-box.mjs --hunyuan --min-vram 78` → rents + provisions in one go.
  Use an **80GB** card; benchmarks.json says 53GB floor, and `--min-vram` exists
  because gpu-box would otherwise rent the 40GB variant of `A100_SXM4`.
  Measured A100 SXM4 80GB: 67 s/step, 121f @ 720×1280, 31.7/80GB, no offload.
- Tunnel: `ssh -L 8189:localhost:8188 -p <port> root@<host>`, then
  `node tools/image-to-video.mjs --provider comfy` (8189 is its default).
- `node tools/gpu-box.mjs down --id <id>` the moment it is finished.

## Assets ready to use

- `motion/shot-real.png` — 720×1280 from the real master: Ge Hong, bridge,
  deer, pine, cliff, stream. Has a small waterfall under the bridge, left side.
- `motion/shot-gen.png` — 720×1280 from the generated 高遠 still.
- `gate-a/vert1-canvas.png`, `vert2-both.png` — generated 高遠 stills.
- `motion/push-real.mp4` — THE FAILURE. Worth rewatching.
- `motion/push-real-fix1.mp4`, `-fix3.mp4` — the good ones.
- `motion/still-control-fix4.mp4` — static control.

## Measurement discipline (bible §4.7 — this bit is not optional)

Two parallax claims died to controls this session. Before believing any number
about a rendered result, **build the null**:

- `motion/silk-survival.py` — per-frame % of the frame still in the painting's
  own tonal band, calibrated from frame 0. Failure 19.5%, fix1 67.8%,
  static control 89.4%. **The control's 11% loss is the drift floor** — always
  quote a result against it, never against 100%.
- `motion/flow-residual.py` — fits scale+translation out of the optical flow.
  Needs a NULL to be meaningful; `make-zoom-ref.py` builds a synthetic flat zoom.
- Still missing: a **positive** control. Render the 18-plane stack through
  `render-parallax.py` on a known camera path to calibrate what real depth
  scores. Until then, do not claim parallax.

## Suggested first three runs

1. Crop a tight box around the waterfall under the bridge in `shot-real.png`.
   Animate with the substance named (`"water falls and flows downward"`), cfg 3,
   73 frames. Does the ink survive when water is the *only* thing in frame?
2. Composite that clip back over the locked full plate. Does the seam read?
3. Same on foliage — the pine at frame right — with `"leaves stir in a breeze"`.

Kill the box, then report with pictures, not prose.
