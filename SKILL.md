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
| `gpu-box.mjs` | rent / provision / kill a Vast.ai GPU box |

Internals (not tools): `_env` `_replicate` `_comfy` `_fleet` `_uso`.
Proven ComfyUI graphs in `tools/workflows/`.
Related standalone tool: `rectum` (URL → clip on disk) at
`~/projects/mediaStudio/rectum/`, its own CLI.

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
supplies the LOOK):

    node $T/generate-image.mjs --style inkwash --prompt "$(cat regen/shot-02.txt)" --out regen/shot-02.png
    open regen/shot-02.png

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
