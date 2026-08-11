# CLAUDE.md — media-tools

## What this project is
The toolbox. Every media capability (image gen, i2v, restyle, transcription,
stitch, GPU rental, frame stylization) is ONE single-purpose CLI in `tools/`.
A "lane" (bongpot, cutwork) is a script that composes these tools — never the
other way round. Spec: `docs/specs/2026-08-11-media-tools-design.md`.

## The tool contract (law — no exceptions)
1. One job per tool; its description has no "and".
2. Explicit I/O: inputs by flag, outputs by `--out`. A tool needing a
   transcript takes `--transcript path` — it NEVER runs transcription itself.
   No tool invokes another tool.
3. `--help` is the contract: usage, every flag, one worked example; exits 0.
4. JSON on stdout where there is data; progress/logs on stderr; meaningful
   exit codes; no side effects beyond the named outputs.
5. Styles by reference: `--style inkwash` → `styles/inkwash/style.json`.
   Style strings never live in tool code.
6. Composition lives in `jobs/<name>/run.sh` or the caller's own scripts.
7. Foreign-cwd rule: tools resolve `.env` and `styles/` via `import.meta.url`
   (repo-relative), never `process.cwd()`. Flag paths resolve against cwd.

## Naming
Verb-noun tools (`generate-image.mjs`) · `_`-prefix vendor adapters
(`_replicate.mjs`) · plain-noun data dirs (`styles/`, `jobs/`).
Names state what the thing does; cleverness in a name is a cost.

## Locked decisions
- Deepgram ALWAYS for transcription (nova-3, diarized). Never Whisper.
- Salvage, not rewrite: logic moved from cutwork/clipsmith stays as proven.
- bongpot untouched until next opened; its tools extract lazily, one at a time.
- No daemon, no server, no plugin system. New tool = new file + a catalog line
  in `SKILL.md`.

## How to work with Ryan
Pressure-test before agreeing. Mentor mode: name the principle and the
industry term. His eyes are the verdict on anything visual — `open` the file,
never declare it good unread. Report WHERE work landed by exact path. Small
commits with search-bait subjects.
