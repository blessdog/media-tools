# media-tools — design spec

**Date:** 2026-08-11 · **Status:** approved by Ryan (session dialogue) · **Author:** Claude + Ryan

## 1. Problem

Media capabilities (image generation, image-to-video, video restyle, transcription,
Vast.ai GPU orchestration, the ink-wash style, THE EAR) are trapped inside
lane-specific repos (`bongpot`, `cutwork`, dead `clipsmith`) as copied files.
The copies have measurably drifted: `generate-stills.mjs` differs by 20 lines
between bongpot and cutwork (cutwork got the flux-2 fixes 2026-08-05; bongpot
never did); `wan-clips.mjs` by 8; `_replicate.mjs` by 2. Every new project
either re-copies (more drift) or is built inside a lane it doesn't belong to.
Ryan's six-months-out test: a pet-shop commercial, a skydiving montage, an
ink-washed transcript film — arbitrary projects must be able to use every
capability without inheriting any lane.

## 2. Decision

**Unix philosophy, tools-first.** Every micro-capability is its own
single-purpose CLI in ONE repo (`~/projects/media-tools/`). A "lane" is not an
owner of tools — it is a script that composes them. Nothing runs implicitly.

This knowingly **reverses the 2026-07-03 deliberate fork** ("deliberately
forked, not shared") — for the capability layer only. Lane brains (bongpot's
5-pass, cutwork's insert brain) stay separate forever; lane purity survives.
The pattern generalizes `rectum`'s charter ("ends at the clip"): one tool, one
job, hard edge.

## 3. End state

```
~/projects/media-tools/
  CLAUDE.md                 what this is; the tool contract; locked decisions
  SKILL.md                  agent-facing catalog (symlinked → ~/.claude/skills/media-tools/)
  .env                      all provider keys, one place, never committed
  tools/
    transcribe.mjs          media file → diarized transcript.json (Deepgram nova-3)
    generate-image.mjs      prompt (+ --style) → image (Replicate)
    image-to-video.mjs      still + prompt → motion clip (seedance default)
    restyle-video.mjs       clip + style → restyled clip (luma/wan/kling adapters)
    stylize-frames.py       clip → deterministically styled frames (Blender compositor)
    stitch.mjs              clip list (+ audio) → one video (ffmpeg)
    gpu-box.mjs             rent / provision / kill Vast.ai box
    _replicate.mjs          vendor adapter (internal; _-prefix = not a tool)
    _comfy.mjs              vendor adapter
    _fleet.mjs              vendor adapter
    workflows/              proven ComfyUI graphs (LTX json salvaged from clipsmith)
  styles/
    inkwash/
      style.json            prompt string, model params, negation-trap notes
      fusion-theme.json     media-studio's representation (adopted on its next touch)
      treatment-params.json Blender recipe values
      reference/            images that DEFINE the look — approved by Ryan's eyes
  jobs/                     gitignored scratch; one-off compositions run here
  docs/
    specs/                  this file
```

Future tools are siblings: `the-ear`, `remove-silence`, `image-to-3d` — one
file plus one catalog line each. No new folder taxonomy, ever, without a spec.

## 4. The tool contract

Every file in `tools/` (non-`_`-prefixed) obeys, no exceptions:

1. **One job.** Its description has no "and."
2. **Explicit I/O.** Inputs by flag; outputs by `--out`. A tool needing a
   transcript takes `--transcript path` — it NEVER runs transcription itself.
   No tool invokes another tool.
3. **`--help` is the contract.** Usage, every flag, one worked example.
   Ground truth for humans and agents alike.
4. **JSON on stdout** where there is data; meaningful exit codes; no side
   effects beyond the named outputs.
5. **Styles by reference.** `--style inkwash` resolves to
   `styles/inkwash/style.json`. Style strings never live in tool code.
6. **Composition lives in scripts** (`jobs/<name>/run.sh`, written/edited by
   Ryan or drafted by an agent) — never inside tools.

Naming convention: **verb-noun for tools** (`generate-image`), **vendor names
for vendor adapters** (`_replicate` — the vendor is the description), **plain
nouns for data dirs** (`styles/`, `jobs/`). Names state what the thing does;
cleverness is a cost.

## 5. styles/ — the look SSOT

A style is DATA in every representation it has, so the look outlives any
rendering technology. `inkwash/` is the founding member:

- `style.json` — the diffusion prompt string (from `cutwork/config/creative.js`
  `INK_WASH_STYLE`), model parameters, and the documented negation trap
  (naming a forbidden thing summons it — describe positively).
- `treatment-params.json` — the Blender compositor recipe values.
- `fusion-theme.json` — media-studio's theme data (copied in at phase 1;
  media-studio adopts the SSOT copy on its next touch, not before).
- `reference/` — the frozen images that define "right." Ryan's eyes are the
  verdict; this folder is that verdict made durable.

## 6. Discovery — one skill, two layers

- **`SKILL.md`** in-repo (SSOT; drifts show in the same diff as code),
  symlinked into `~/.claude/skills/media-tools/`. Frontmatter description:
  "Use when creating, transcribing, styling, animating, or assembling any
  image/video/audio media." Body = catalog table + composition examples.
  Progressive disclosure: description always in context; body loads on use.
- **`--help`** makes every tool self-describing with no skill installed —
  any agent, any harness. The skill is the index; help text is the contract;
  behavior lives only in the CLIs.

Bible addendum (drafted in phase 4): "Agent-facing tool surfaces" — this
pattern, recorded as a principle.

## 7. Migration phases

Salvage, not rewrite (bible §5.3): files MOVE and get renamed/normalized;
logic is not rebuilt. Each phase independently shippable.

| # | phase | done when |
|---|---|---|
| 1 | **Bootstrap**: repo, Day-0 checklist (bible §1), contract in CLAUDE.md, `styles/inkwash/` extracted, FIRST tool moved (`quick-still.mjs` → `generate-image.mjs`) to prove contract + style resolution together | repo tagged `project-start`; `generate-image --style inkwash` renders one approved test image from a foreign cwd |
| 2 | **Salvage cutwork's remaining tools**: move + rename per §3; flags normalized; cutwork's copies deleted; cutwork configs re-pointed | every tool runs from a foreign cwd; `--help` passes contract review; cutwork's existing flows still work |
| 3 | **Salvage clipsmith**: `stitch.mjs` + LTX workflow in; folder → `mediaStudio/archive/` | stitch proven on real clips; clipsmith gone from workspace |
| 4 | **Skill + docs**: SKILL.md, symlink, bible section | fresh session in a random directory reaches the right tools unprompted on a media request |
| 5 | **Prove end-to-end**: the Sheen ink-wash restyle as `jobs/sheen-inkwash/run.sh` | finished clip Ryan's eyes approve |
| 6+ | **Lazy extractions**: bongpot's tools (THE EAR first), each only when bongpot is next opened | one catalog entry per extraction; bongpot never regresses |

Phase 5 precedes 6 deliberately: the architecture proves itself on real work
before any surgery near bongpot.

## 8. Worked example (the thesis test)

"30-second commercial for Dave's pet shop, ink wash, logo at the end" — agent
in any directory hits the skill and drafts `jobs/petshop/run.sh`:

```zsh
T=~/projects/media-tools/tools
for shot in storefront puppy-window kid-goldfish logo-card; do
  node $T/generate-image.mjs --style inkwash --prompt "$(cat prompts/$shot.txt)" --out stills/$shot.png
done                                          # Ryan eyeballs stills; regen until right
for shot in storefront puppy-window kid-goldfish; do
  node $T/image-to-video.mjs --image stills/$shot.png --prompt "$(cat motion/$shot.txt)" --out clips/$shot.mp4
done
node $T/stitch.mjs --list shots.txt --audio vo.mp3 --out petshop-30s.mp4
```

No transcription ran — none was asked for. The lane died; the look survived.

## 9. Decisions log

| decision | rationale |
|---|---|
| Tools-first (Unix), lanes are scripts | Ryan's precision/control requirement; rectum charter generalized |
| One repo, absolute-path invocation | one copy on disk = drift structurally impossible; agent-native via Bash |
| NOT a monorepo/npm workspace | team-scale ceremony a solo+agents workflow doesn't need |
| MCP deferred, not rejected | Claude Code calls CLIs natively; MCP is a thin wrapper later if a non-CLI consumer appears |
| One skill, not one per tool | discovery fragmentation is the same disease as scattered repos |
| bongpot untouched until next opened | don't-regress-working-code; lazy extraction per tool |
| cutwork renamed AFTER extraction | can't name a pile that's about to change shape |
| clipsmith archived after salvage | dead one-day experiment; third stale copy of vast/comfy tools |
| media-studio untouched now | active project; adopts `styles/` SSOT on next touch |
| `jobs/` gitignored scratch; real projects graduate to `~/projects/<name>/` | one-offs stay cheap; nothing forced into repos prematurely |

## 10. Non-goals

- No daemon, no server, no UI, no queue. Conversational orchestration + shell scripts.
- No plugin/registry system. New tool = new file + catalog line.
- No shared npm package between lane repos. The toolbox is the only sharing surface.
- No speculative tools. A capability earns a file when real work needs it (YAGNI).

## 11. Risks

- **Phase 2 breaks cutwork mid-flight** → mitigated by per-tool moves with
  cutwork verified after each, small commits, each reversible.
- **Contract rot** (tools grow flags/implicit behavior) → `--help` review is
  part of any tool PR; the contract lives in CLAUDE.md where every session loads it.
- **Style SSOT ignored under deadline** ("just paste the prompt string") →
  `--style` flag makes the right way the easy way; creative.js copy deleted in
  phase 2 so there is nothing else to paste from.
