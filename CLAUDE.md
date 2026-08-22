# CLAUDE.md — media-tools

## SHOW ME PIXELS (law, 2026-08-20 — "a path is not a picture")
Every claim in this repo is a claim about pixels, so every claim comes with the
pixels ON SCREEN. If a message to Ryan names an image or a video, `open` it in
the same turn. Not "it's at jobs/.../evidence-foo.png", not "it's on your
Desktop", not a symlink to go find. His words, after repeating it for sessions:
*"I'm not a machine, I need pixels in front of my eyes. So if you say, hey, take
a look, put pixels up. Make that a rule. Make it more than a rule. Make it a
law."* Note `Read`ing an image shows it to the MODEL, not to him — only `open`
is showing.

AMENDED 2026-08-21: this is a rule about PRECISION, not frequency. Ryan, after a
session that opened a picture for every intermediate: *"when there's something
you need to show me, you can show me precisely instead of showing a path where
to find it. Not like every single change needs to come before my eyes."* Name a
visual and you still open it — but name fewer. Show at verdict points; a dead
hypothesis is a sentence, not a contact sheet. **Probe renders go to the
scratchpad and are deleted; only a visual a LIVE CLAIM cites, or one he ruled
on, is written into the repo.** And any stage that writes video clears its own
scaffolding — measured 2026-08-21, all of `evidence/` was 124MB while one
concat left 583MB of intermediate mp4s. Enforced by `~/.claude/hooks/show-me-pixels-stop.sh`, which refuses
to end a turn whose text names a visual that was never opened.

## MOTION BEFORE CAMERA (law, 2026-08-20 — Ryan: "Bring it to life. That is number one.")
In any project whose subject is a still image made to move, **authoring the
motion comes first and the camera comes last.** Ryan, after five days of being
handed camera moves over still ink: *"stop cutting corners and doing the same
fucking camera pan shot… you still keep putting it off and showing me the same
fucking zigzag Ken Burns left, right, camera pan. Not that we shouldn't, but
that shouldn't be the only thing we're doing."*

The drift is structural, so expect it in yourself: parallax is cheap, fast and
*looks* like progress; authoring stroke cycles is slow manual work and is the
actual deliverable. A flight over a still painting is not a milestone — it is
the corner being cut. Measured: `jobs/wang-meng` reached a 31-station, 20-minute
route with living cycles in exactly ONE of five zones; twelve of its stations
push into water that does not move.

Enforced, not requested: `jobs/wang-meng/film/compile-flight.py` REFUSES to
render a leg whose zone has no living cycles (`LIVING GATE`). Reaching for
`--allow-dead-zones` to get a pretty flight out the door IS the violation.
Read `jobs/wang-meng/STATE.md` — the law and the work order are at the top.

## NAME THE TECHNIQUE BEFORE YOU PICK THE TOOL (law, 2026-08-20 — bible §5.10)
Ryan: *"when your only tool is the hammer… all of your problems start looking
like nails."* Before reaching into `tools/`, say in one sentence what a
practitioner of the craft would DO. *"A leaf in wind is a cut-out cel on a hinge
over a clean background"* is a technique and can be checked. *"animate-strokes
has a --field sway flag"* is a tool that runs, which is not the same claim.

Two engines, neither of which feels like a mistake at the time: **a tool that
RUNS is more persuasive than a tool that FITS** (a flag means someone once
thought about the case, not that it works), and **tuning has a gradient while
tool-choice does not** — inside a tool every knob moves a number and feels like
progress, while stepping out to ask "wrong tool?" has no local signal. Measured
2026-08-20: four canopy-mask hypotheses and two render modes tuned inside
`animate-strokes` before Ryan named the right technique from memory.

So, in this repo:
1. **Every tool's docstring says what it is NOT for and names the tool that is.**
   Write it the moment a tool is proven wrong for something — a byproduct of
   failure, not extra work. `tools/cut-stroke.py` is the reference: it opens with
   a table of four other maskers and the measured reason each fails on strokes.
2. **`SKILL.md`'s problem table gives ONE answer per problem.** It had two
   adjacent rows — "the leaves should stir" and "a branch should swing" — sending
   one problem to two tools, wrong one first. When two rows can describe one
   situation, merge them and write down the TEST that separates the cases.

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
