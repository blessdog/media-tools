# STATUS — media-tools

## 2026-08-12 — PHASE 5 DONE: the real renderer is wired and proven

`generate-image --provider comfy` runs the USO graph on a Vast box. Nine
inkwash frames rendered from `jobs/sheen-inkwash/regen/*.txt` through
`uso-inkwash` — the 2026-06-09 renderer, not an approximation of it.
Contact sheet: `jobs/sheen-inkwash/renders/contact-sheet.png`.

What the live run settled:

- **The gist risk is closed.** The pinned URL in `gpu-box.mjs` is byte-identical
  to `tools/provision/provision-ltx.sh` and carries the USO block.
- **`.vast/ssh_key.pub` never came across in the salvage.** It now holds
  `~/.ssh/id_ed25519.pub` (matching `SSH_KEY` at `gpu-box.mjs:318`). Without it
  `forward` cannot open the tunnel.
- **Provisioning pulls LTX's 29GB checkpoint BEFORE the USO block**, so a
  stills-only job pays ~30 min for weights it never loads. Pulling the four USO
  files directly in parallel (same paths, so the provisioner skips them) had the
  box rendering in ~12 min instead. A `--stills-only` provisioning path is the
  obvious next economy.
- **Routing degrades, it does not fail.** No box → hosted fallback with a
  warning; `--provider comfy` explicitly → exit 3 naming the box command.
- Box `47503264` is **STOPPED, not destroyed** — storage-only ~$0.033/hr, weights
  retained, `gpu-box start` resumes in ~1-2 min. **`gpu-box down` when the look
  is settled**, or it keeps trickling.

Open: **the identity channel has never been exercised.** Every frame so far is
style + text, so the men are generic. `--plate-image` is wired and untested, and
nothing yet extracts a photoreal plate from source footage.

## 2026-08-11 — phases 1–4 shipped

Read `CLAUDE.md` (the tool contract) and `docs/specs/2026-08-11-media-tools-design.md`
(especially **§12 Amendments**, written after live testing contradicted the
original spec). The plan is `docs/plans/2026-08-11-media-tools-implementation.md`.

### What exists and works

Nine tools in `tools/`, all run from any directory by absolute path, all with
`--help`:

| tool | proven on |
|---|---|
| `generate-image.mjs` | live render, foreign cwd, style resolved from `styles/` |
| `restyle-image.mjs` | two of Ryan's photos + a Sheen frame |
| `image-to-video.mjs` | salvaged, `--help` only — NOT yet run live |
| `restyle-video.mjs` | 10s Sheen slice via luma, first_frame anchored |
| `transcribe.mjs` | ran clean; returned 0 words because the clip has no speech |
| `describe-video.mjs` | 9 shots off a 43s clip, black frames dropped |
| `stitch.mjs` | 3 real clips, 1920x1088@24 → 1920x1080@30, 15.12s |
| `stylize-frames.py` | salvaged, syntax-checked — NOT yet run live |
| `gpu-box.mjs` | live `status` against the Vast API ($0, 0 instances) |

`cutwork` is cut over: its copies deleted, imports re-pointed to absolute
toolbox paths, `node --check` clean. `clipsmith` → `mediaStudio/archive-clipsmith`
after salvaging `stitch` and the LTX workflow. `SKILL.md` is symlinked into
`~/.claude/skills/media-tools` and loads in fresh sessions. Bible gained §5.7
(agent-facing tool surfaces) and §5.8 (creative direction is an asset).

### PHASE 5 — wire the real renderer

**The goal:** `generate-image --provider comfy` running the `uso-inkwash` graph,
because that is the look Ryan actually approved (2026-06-09) and everything
hosted so far is an approximation of it.

Everything needed exists separately and is NOT yet connected:

- `tools/_uso.mjs` — `buildUsoGraph({ plateImage, swatchImage, prompt, seed, lora,
  guidance, width, height, steps, prefix, ckpt })` returns the ComfyUI graph.
- `tools/_comfy.mjs` — `uploadInput`, `runWorkflow`, `fetchOutput`, `runToFile`.
- `tools/gpu-box.mjs` — `up --rent`, `wait`, `forward --port 8189`, `down`.
- `tools/provision/provision-ltx.sh:131-137` — installs the whole USO stack
  (flux1-dev-fp8, uso-flux1-dit-lora-v1, uso-flux1-projector-v1,
  sigclip_vision_patch14_384).
- `styles/inkwash/style.json` `.renderer` — the recipe; `.channels` — the map.
- `styles/inkwash/reference/LOCKED-inkwash-texture-1.png` — the style channel.
  **LOCKED. Never regenerate.**

**Steps:**
1. `generate-image` reads `style.renderer.provider`; when `comfy`, upload the
   swatch (+ optional identity plate) via `_comfy.uploadInput`, build with
   `buildUsoGraph`, run against `http://127.0.0.1:8189`, write the output.
   Keep the Replicate path as the fallback when no box is up.
2. Box up: `node tools/gpu-box.mjs up --rent` → `wait` → `forward --port 8189`.
3. Render the Sheen shots, `open` every result, Ryan's eyes decide.
4. `node tools/gpu-box.mjs down` — **billing only stops when the box is
   DESTROYED.** Confirm `status` shows 0 instances.

**RISK, unverified:** `gpu-box.mjs:118` pulls provisioning from a **pinned gist
URL**, not from `tools/provision/`. If that gist predates the USO block, the
models will not land on the box and the graph will fail on missing checkpoints.
Check the gist contents (or re-gist `tools/provision/provision-ltx.sh` and update
the URL) BEFORE spending box time.

**Open, smaller:** identity for the Sheen shots needs a photoreal plate built
from his face — `generate-image --plate` makes plates, but nothing yet extracts
one from source footage.

### The live job

`jobs/sheen-inkwash/` (gitignored — scratch):
`source.mp4` (43s Parliament cigarette ad, 854x480, Russian TV rip, Cyrillic
watermark in one shot, music not dialogue), `slice.mp4` (10s test),
`shots.json` (9 described shots), `regen/shot-NN.txt` (9 editable prompts),
plus earlier hosted-render candidates.

### Standing rules learned here

- **`open` every file you produce, in the same command that makes it.**
  Rendering an image into the assistant's context does not put it on Ryan's
  screen. He had to say this four times in one session.
- **`node --check` is not a smoke test** — it passed a file with an undefined
  variable. Run the tool.
- **Test on real media, never fixtures.** Every gap found today (missing tools,
  the wrong style string, black frames, 1088-tall clips) came from real files.
- **NO nano-banana for inkwash** — `style.json.rejected` records why.
