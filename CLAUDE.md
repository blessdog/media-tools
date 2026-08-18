# CLAUDE.md — media-tools

## EVIDENCE LANDS IN THE REPO (law, 2026-08-18 — Ryan: "you are too amnesic")
Any image, video, chart, or diagnostic that is (a) opened on Ryan's screen,
(b) cited in a claim or verdict, or (c) produced by a probe/experiment, is
WRITTEN INTO THE REPO under `jobs/<job>/` before or at the moment it is shown
— never left in a session scratchpad. Scratchpads are for intermediates nobody
will ever cite. The failure this bans, measured: a displacement-grid diagnostic
was rendered to a scratchpad on 2026-08-16, opened, argued from — and the file
evaporated with the session; only Ryan's manual screenshot preserved it, and
its provenance is unrecoverable. Every experiment's evidence also gets one line
in the job's STATE.md (what it shows, where it lives) in the same session that
made it. Research that isn't cataloged in the repo does not exist.

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

## NEVER SHIP SLOP (Ryan, 2026-08-12 — law, not preference)
Cheap + fast diffusion = slop, and **slop is worthless trash**. His words, after
I animated approved inkwash stills with a cheap hosted i2v model: *"running a
video through this cheap replicate video model is basically taking a shit
directly in my eyes. That would actually be preferable to what this shit pumps
out."* It is instantly apparent — three hands, impossible motion, a painting
turning photographic.

So: **anything Ryan will LOOK at gets the best renderer available, from the
first frame.** Rent the box, wait the 15 minutes. Never substitute a fast hosted
model to "prove the pipeline" — a pipeline proven with slop proves nothing he
cares about. If the good path is unavailable, say so and STOP; do not silently
fall back. `generate-image`'s hosted fallback is for plumbing checks he is not
being asked to look at, never for a deliverable.

### AMENDED 2026-08-12 (Ryan): judge the OUTPUT, not the architecture
The original rule banned distilled and hosted models outright. That is too
blunt and it was already wrong twice in one day:

- Hosted `flux-2-dev` produced a frame Ryan called *"decent… looks like someone
  actually painted"* — the blanket "hosted = slop" would have refused to make it.
- The Krea-2 ink-wash LoRAs he wants are trained on **Krea-2-Turbo**, a
  distilled base. Vetoing them on the word "turbo" would have thrown away the
  best-matching style found so far.

Ryan: *"shouldn't be outright banning a distilled model. Silly. Should be on a
case by case basis."*

So the rule is: **slop is a property of pixels, not of a model's category.**
Distillation, quantisation and hosted inference are all legitimate until the
output says otherwise. What survives unchanged:

- **His eyes are the verdict.** `open` the file; never declare it good unread.
- **Never silently downgrade.** Substituting a lesser renderer without saying so
  is the actual sin — that is what "taking a shit directly in my eyes" was about.
- **Name the trade.** "turbo, distilled, 8 steps" goes in the manifest so a bad
  frame is diagnosable instead of mysterious.
- **A/B rather than assume.** Turbo vs raw, fp8 vs bf16 — same seed, both
  rendered, he picks.

Note the distinction that matters: **distillation** changes what the model does
(fewer steps, altered behaviour) and must be judged. **Quantisation** (fp8, int8)
is a precision trade on the same model and is normally free. Do not conflate them.

## THE OUTPUT CONTRACT (law, 2026-08-18 — enforced in gpu-box.mjs)
Before ANY model campaign or GPU rent, state in one line what the output
physically is — resolution, frame count, fps — against what the deliverable
needs. The spec is on the model card, free. If it fails the deliverable, KILL
before architecture, before cost estimates, before enthusiasm. Measured
failure: three A100 rentals (~$9, 1.5 days) for Voyager before anyone said
"768×512 against a 105-megapixel scroll." `gpu-box.mjs up --rent` now refuses
without `--contract "<spec — verdict>"`. Env checks ask "will it run"; the
contract asks "can the output survive Ryan's eyes" (see NEVER SHIP SLOP).

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

**Prose hides errors (2026-08-14, bible §4.7).** This bites hardest in a media
repo, because nearly every claim here is a claim about pixels. Never describe
what an image or clip *would* show — render it and `open` it. Never use "it" as
a sentence subject without naming the referent. And before believing any
measurement of a rendered result, BUILD THE NULL: a static control, a synthetic
flat version, an untreated frame. Measured this session — a parallax claim
survived an hour in prose and died 90 seconds after being rendered beside a
synthetic pure zoom. Two different metrics had "proved" it; controls explained
away both. A metric with a plausible story attached is not evidence.
