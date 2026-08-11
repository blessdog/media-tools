# media-tools Implementation Plan (Phases 1–5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `~/projects/media-tools/` — one repo of single-purpose media CLIs salvaged from cutwork/clipsmith — proven end-to-end on the Sheen ink-wash restyle.

**Architecture:** Unix tools-first. Each capability is one CLI obeying the tool contract (spec §4). Vendor adapters are `_`-prefixed internals. Styles are data in `styles/`. Lanes compose tools via scripts; no tool calls another tool.

**Tech Stack:** Node ≥20 (ESM, no deps beyond node: builtins), Python/Blender (stylize-frames only), ffmpeg, Replicate API, Deepgram API, Vast.ai API.

**Spec:** `docs/specs/2026-08-11-media-tools-design.md` — read §4 (tool contract) before any task.

## Global Constraints

- **Tool contract (spec §4) is law:** one job; explicit I/O by flag; `--out` for outputs; no tool invokes another tool; `--help` prints usage + every flag + one example, exits 0; JSON on stdout where there's data; no side effects beyond named outputs.
- **Names:** verb-noun tools (`generate-image.mjs`), `_`-prefix vendor adapters, plain-noun data dirs.
- **Foreign-cwd rule:** every tool must work when invoked from ANY directory. Therefore `.env` and `styles/` resolve relative to the tool file (`import.meta.url`), NEVER `process.cwd()`. Inputs/outputs from flags resolve against cwd (caller's intent).
- **Salvage, not rewrite:** moved files keep their logic; only imports, env resolution, and flags are normalized. Do not "improve" working code.
- **No test framework.** Verification = `node --check` (syntax), `--help` exit-0 checks, deterministic local runs (ffmpeg-generated fixtures), and ONE live API smoke test only where a phase criterion demands it (costs cents; announce before running).
- **Never print `.env` contents** to stdout/logs. Copy keys with `cp`/`grep -c` checks only.
- **Small commits, search-bait subjects, one concern each.** Work happens in `/Users/SSDrive/projects/media-tools/` unless the task says otherwise.
- **cutwork must not regress:** any task touching `/Users/SSDrive/projects/mediaStudio/cutwork/` ends with `node --check` passing on every modified file.

---

## Phase 1 — Bootstrap (spec §7.1)

### Task 1: Repo scaffolding — CLAUDE.md, .env, directories

**Files:**
- Create: `CLAUDE.md`, `tools/`, `styles/`, `jobs/.gitkeep`
- Copy: `/Users/SSDrive/projects/mediaStudio/cutwork/.env` → `.env` (never committed; `.gitignore` already covers it)

**Interfaces:**
- Produces: repo layout every later task assumes; `.env` holding `REPLICATE_API_TOKEN`, `DEEPGRAM_API_KEY` (+ any `VAST_*` keys present in cutwork's).

- [ ] **Step 1: Directories + env**

```bash
cd /Users/SSDrive/projects/media-tools
mkdir -p tools styles jobs && touch jobs/.gitkeep
cp /Users/SSDrive/projects/mediaStudio/cutwork/.env .env
grep -c "REPLICATE_API_TOKEN\|DEEPGRAM_API_KEY" .env   # expect ≥2; do NOT cat .env
```

- [ ] **Step 2: Write `CLAUDE.md`**

```markdown
# CLAUDE.md — media-tools

## What this project is
The toolbox. Every media capability (image gen, i2v, restyle, transcription,
stitch, GPU rental, frame stylization) is ONE single-purpose CLI in `tools/`.
A "lane" (bongpot, cutwork) is a script that composes these tools — never the
other way round. Spec: `docs/specs/2026-08-11-media-tools-design.md`.

## The tool contract (law — no exceptions)
1. One job per tool; description has no "and".
2. Explicit I/O: inputs by flag, outputs by `--out`. A tool needing a
   transcript takes `--transcript path` — it NEVER runs transcription itself.
   No tool invokes another tool.
3. `--help` is the contract: usage, every flag, one worked example; exits 0.
4. JSON on stdout where there is data; meaningful exit codes; no side effects
   beyond the named outputs.
5. Styles by reference: `--style inkwash` → `styles/inkwash/style.json`.
   Style strings never live in tool code.
6. Composition lives in `jobs/<name>/run.sh` or the caller's own scripts.
7. Foreign-cwd rule: tools resolve `.env`/`styles/` via `import.meta.url`
   (repo-relative), never `process.cwd()`. Flag paths resolve against cwd.

## Naming
Verb-noun tools (`generate-image.mjs`) · `_`-prefix vendor adapters
(`_replicate.mjs`) · plain-noun data dirs (`styles/`, `jobs/`).

## Locked decisions
- Deepgram ALWAYS for transcription (nova-3, diarized). Never Whisper.
- Salvage, not rewrite: logic moved from cutwork/clipsmith stays as proven.
- bongpot untouched until next opened; its tools extract lazily, one at a time.
- No daemon, no server, no plugin system. New tool = new file + catalog line
  in SKILL.md.

## How to work with Ryan
Pressure-test before agreeing. Mentor mode: name the principle and industry
term. His eyes are the verdict on anything visual — `open` the file, never
declare it good unread. Report WHERE work landed by exact path. Small commits,
search-bait subjects.
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md jobs/.gitkeep && git commit -m "scaffold: CLAUDE.md with the tool contract; tools/ styles/ jobs/ layout"
```

---

### Task 2: `styles/inkwash/` — the style SSOT

**Files:**
- Create: `styles/inkwash/style.json`, `styles/inkwash/treatment-params.json`, `styles/inkwash/reference/.gitkeep`
- Read (source): `/Users/SSDrive/projects/mediaStudio/cutwork/config/creative.js:39` (INK_WASH_STYLE), `:46` (PHOTOREAL_PLATE_STYLE), `:48-59` (object variant + negation-trap doc)

**Interfaces:**
- Produces: `style.json` with shape `{ "name", "prompt", "objectPrompt", "notes", "image": { "model", "params" } }` — `generate-image.mjs` (Task 4) reads `.prompt` and `.image.model`/`.image.params`.

- [ ] **Step 1: Write `styles/inkwash/style.json`**

Copy the prompt strings VERBATIM from `creative.js` (open the file; do not retype from this plan). Structure:

```json
{
  "name": "inkwash",
  "prompt": "<VERBATIM the INK_WASH_STYLE string from cutwork/config/creative.js line 39>",
  "objectPrompt": "<VERBATIM the object/mechanism variant string defined just below it>",
  "notes": "NEGATION DOES NOT WORK: naming a forbidden thing summons it (flux-2-dev returned calligraphy + red seal when told 'no Chinese characters', S5-B-030). Describe positively: the paper is blank and unmarked. Style enters at the keyframe/restyle step, never at identity-plate genesis (2026-06-09 decoupling).",
  "image": {
    "model": "replicate/black-forest-labs/flux-2-dev",
    "params": { "output_format": "png" }
  }
}
```

- [ ] **Step 2: Write `styles/inkwash/treatment-params.json`**

Open `/Users/SSDrive/projects/mediaStudio/cutwork/tools/treatment.py`, find the compositor node values (blur size, glare/bloom settings, curve points, desaturation factor, ink-mix factor, paper-mix factor — they are literals in the node-group build code). Record them:

```json
{
  "source": "cutwork/tools/treatment.py as of 2026-08-05 (moves to tools/stylize-frames.py in Task 9)",
  "params": { "<name each literal found>": "<its value>" }
}
```

- [ ] **Step 3: Validate + commit**

```bash
node -e "const s=require('./styles/inkwash/style.json'); if(!s.prompt||s.prompt.length<100) throw 'prompt missing'; console.log('style.json OK:', s.prompt.length, 'chars')"
git add styles/ && git commit -m "styles: inkwash SSOT — prompt strings, negation-trap notes, treatment params extracted from cutwork"
```

*(`fusion-theme.json` is deferred: media-studio is untouched this round; its theme data joins on that repo's next touch, per spec §9.)*

---

### Task 3: `tools/_env.mjs` + `tools/_replicate.mjs` — the shared plumbing

**Files:**
- Create: `tools/_env.mjs` (new, ~25 lines)
- Copy+modify: `/Users/SSDrive/projects/mediaStudio/cutwork/tools/_replicate.mjs` → `tools/_replicate.mjs`

**Interfaces:**
- Produces: `_env.mjs` exports `repoRoot(): string` and `envKey(name: string): string` (throws if missing). `_replicate.mjs` exports `latestVersion`, `predict`, `predictVersioned`, `predictModel`, `fetchBytes`, `sleep` — signatures unchanged from cutwork's copy.

- [ ] **Step 1: Write `tools/_env.mjs`**

```js
// media-tools — repo-rooted .env access. Tools run from ANY cwd (foreign-cwd
// rule, CLAUDE.md §7), so the .env lives next to this file's parent dir and is
// resolved via import.meta.url — never process.cwd().
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

export function repoRoot() {
  return dirname(dirname(fileURLToPath(import.meta.url)));
}

export function envKey(name) {
  if (process.env[name]) return process.env[name];
  let text = '';
  try { text = readFileSync(join(repoRoot(), '.env'), 'utf8'); } catch {}
  const m = text.match(new RegExp(`^\\s*${name}\\s*=\\s*(.+?)\\s*$`, 'm'));
  if (m) return m[1].replace(/^["']|["']$/g, '');
  throw new Error(`${name} not set (env or ${join(repoRoot(), '.env')})`);
}
```

- [ ] **Step 2: Copy `_replicate.mjs`, inline the one config import**

```bash
cp /Users/SSDrive/projects/mediaStudio/cutwork/tools/_replicate.mjs tools/_replicate.mjs
```

Then in `tools/_replicate.mjs` replace the import line
`import { REPLICATE_API_BASE } from '../config/config.js';` with:

```js
const REPLICATE_API_BASE = 'https://api.replicate.com/v1';
```

(One consumer, one constant — inlining is correct; a config SSOT returns if a second consumer appears. Everything else stays byte-identical.)

- [ ] **Step 3: Verify + commit**

```bash
node --check tools/_env.mjs && node --check tools/_replicate.mjs
node -e "import('./tools/_env.mjs').then(m=>console.log('root:',m.repoRoot()))"   # prints .../projects/media-tools
git add tools/_env.mjs tools/_replicate.mjs && git commit -m "tools: _env repo-rooted secrets + _replicate adapter salvaged from cutwork (config import inlined)"
```

---

### Task 4: `tools/generate-image.mjs` — founding tool, proves contract + styles

**Files:**
- Create: `tools/generate-image.mjs` (salvaged from `/Users/SSDrive/projects/mediaStudio/cutwork/tools/quick-still.mjs`)

**Interfaces:**
- Consumes: `envKey` from `_env.mjs`; `predict`, `fetchBytes` from `_replicate.mjs`; `styles/<key>/style.json` shape from Task 2.
- Produces: the flag pattern every later tool copies: `--help`, `--style KEY | --raw`, `--out` required.

- [ ] **Step 1: Write the tool**

```js
// media-tools — generate-image: prompt (+ style) → one image. One job.
//
//   node generate-image.mjs --prompt "..." --out img.png [--style inkwash]
//     [--object] [--raw] [--aspect 16:9] [--seed N] [--model replicate/...]
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { envKey, repoRoot } from './_env.mjs';
import { predict, fetchBytes } from './_replicate.mjs';

const HELP = `generate-image — text prompt (+ optional style) to one image via Replicate

usage: node generate-image.mjs --prompt "..." --out path.png [flags]

flags:
  --prompt TEXT   (required) content description
  --out PATH      (required) output image path
  --style KEY     style from styles/KEY/style.json, prepended (default: inkwash)
  --object        use the style's objectPrompt variant (apparatus, not figures)
  --raw           no style prefix; --prompt verbatim
  --aspect R      16:9 | 3:4 | 1:1  (default 16:9)
  --seed N        reproducible generation
  --model M       override model (default: style's image.model)

example:
  node ~/projects/media-tools/tools/generate-image.mjs \\
    --style inkwash --prompt "a pet shop storefront at dusk" --out stills/01.png`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const prompt = flag('--prompt'); const out = flag('--out');
if (!prompt || !out) { console.error(HELP); process.exit(2); }
const raw = args.includes('--raw');
const styleKey = flag('--style', 'inkwash');

let style = null;
if (!raw) {
  const p = join(repoRoot(), 'styles', styleKey, 'style.json');
  try { style = JSON.parse(readFileSync(p, 'utf8')); }
  catch { console.error(`unknown --style '${styleKey}' (no ${p})`); process.exit(2); }
}
const stylePrefix = style ? (args.includes('--object') ? style.objectPrompt : style.prompt) : '';
const fullPrompt = raw ? prompt : `${stylePrefix} ${prompt}`;
const model = flag('--model', style?.image?.model || 'replicate/black-forest-labs/flux-2-dev');

const input = { prompt: fullPrompt, aspect_ratio: flag('--aspect', '16:9'), ...(style?.image?.params || { output_format: 'png' }) };
const seed = flag('--seed'); if (seed) input.seed = parseInt(seed, 10);

console.error(`generate-image: ${model} → ${out}`);
const url = await predict(model, input, { token: envKey('REPLICATE_API_TOKEN'), label: 'generate-image' });
const bytes = await fetchBytes(url);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);
console.log(JSON.stringify({ out, bytes: bytes.length, model, style: raw ? null : styleKey }));
```

(Salvage notes: `predict()` not `predictModel()` — flux-2-dev 404s on the model-scoped endpoint, per cutwork `config.js:41` comment. Progress goes to **stderr**, result JSON to **stdout**, per contract.)

- [ ] **Step 2: Static checks**

```bash
node --check tools/generate-image.mjs
node tools/generate-image.mjs --help          # exits 0, prints contract
cd /tmp && node ~/projects/media-tools/tools/generate-image.mjs --help && cd -   # foreign cwd
```

- [ ] **Step 3: LIVE smoke test (phase-1 done criterion — costs cents, announce first)**

```bash
cd /private/tmp && node ~/projects/media-tools/tools/generate-image.mjs \
  --style inkwash --prompt "a lone fisherman poling a flat skiff across still water at dawn" \
  --out /tmp/inkwash-smoke.png && open /tmp/inkwash-smoke.png
```

Expected: JSON line on stdout; image opens; **Ryan's eyes approve** the ink-wash look renders from `style.json`.

- [ ] **Step 4: Commit**

```bash
git add tools/generate-image.mjs && git commit -m "tools: generate-image — founding tool; styles-by-reference proven (quick-still salvage)"
```

**Phase 1 complete when:** smoke image approved. This closes spec §7 phase 1.

---

## Phase 2 — Salvage cutwork's remaining tools (spec §7.2)

### Task 5: `tools/image-to-video.mjs`

**Files:**
- Create: `tools/image-to-video.mjs` (salvaged from `cutwork/tools/quick-i2v.mjs`)

**Interfaces:**
- Consumes: `envKey` (`_env.mjs`), `predictModel`, `fetchBytes` (`_replicate.mjs`).
- Produces: `uploadFile(path, token, mime)` stays INTERNAL to this tool for now (restyle-video gets its own copy in Task 15; promote to `_replicate.mjs` only if a third consumer appears — bible §2.3).

- [ ] **Step 1: Copy and normalize**

```bash
cp /Users/SSDrive/projects/mediaStudio/cutwork/tools/quick-i2v.mjs tools/image-to-video.mjs
```

Edits (keep the MODELS adapter table and upload-not-data-URI logic byte-identical):
1. Replace the local `replicateToken()` function with `import { envKey } from './_env.mjs';` and call `envKey('REPLICATE_API_TOKEN')`.
2. Add a `HELP` string + `--help` handling in the Task-4 pattern (usage, all six flags — `--image --prompt --out --duration --resolution --model --moving` — plus the seedance-default / wan-E002 note from the header comment, one example).
3. Final line becomes contract JSON on stdout: `console.log(JSON.stringify({ out, bytes: bytes.length, model, duration, resolution }));` with progress prints moved to `console.error`.

- [ ] **Step 2: Verify + commit**

```bash
node --check tools/image-to-video.mjs && node tools/image-to-video.mjs --help
git add tools/image-to-video.mjs && git commit -m "tools: image-to-video (quick-i2v salvage) — seedance default, E002 upload guard kept"
```

### Task 6: `tools/transcribe.mjs`

**Files:**
- Create: `tools/transcribe.mjs` (salvaged from `cutwork/tools/transcribe-local.mjs`)

**Interfaces:**
- Consumes: `envKey` from `_env.mjs`.
- Produces: transcript.json shape `{ words: [...], utterances: [{start,end,text,speaker,confidence}] }` — unchanged; downstream consumers (cutwork's packer bridge) depend on it.

- [ ] **Step 1: Copy and normalize**

```bash
cp /Users/SSDrive/projects/mediaStudio/cutwork/tools/transcribe-local.mjs tools/transcribe.mjs
```

Edits:
1. Delete the `../config/config.js` import; inline the constants (values from cutwork `config.js:151-155`):

```js
const DEEPGRAM_LISTEN_URL = 'https://api.deepgram.com/v1/listen';
const DEEPGRAM_MODEL = 'nova-3';           // Deepgram ALWAYS — locked decision
const DEEPGRAM_UTT_SPLIT = 1.2;
```

2. Replace the local `key()` with `envKey('DEEPGRAM_API_KEY')`.
3. Make `--out` REQUIRED (contract: no default output location into a cwd-relative `outputs/`).
4. Add `HELP` + `--help` (flags: positional audio path, `--out`; note the audio/mpeg content-type and diarize/utterances params).
5. Summary lines → `console.error`; add final stdout JSON: `console.log(JSON.stringify({ out: outPath, words: words.length, utterances: utterances.length, speakers: new Set(utterances.map(u=>u.speaker)).size }));`

- [ ] **Step 2: Verify + commit**

```bash
node --check tools/transcribe.mjs && node tools/transcribe.mjs --help
git add tools/transcribe.mjs && git commit -m "tools: transcribe — Deepgram nova-3 diarized (transcribe-local salvage), constants inlined"
```

### Task 7: `tools/gpu-box.mjs`

**Files:**
- Create: `tools/gpu-box.mjs` (salvaged from `cutwork/tools/vast.mjs`, 385 lines, self-contained — no config imports)

- [ ] **Step 1: Copy verbatim, then normalize only env + help**

```bash
cp /Users/SSDrive/projects/mediaStudio/cutwork/tools/vast.mjs tools/gpu-box.mjs
grep -n "VAST_API_KEY\|\.env\|readFileSync('.env'" tools/gpu-box.mjs
```

Whatever local .env-reading it does (the grep shows it), replace with `envKey('VAST_API_KEY')` from `./_env.mjs`. Update the usage line to `gpu-box.mjs <up|status|down|stop|start|wait|run|forward>` and route `--help` to print it with exit 0. It also writes state under a `.vast/` dir — repo-root it: `join(repoRoot(), '.vast')`, and add `.vast/` to `.gitignore`. **No other edits** — 385 proven lines stay proven.

- [ ] **Step 2: Verify + commit**

```bash
node --check tools/gpu-box.mjs && node tools/gpu-box.mjs --help
node tools/gpu-box.mjs status        # live read-only call; expect "0 instances" table, $0 spend
printf '\n.vast/\n' >> .gitignore
git add tools/gpu-box.mjs .gitignore && git commit -m "tools: gpu-box — Vast.ai rent/kill CLI (vast.mjs salvage), env+state repo-rooted"
```

### Task 8: `tools/stylize-frames.py` + adapters + workflows

**Files:**
- Create: `tools/stylize-frames.py` (from `cutwork/tools/treatment.py` — verbatim, self-contained bpy script)
- Create: `tools/_comfy.mjs`, `tools/_fleet.mjs` (from cutwork, byte-identical copies)
- Create: `tools/workflows/` (copy `cutwork/tools/wan-*.json` graphs if any live beside the tools; the LTX graph arrives in Task 11 with clipsmith)

- [ ] **Step 1: Copy**

```bash
cp /Users/SSDrive/projects/mediaStudio/cutwork/tools/treatment.py tools/stylize-frames.py
cp /Users/SSDrive/projects/mediaStudio/cutwork/tools/_comfy.mjs tools/_comfy.mjs
cp /Users/SSDrive/projects/mediaStudio/cutwork/tools/_fleet.mjs tools/_fleet.mjs
```

`stylize-frames.py`: change only the usage strings' filename (`tools/treatment.py` → `tools/stylize-frames.py`). Its `--`-args pattern and node-graph code stay untouched. `_comfy.mjs`/`_fleet.mjs`: check imports with `head -20`; if either imports cutwork config, inline exactly as Task 3 did for `_replicate.mjs`; otherwise byte-identical.

- [ ] **Step 2: Verify + commit**

```bash
python3 -m py_compile tools/stylize-frames.py    # syntax only (bpy import fails outside Blender — expected; py_compile doesn't execute)
node --check tools/_comfy.mjs && node --check tools/_fleet.mjs
git add tools/ && git commit -m "tools: stylize-frames (Blender treatment salvage) + _comfy/_fleet adapters"
```

### Task 9: Re-point cutwork, delete its copies

**Files:**
- Modify: `/Users/SSDrive/projects/mediaStudio/cutwork/tools/generate-stills.mjs`, `wan-clips.mjs`, `i2v-replicate.mjs`, `runcomfy.mjs`, `dispatch-render.mjs`, `render-monitor.mjs`, `world3d-clips.mjs`, `image-to-3d.mjs` (whichever import the moved files — verify by grep, don't trust this list)
- Delete: `cutwork/tools/{quick-still.mjs, quick-i2v.mjs, transcribe-local.mjs, vast.mjs, treatment.py, _replicate.mjs, _comfy.mjs, _fleet.mjs}`

- [ ] **Step 1: Map the real import graph first**

```bash
cd /Users/SSDrive/projects/mediaStudio/cutwork
grep -rln "_replicate\|_comfy\|_fleet\|vast.mjs\|treatment.py" tools/ --include="*.mjs" | grep -v "quick-\|transcribe-local\|^tools/vast\|_replicate\|_comfy\|_fleet"
```

- [ ] **Step 2: Re-point every hit to the toolbox**

In each file from Step 1, change relative imports to the absolute toolbox path, e.g.
`from './_replicate.mjs'` → `from '/Users/SSDrive/projects/media-tools/tools/_replicate.mjs'`.
(Absolute path is deliberate: cutwork may move; the toolbox is the fixed point.)

- [ ] **Step 3: Delete the moved copies, verify cutwork**

```bash
git rm tools/quick-still.mjs tools/quick-i2v.mjs tools/transcribe-local.mjs tools/vast.mjs tools/treatment.py tools/_replicate.mjs tools/_comfy.mjs tools/_fleet.mjs
for f in tools/*.mjs; do node --check "$f" || echo "BROKEN: $f"; done   # expect zero BROKEN
```

- [ ] **Step 4: Commit (in cutwork)**

```bash
git add -A && git commit -m "tools: burners moved to ~/projects/media-tools — imports re-pointed, copies deleted (see media-tools spec 2026-08-11)"
```

**Phase 2 complete when:** all tools run `--help` from a foreign cwd; cutwork `node --check` clean.

---

## Phase 3 — Salvage clipsmith, archive it (spec §7.3)

### Task 10: `tools/stitch.mjs` — generalized from clipsmith

**Files:**
- Create: `tools/stitch.mjs` (salvage of `clipsmith/tools/stitch.mjs`'s `normalizeClip` + concat + music-duck logic; the hardcoded TIMELINE/cards/grades are clipsmith-lane content and do NOT come along)

**Interfaces:**
- Consumes: nothing from other tools (ffmpeg only — no API, no `.env`).
- Produces: `--list` file format = one clip path per line, `#` comments allowed.

- [ ] **Step 1: Write the tool**

```js
// media-tools — stitch: ordered clip list → one normalized video. One job.
// Salvaged core of clipsmith's stitch.mjs (normalize→concat→music duck);
// its hardcoded timeline/cards were lane content and stayed behind.
//
//   node stitch.mjs --list shots.txt --out final.mp4 [--music bed.mp3]
import { readFileSync, writeFileSync, mkdirSync, existsSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve, dirname } from 'node:path';
import { tmpdir } from 'node:os';

const HELP = `stitch — concatenate clips into one video, normalized to a uniform format

usage: node stitch.mjs --list shots.txt --out final.mp4 [flags]

flags:
  --list PATH    (required) text file: one clip path per line, # comments ok
  --out PATH     (required) output video
  --music PATH   music bed, ducked to 0.18 under clip audio
  --width N      default 1920
  --height N     default 1080
  --fps N        default 30

example:
  node ~/projects/media-tools/tools/stitch.mjs --list shots.txt --music vo.mp3 --out cut.mp4`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const listPath = flag('--list'); const outPath = flag('--out');
if (!listPath || !outPath) { console.error(HELP); process.exit(2); }
const music = flag('--music');
const W = parseInt(flag('--width', '1920'), 10), H = parseInt(flag('--height', '1080'), 10), FPS = parseInt(flag('--fps', '30'), 10);

const clips = readFileSync(listPath, 'utf8').split('\n')
  .map(l => l.trim()).filter(l => l && !l.startsWith('#'))
  .map(l => resolve(dirname(resolve(listPath)), l));
const missing = clips.filter(c => !existsSync(c));
if (missing.length) { console.error(`missing clips:\n  ${missing.join('\n  ')}`); process.exit(1); }

const segDir = join(tmpdir(), `stitch-${process.pid}`);
rmSync(segDir, { recursive: true, force: true }); mkdirSync(segDir, { recursive: true });
const ff = (a) => execFileSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...a]);

// clipsmith-proven normalize: letterbox (no crop), uniform codec/size/fps,
// silent-or-own audio so concat stream-copy is safe.
clips.forEach((src, n) => {
  const seg = join(segDir, `${String(n).padStart(3, '0')}.mp4`);
  const vf = [`scale=${W}:${H}:force_original_aspect_ratio=decrease`,
    `pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black`, `fps=${FPS},setsar=1`].join(',');
  ff(['-i', src, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
    '-map', '0:v:0', '-map', '1:a:0?', '-map', '0:a:0?',
    '-vf', vf, '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-shortest', seg]);
  console.error(`  ✓ ${n + 1}/${clips.length} ${src}`);
});

const listFile = join(segDir, 'concat.txt');
writeFileSync(listFile, clips.map((_, n) => `file '${join(segDir, `${String(n).padStart(3, '0')}.mp4`)}'`).join('\n'));
mkdirSync(dirname(resolve(outPath)), { recursive: true });
if (music && existsSync(music)) {
  const tmp = join(segDir, '_concat.mp4');
  ff(['-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', tmp]);
  ff(['-i', tmp, '-i', music,
    '-filter_complex', '[1:a]volume=0.18[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]',
    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-shortest',
    '-movflags', '+faststart', outPath]);
} else {
  ff(['-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', '-movflags', '+faststart', outPath]);
}
rmSync(segDir, { recursive: true, force: true });
console.log(JSON.stringify({ out: outPath, clips: clips.length, width: W, height: H, fps: FPS, music: music || null }));
```

- [ ] **Step 2: Deterministic local test (no API, fixture clips generated by ffmpeg)**

```bash
cd /private/tmp && mkdir -p stitch-test && cd stitch-test
ffmpeg -y -hide_banner -loglevel error -f lavfi -i testsrc=duration=1:size=640x360:rate=24 a.mp4
ffmpeg -y -hide_banner -loglevel error -f lavfi -i testsrc=duration=1:size=1280x720:rate=30 b.mp4
printf '# fixture\na.mp4\nb.mp4\n' > shots.txt
node ~/projects/media-tools/tools/stitch.mjs --list shots.txt --out out.mp4
ffprobe -v error -select_streams v -show_entries stream=width,height,r_frame_rate -of csv out.mp4
```

Expected: stdout JSON `{"clips":2,...}`; ffprobe reports `1920,1080` and `30/1`; duration ≈ 2s.

- [ ] **Step 3: Commit**

```bash
cd /Users/SSDrive/projects/media-tools
git add tools/stitch.mjs && git commit -m "tools: stitch — clip list → one video (clipsmith normalize/concat/duck salvage, timeline dropped)"
```

### Task 11: Archive clipsmith

**Files:**
- Create: `tools/workflows/ltx23-ia2v-flat.json` (from `clipsmith/tools/workflows/`)
- Move: `/Users/SSDrive/projects/mediaStudio/clipsmith` → `/Users/SSDrive/projects/mediaStudio/archive-clipsmith` *(mediaStudio has no `archive/` dir and is not a repo — a sibling rename keeps it findable without inventing structure)*
- Modify: `/Users/SSDrive/projects/mediaStudio/README.md` (its tables mention clipsmith)

- [ ] **Step 1: Salvage the workflow, archive the folder**

```bash
mkdir -p tools/workflows
cp /Users/SSDrive/projects/mediaStudio/clipsmith/tools/workflows/ltx23-ia2v-flat.json tools/workflows/
git add tools/workflows && git commit -m "workflows: LTX i2v graph salvaged from clipsmith (proven on bongpot render path)"
mv /Users/SSDrive/projects/mediaStudio/clipsmith /Users/SSDrive/projects/mediaStudio/archive-clipsmith
```

- [ ] **Step 2: Update the workspace README**

In `mediaStudio/README.md`, "Not repositories" section: change the `clipsmith/` bullet to
`- **archive-clipsmith/** — dead 2026-06-13 experiment; stitch core + LTX workflow salvaged into ~/projects/media-tools (2026-08-11); kept for its outputs/`.

**Phase 3 complete when:** stitch fixture test passes; clipsmith gone from the active workspace listing.

---

## Phase 4 — Discovery: SKILL.md, symlink, bible (spec §7.4)

### Task 12: `SKILL.md` + symlink

**Files:**
- Create: `SKILL.md` (repo root)
- Create: symlink `~/.claude/skills/media-tools` → `/Users/SSDrive/projects/media-tools`

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: media-tools
description: Use when creating, transcribing, styling, animating, or assembling any image, video, or audio media — image generation, image-to-video, video restyle, transcription, clip stitching, Vast GPU rental. One CLI per capability; compose them in scripts.
---

# media-tools — the toolbox

One repo of single-purpose media CLIs at `~/projects/media-tools/tools/`.
Rules: nothing runs implicitly — a tool needing a transcript takes
`--transcript`; styles resolve from `styles/<key>/style.json` via `--style`;
every tool's `--help` is its authoritative contract (read it before calling).
Compose tools in a job script (`jobs/<name>/run.sh`), one line per step, so
the human can read/edit/re-run it.

## Catalog

| tool | one job |
|---|---|
| `generate-image.mjs` | prompt (+ `--style`) → image (Replicate) |
| `image-to-video.mjs` | still + prompt → motion clip (seedance default) |
| `restyle-video.mjs` | clip + prompt/style → restyled clip (luma default) |
| `stylize-frames.py` | clip → deterministic styled frames (Blender; run via `blender -b -P`) |
| `transcribe.mjs` | audio/video file → diarized transcript.json (Deepgram nova-3, ALWAYS Deepgram) |
| `stitch.mjs` | clip-list file (+ music) → one normalized video (ffmpeg, no API) |
| `gpu-box.mjs` | rent / provision / kill a Vast.ai GPU box |

Styles live in `styles/` (currently: `inkwash`). Proven ComfyUI graphs in
`tools/workflows/`. Related standalone tool: `rectum` (URL → clip on disk)
lives at `~/projects/mediaStudio/rectum/`, invoked as its own CLI.

## Composition examples

Ink-wash still → motion clip:
    T=~/projects/media-tools/tools
    node $T/generate-image.mjs --style inkwash --prompt "storefront at dusk" --out stills/01.png
    node $T/image-to-video.mjs --image stills/01.png --prompt "gentle camera hold, mist drifts" --out clips/01.mp4

Transcript-driven work (ONLY when asked for a transcript):
    node $T/transcribe.mjs interview.mp3 --out transcript.json

Assemble:
    node $T/stitch.mjs --list shots.txt --music bed.mp3 --out final.mp4
```

- [ ] **Step 2: Symlink + verify + commit**

```bash
mkdir -p ~/.claude/skills && ln -sfn /Users/SSDrive/projects/media-tools ~/.claude/skills/media-tools
ls -la ~/.claude/skills/media-tools/SKILL.md    # resolves through the symlink
git add SKILL.md && git commit -m "skill: media-tools catalog — progressive-disclosure index over the tool CLIs"
```

*(Note: `restyle-video.mjs` appears in the catalog but lands in Task 14 — commit this task and Task 14 in the same working session so the catalog never ships describing a missing tool; or reorder locally, catalog last.)*

### Task 13: Bible section — "Agent-facing tool surfaces"

**Files:**
- Modify: `/Users/SSDrive/projects/bible/README.md` (append new §5.7 under Pipeline & Architecture Rules; add Appendix terms)

- [ ] **Step 1: Append §5.7**

```markdown
### 5.7 Agent-facing tool surfaces (Unix philosophy for agents)
When capabilities will be consumed by AI agents as well as humans:
- **Tools-first decomposition.** Each micro-capability is its own
  single-purpose CLI (one job, no "and"). A workflow/"lane" is a script
  that composes tools — never an owner of them. Nothing runs implicitly:
  a tool that needs a transcript takes `--transcript path`; it never
  invokes transcription itself.
- **The target architecture comes from the domain's atoms, not from the
  current repo shape.** Salvage discipline (§5.3) governs the migration
  PATH only — never the destination.
- **Three description layers:** `--help` is the per-tool contract (usage,
  every flag, one example, exit 0); one SKILL.md catalog is the discovery
  index (name + trigger description always in agent context; body loads
  on use — "progressive disclosure"); behavior lives ONLY in the CLIs.
- **Explicit I/O:** inputs by flag, outputs by `--out`, JSON on stdout,
  progress on stderr, meaningful exit codes. This is what makes tools
  composable in shell scripts by human and agent alike.
- **Names state what the thing does.** Verb-noun tools (`generate-image`),
  vendor names for vendor adapters (`_replicate`), plain nouns for data
  (`styles/`). Cleverness in names is a cost, not a feature.
```

- [ ] **Step 2: Appendix terms + commit (in the bible repo)**

Append to the Appendix list:
```markdown
- **Unix philosophy** — one tool, one job, compose in scripts; text streams as interface.
- **Progressive disclosure** — cheap index always present; full doc loads on demand (how agent skills work).
```

```bash
cd /Users/SSDrive/projects/bible && git add README.md && git commit -m "bible: 5.7 agent-facing tool surfaces — tools-first decomposition, help/skill layers (from media-tools consultation 2026-08-11)"
```

**Phase 4 complete when:** a fresh Claude session in a random directory, asked for a media task, reaches for the toolbox unprompted (manual check by Ryan next session).

---

## Phase 5 — Prove end-to-end: the Sheen ink-wash job (spec §7.5)

### Task 14: `tools/restyle-video.mjs`

**Files:**
- Create: `tools/restyle-video.mjs` (new tool; adapters verified live against the Replicate API 2026-08-11 — see `docs/` research in cutwork: `v2v-restyle-research.md` §2)

**Interfaces:**
- Consumes: `envKey` (`_env.mjs`), `predictModel`, `fetchBytes` (`_replicate.mjs`), `styles/<key>/style.json` (`.prompt` only).
- Produces: nothing consumed by other tools.

- [ ] **Step 1: Write the tool**

```js
// media-tools — restyle-video: clip + style prompt → restyled clip. One job.
// Adapters verified against the live Replicate schemas 2026-08-11:
//   luma/modify-video      — mode dial adhere_1..reimagine_3, ≤30s/100MB, first_frame anchor
//   wan-video/wan-2.7-videoedit — 2-10s, audio_setting origin keeps source audio
//   kwaivgi/kling-v3-omni-video — reference_video 3-10s + up to 4 reference_images
//
//   node restyle-video.mjs --video in.mp4 --out out.mp4 [--style inkwash | --prompt "..."]
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';
import { envKey, repoRoot } from './_env.mjs';
import { predictModel, fetchBytes } from './_replicate.mjs';

const HELP = `restyle-video — restyle an existing clip via a hosted v2v model

usage: node restyle-video.mjs --video in.mp4 --out out.mp4 [flags]

flags:
  --video PATH        (required) source clip (model limits: luma ≤30s/100MB, wan 2-10s)
  --out PATH          (required) output clip
  --style KEY         use styles/KEY/style.json prompt (default: inkwash)
  --prompt TEXT       extra/override prompt (appended after style; alone with --raw)
  --raw               no style; --prompt verbatim
  --model M           luma/modify-video (default) | wan-video/wan-2.7-videoedit | kwaivgi/kling-v3-omni-video
  --mode M            luma only: adhere_1..3 flex_1..3 reimagine_1..3 (default flex_2)
  --first-frame PATH  luma only: pre-styled frame 1 as the style anchor
  --keep-audio        wan only: audio_setting=origin

example:
  node ~/projects/media-tools/tools/restyle-video.mjs --video slice.mp4 \\
    --style inkwash --mode flex_2 --out slice-inkwash.mp4`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const video = flag('--video'); const out = flag('--out');
if (!video || !out) { console.error(HELP); process.exit(2); }
const raw = args.includes('--raw');
const styleKey = flag('--style', 'inkwash');
let stylePrompt = '';
if (!raw) {
  const p = join(repoRoot(), 'styles', styleKey, 'style.json');
  try { stylePrompt = JSON.parse(readFileSync(p, 'utf8')).prompt; }
  catch { console.error(`unknown --style '${styleKey}' (no ${p})`); process.exit(2); }
}
const prompt = [stylePrompt, flag('--prompt', '')].filter(Boolean).join(' ').trim();
if (!prompt) { console.error('need --style or --prompt'); process.exit(2); }
const model = flag('--model', 'luma/modify-video');
const tok = envKey('REPLICATE_API_TOKEN');

// Wan/luma fetch media server-side; data: URIs get opaque E002 (proven in
// image-to-video) — upload to Replicate files API first.
async function uploadFile(path, mime) {
  const body = new FormData();
  body.append('content', new Blob([readFileSync(path)], { type: mime }), basename(path));
  const r = await fetch('https://api.replicate.com/v1/files', {
    method: 'POST', headers: { Authorization: `Bearer ${tok}` }, body });
  const j = await r.json();
  if (!r.ok || !j?.urls?.get) throw new Error(`upload ${r.status}: ${JSON.stringify(j).slice(0, 300)}`);
  return j.urls.get;
}

const videoUrl = await uploadFile(video, 'video/mp4');
const MODELS = {
  'luma/modify-video': async () => ({
    video: videoUrl, prompt, mode: flag('--mode', 'flex_2'),
    ...(flag('--first-frame') ? { first_frame: await uploadFile(flag('--first-frame'), 'image/png') } : {}),
  }),
  'wan-video/wan-2.7-videoedit': async () => ({
    video: videoUrl, prompt, resolution: '1080p',
    ...(args.includes('--keep-audio') ? { audio_setting: 'origin' } : {}),
  }),
  'kwaivgi/kling-v3-omni-video': async () => ({
    prompt: `restyle <<<video_1>>>: ${prompt}`, reference_video: videoUrl, video_reference_type: 'base',
  }),
};
if (!MODELS[model]) { console.error(`unknown --model '${model}' (known: ${Object.keys(MODELS).join(', ')})`); process.exit(2); }
console.error(`restyle-video: ${model} → ${out}`);
const url = await predictModel(model, await MODELS[model](), { token: tok, label: 'restyle-video', interval: 5000, maxPolls: 360 });
const bytes = await fetchBytes(url);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);
console.log(JSON.stringify({ out, bytes: bytes.length, model }));
```

- [ ] **Step 2: Verify + commit**

```bash
node --check tools/restyle-video.mjs && node tools/restyle-video.mjs --help
git add tools/restyle-video.mjs && git commit -m "tools: restyle-video — luma/wan/kling v2v adapters (schemas verified 2026-08-11)"
```

### Task 15: `jobs/sheen-inkwash/run.sh` — the proof

**Blocker to clear first:** the source clip is on the unplugged BleSSD (or was never saved — last night's grabs targeted the absent drive). Ryan plugs BleSSD OR re-grabs the video via rectum (whose fallback now lands in `~/Movies/rectum-clips/` — commit that fix first if still uncommitted: `cd ~/projects/mediaStudio/rectum && git add -A && git commit -m "fix: clips_root falls back to ~/Movies/rectum-clips when BleSSD absent"`).

**Files:**
- Create: `jobs/sheen-inkwash/run.sh` (gitignored — jobs are scratch; the SCRIPT PATTERN is what's being proven)

- [ ] **Step 1: Write the job script** (`SRC` filled with the real clip path once located)

```zsh
#!/bin/zsh
# sheen-inkwash — 10s slice, two roads compared: generative restyle vs Blender treatment
set -euo pipefail
T=~/projects/media-tools/tools
SRC="<the sheen clip path>"          # ← fill when clip is on disk
cd "$(dirname "$0")"

ffmpeg -y -ss 10 -t 10 -i "$SRC" -c:v libx264 -crf 18 -an slice.mp4   # 10s test slice
node $T/restyle-video.mjs --video slice.mp4 --style inkwash --mode flex_2 --out road-a-luma.mp4
blender -b -P $T/stylize-frames.py -- slice.mp4 road-b-treatment.mp4
open road-a-luma.mp4 road-b-treatment.mp4                              # Ryan's eyes decide
```

- [ ] **Step 2: Run it, show both outputs, record the verdict**

Run the script (announce the luma call — real spend). `open` both. **Ryan's eyes are the verdict** (spec §7.5). Record the verdict + chosen road in `docs/specs/2026-08-11-media-tools-design.md` under a new "## 12. Phase-5 verdict" heading, commit.

- [ ] **Step 3: Tag the milestone**

```bash
cd /Users/SSDrive/projects/media-tools && git tag -a v0.1.0 -m "toolbox proven end-to-end: sheen ink-wash restyle approved"
```

**Phase 5 complete when:** Ryan approves a restyled clip and v0.1.0 is tagged.

---

## Self-review record

- Spec coverage: §3 tree → Tasks 1–14; §4 contract → Task 1 CLAUDE.md + every tool's HELP; §5 styles → Task 2 (fusion-theme explicitly deferred per §9); §6 skill → Task 12; §7 phases 1–5 → Tasks 1–15; bible addendum → Task 13. Phase 6+ (bongpot) is deliberately unplanned — lazy by spec.
- Known sequencing note: SKILL.md (Task 12) lists restyle-video which lands in Task 14 — flagged inline; execute 12 and 14 in the same session or swap order.
- cutwork re-point (Task 9) greps the real import graph rather than trusting a hardcoded file list.
