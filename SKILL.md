---
name: media-tools
description: Use when creating, transcribing, describing, styling, animating, or assembling any image, video, or audio media — image generation, photo/video restyling, image-to-video, transcription, shot-by-shot video description, clip stitching, Vast GPU rental. One CLI per capability; compose them in scripts.
---

# media-tools — the toolbox

One repo of single-purpose media CLIs at `~/projects/media-tools/tools/`.
Invoke by absolute path from any directory.

**Rules.** Nothing runs implicitly — a tool that needs a transcript takes
`--transcript`, it never transcribes for you. Styles resolve from
`styles/<key>/style.json` via `--style`. Every tool's `--help` is its
authoritative contract; read it before calling. Compose tools in a job script
(`jobs/<name>/run.sh`), one line per step, so the human can read and re-run it.

**Never ship slop.** Cheap+fast diffusion is not a shortcut to a result, it is a
different and worthless result — Ryan can see it instantly. Anything he will look
at gets the best renderer available from the first frame, even if that means
renting a GPU box and waiting. Never fall back to a cheap hosted model silently;
say the good path is down and stop. See CLAUDE.md.

**Always `open` what you produce.** Rendering an image or video into the
assistant's own context does NOT put it on Ryan's screen. Run `open <path>` in
the same command that creates the file.

## Catalog

| tool | one job |
|---|---|
| `generate-image.mjs` | scene text + style → image |
| `restyle-image.mjs` | existing image + style → repainted image, composition kept |
| `image-to-video.mjs` | still + motion prompt → clip (seedance-1-lite default) |
| `restyle-video.mjs` | clip + style → restyled clip (luma default; wan/kling/aleph) |
| `stylize-frames.py` | clip → deterministic styled frames (Blender; `blender -b -P`) |
| `transcribe.mjs` | audio/video → diarized transcript.json (Deepgram nova-3, ALWAYS Deepgram) |
| `describe-video.mjs` | video → shot-by-shot written script (vision via OpenRouter) |
| `stitch.mjs` | clip-list file (+ music) → one normalized video (ffmpeg, no API) |
| `shard-models.mjs` | one image → N renderers on N boxes in parallel (the bake-off) |
| `gpu-box.mjs` | rent / provision / kill a Vast.ai GPU box |
| `plan-gpu.mjs` | workload → which card to rent, ranked by cost PER JOB (rents nothing) |
| `fetch-artwork.mjs` | open-access museum collection → images + metadata sidecars |
| `fetch-image.mjs` | one image (URL or local file) → library + provenance sidecar |
| `find-page-image.mjs` | web page → the images in it, ranked (downloads nothing) |
| `estimate-depth.py` | image → depth map (works on PHOTOS; fails on ink painting — see its docs) |
| `segment-regions.py` | image → non-overlapping regions, auto (objects, never big planes) |
| `segment-points.py` | clicked points + depths → cut RGBA depth planes |
| `crop-tiles.mjs` | artwork scans → square training tiles, mount silk and blank paper removed |
| `mask-bare-ground.py` | box → mask of the UNPAINTED ground (留白), cut by material not contour |
| `animate-strokes.py` | still + mask → looping clip; the painter's own ink displaced, never redrawn |
| `composite-shot.py` | still plate + N animated regions → one shot; everything else stays frozen |
| `walk-figure.py` | clean plate + figure mask → a cut-out walk cycle + a pan bar + hinged limbs |
| `clean-plate.py` | still + mask → the masked thing removed by patch synthesis, texture intact |
| `cut-stroke.py` | stated paths + image → one mask per painted STROKE (a limb, branch, rope, rail) |
| `locate-crop.py` | a crop + the image it came from → crop.json, the transform everything else reads |
| `crop-region.py` | big image + crop.json → a working region, the mask offset recorded |
| `compose-depth.py` | labelled planes (+ per-object relief) → one depth map |
| `probe-parallax.py` | image + depth → does this move carry depth? measures against a built-in null |
| `probe-zoom.py` | rendered frames → is this move a ZOOM or a FLIGHT? fits one global scale and reports the leftover, against a flat-still control |
| `probe-planes.py` | plane stack → is it OBJECT-COMPLETE? finds painted things straddling two depths |
| `contact-sheet.py` | N rendered loops → ONE tiled sheet with labels; the human gives one verdict instead of N |
| `complete-planes.py` | plane stack with gaps → every pixel claimed, by nearest-plane proximity |
| `inpaint-planes.py` | plane stack → each plane painted on BEHIND its occluders, so a dolly opens no holes |
| `pin-objects.py` | plane stack + object masks → no painted object straddles two depths |
| `render-warp.py` | objects + depths + camera path → frames, as ONE continuous warp; rigid objects, strain in the wash, no holes, NO occlusion |
| `render-living.py` | master + per-region animation cycles + camera path → frames; 2D Ken Burns window over a LIVING painting (cycles composited per frame, cost O(window)) |

Internals (not tools): `_env` `_replicate` `_comfy` `_fleet` `_uso` `_hunyuan`.
Proven ComfyUI graphs in `tools/workflows/`. Renderer recipes in `models/` —
one JSON per model, read by `shard-models`; never in tool code.
**`models/` is mostly MANIFESTS, not renderers — 1 of 8 can currently render
(`uso-inkwash`). Read `models/README.md` and run its check before planning
around any model.** A memory of having run something once is not a capability.
Related standalone tool: `rectum` (URL → clip on disk) at
`~/projects/mediaStudio/rectum/`, its own CLI.

## Reach for this when

The catalog says what each tool DOES. This says which one a problem wants —
agents arrive with a situation, not a capability.

**Before choosing, run `tools/find-technique.py "<the situation in your own
words>"`.** It prints the top-3 live procedures from `knowledge/` with each
one's nearest confusable sibling and the already-refuted list. This table is a
human summary; the store is the source of truth, it is type-checked, and it
holds at most ONE live entry per problem. Do not stop at the first row that
matches a keyword — that is exactly how 2026-08-20 happened.

| the situation | the route |
|---|---|
| "which of these candidates is right?" — a parameter sweep, two rigs, an effect vs its null | `contact-sheet.py --cells ... --focus motion` — render every candidate FIRST, then tile them into one sheet and ask once. Showing them one at a time is how 2026-08-21 rendered eight canopy variants and put two on screen. Two candidates only, and wanting them full size? `ab-cycle.py` |
| "the water should move" — ripples, a fall, a surface | `animate-strokes` — displaces the painter's own ink in place, and it loops. Never a video model |
| "the leaves should stir" / "a limb, branch, rope or rail should swing" | `cut-stroke` → `clean-plate` → a hinge rig (`walk-figure --limbs` is the proven one). NOT `animate-strokes` — see the test below |
| **the test that splits those two rows** | Does the thing UNCOVER GROUND when it moves, or does it have STRUCTURE THAT MUST STAY PUT? Either yes → cut-out card on a pivot. A displacement field cannot hold a trunk still while its leaves move, and it has no real background to reveal — `animate-strokes` fills holes with `cv2.INPAINT_TELEA`, the averaging inpainter `clean-plate` exists to replace. Both yeses were true of foliage and it took a human to notice (2026-08-20) |
| "a figure should cross the frame" | `crop-region` → `clean-plate` → `walk-figure --window/--pan` |
| "the figure moved and left a hole" | `clean-plate` (and the plate must lose the WHOLE thing that moves) |
| "where did this crop come from?" | `locate-crop` → crop.json, then every tool reads it |
| "the seams/cards still show, or I never want a hole" | `render-warp` — one continuous sheet instead of layers. Trade: it cannot occlude, so nothing passes behind anything |
| "I want to fly into the picture" | `render-parallax --plane-fit --z-step 0.15`. WITHOUT `--plane-fit` a dolly is a zoom — see below |
| "an object shears / is cut in half by the camera move" | `segment-regions` for objects, then `pin-objects`. An object across two depths is magnified at two rates |
| "the camera move opens holes / white gaps" | `inpaint-planes` — fill in LAYER space once, never per frame. Frame 0 must stay byte-identical |
| "the camera move is deforming the painting" | `probe-planes` first. An object split across two depths is magnified at two rates at once; `complete-planes` seals the gaps |
| "the push looks like a zoom, not a flight" | `--plane-fit`. One global focal makes depth separation resize the planes, so z-step gets throttled to keep the composition and the parallax budget collapses (measured: 6.8%) |
| "does this camera move actually carry depth?" | `probe-zoom --control` for a rendered move, `probe-parallax --null` for a depth map. Never quote a number without the control |
| "which GPU, and is it worth renting?" | `plan-gpu` (rents nothing) → `gpu-box` |
| "animate a painting" — the whole job | read `kits/painting-animation/SKILL.md` before anything |

## Naming conventions

The verb states the job, so an unfamiliar tool is guessable from its name alone.

| verb | produces | e.g. |
|---|---|---|
| `fetch-` `find-` | source material | `fetch-artwork`, `find-page-image` |
| `crop-` | a subset of an image | `crop-region`, `crop-tiles` |
| `segment-` `mask-` `cut-` | masks | `segment-points`, `mask-bare-ground`, `cut-stroke` |
| `estimate-` `locate-` `plan-` | information, no pixels | `estimate-depth`, `locate-crop`, `plan-gpu` |
| `generate-` `restyle-` `compose-` | new pixels | `generate-image`, `compose-depth` |
| `animate-` `walk-` | motion | `animate-strokes`, `walk-figure` |
| `render-` `composite-` `stitch-` | the deliverable | `render-parallax`, `stitch` |
| `complete-` `pin-` | makes an existing artifact whole / consistent | `complete-planes`, `pin-objects` |
| `probe-` | **a measurement that can only falsify** | `probe-parallax`, `probe-zoom`, `probe-planes` |

`probe-` is its own class on purpose. Those tools never produce a deliverable —
they exist to kill a claim before it reaches the screen, which is this repo's
whole discipline. If you find yourself quoting a number a `probe-` tool produced
without also quoting its null, you have not measured anything.

## Kits

A kit is the golden path through the toolbox for one class of job: the ordered
procedure, the decision points, and the measured dead ends. Tools stay general
and reusable; the kit is where domain knowledge lives; `jobs/<name>/painting.json`
holds what is true of one instance only.

| kit | for |
|---|---|
| `kits/painting-animation/` | making a still painting move — camera, water, foliage, walking figures |

## Styles

`styles/<key>/style.json` is a **renderer recipe**, not a prompt string. Read it
before rendering — it names the winning renderer, the channel map, the locked
reference assets, a hosted fallback, and **models explicitly rejected for that
look**. Honour the `rejected` block.

`inkwash` — the approved renderer is `uso-inkwash`: USO dual-channel on ComfyUI
on a Vast box, three separate channels (face-free style swatch through CLIPVision
sigclip / photoreal identity plate on a ReferenceLatent / content-only text).
`reference/LOCKED-inkwash-texture-1.png` is LOCKED — never regenerate it.
`google/nano-banana-pro` is REJECTED for this look; it was only ever a
character-drift test.

## Composition examples

Footage with no dialogue → a script you can direct from:

    T=~/projects/media-tools/tools
    node $T/describe-video.mjs --video source.mp4 --out shots.json --threshold 0.15 --every 4

Regenerate from that script (the description is the CONTENT channel; the style
supplies the LOOK). With a box up this runs the real USO renderer; without one
it degrades to the hosted fallback and says so:

    node $T/gpu-box.mjs up --rent && node $T/gpu-box.mjs forward --port 8189 &
    node $T/generate-image.mjs --style inkwash --provider comfy \
      --prompt "$(cat regen/shot-02.txt)" --out regen/shot-02.png
    open regen/shot-02.png
    node $T/gpu-box.mjs stop      # GPU billing off, weights kept (~$0.03/hr)
    node $T/gpu-box.mjs down      # DESTROY — the only thing that stops billing entirely

Restyle a real photo, composition preserved:

    node $T/restyle-image.mjs --image photo.jpg --style inkwash --out photo-inkwash.png && open photo-inkwash.png

Still → motion → assembled cut:

    node $T/image-to-video.mjs --image stills/01.png --prompt "slow drift, mist rolls left" --out clips/01.mp4
    node $T/stitch.mjs --list shots.txt --music bed.mp3 --out final.mp4 && open final.mp4

Transcription ONLY when asked for a transcript:

    node $T/transcribe.mjs interview.mp3 --out transcript.json

## Gotchas earned the hard way

- **`node --check` is not a smoke test.** It passes on a file with an undefined
  variable. Run the tool.
- macOS screenshot filenames contain a narrow no-break space (U+202F) before
  "PM" — a typed path never matches. Glob or `find -exec`.
- ffmpeg `signalstats` writes to **stderr**; `execFileSync` returns stdout only.
- Edit models need an instruction verb ("Repaint this photograph, keeping the
  same composition…"); a bare style noun-phrase returns the source untouched.
- Negation summons what it forbids. Describe positively.
- A file named `*-test.mjs` is evidence of an experiment, not of a decision.
  Do not rebuild a style around its outputs.
- `gpu-box stop` ends GPU billing and keeps the weights; only `down` (destroy)
  ends billing entirely. Provisioning pulls LTX's 29GB checkpoint before the USO
  models — for a stills-only job, pull the four USO files directly instead of
  paying to wait for the whole manifest.
- Shell-quoting a prompt out of a file: strip a `Shot N — 12 s` header only if
  it's actually there, and BSD `sed` needs `d` inside braces terminated (`{...;}`).
  Put anything with a loop in a script file, not a one-liner.
