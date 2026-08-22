# HARNESS BRIEF — Scroll Animation Project (Wang Meng / Ge Hong)

*Drop this file in the repo root. First instruction to Claude Code: "Read HARNESS-BRIEF.md
in full. We are building the harness it describes, in the phase order given, one phase
per session. Do not skip ahead."*

---

## CONTEXT — why this exists (read before building anything)

This project animates Chinese ink-wash handscrolls (subtle leaf/water motion, layered
parallax, camera travel) for long-form video. Past sessions failed in known ways:

1. **Amnesia** — multi-day work across sessions loses hard-won knowledge.
2. **Satisficing** — vague goals produce the laziest passing output (the same
   side-to-side pan, minimal edits, premature "done").
3. **Scope blindness** — the scroll is too large to hold in one context; work must
   be per-scene.
4. **Unverifiable taste** — "looks natural" cannot be checked by code, so loops on
   aesthetics burn tokens converging on garbage.

The harness fixes these by one principle: **make wrong shapes unrepresentable.**
Knowledge lives in repo artifacts (never in session memory). "Done" is a mechanical
check (never self-assessment). Taste is decided by the human, once, from cheap
batched options (never iterated by the agent).

## ARCHITECTURE — the target state

- **Declarative scene manifest** (`scenes/*.yaml`, one per scene tile): regions with
  coordinates and masks, effect assignments (`leaf_sway`, `water_ripple`, `static`),
  per-effect parameters, camera keyframes. The renderer is a deterministic script
  reading the manifest. Sessions edit manifests or improve tools — never "animate
  the scroll" freeform.
- **Tool library** (`tools/`): parameterized effects, proxy renderer, optical-flow
  checker, contact-sheet generator, manifest linter, acceptance checker.
- **Rules** (`DIRECTION.md`): hard aesthetic constraints (no motion outside masks;
  camera paths must vary; restraint over spectacle).
- **State** (`PROGRESS.md`): current status + next step, updated at end of EVERY session.
- **Harness config** (`.claude/`): hooks, subagents, commands (built in Phase 2).

## PHASE 1 — Verification substrate (build first; everything depends on it)

1. **JSON Schema for the scene manifest.** Every field typed and bounded. Unknown
   effect names, out-of-bounds coordinates, missing masks = schema violations.
2. **`tools/lint_manifest.py`** — validates a manifest against the schema PLUS
   project rules that schema can't express: camera path must differ from the last
   3 rendered paths (read from render log); every animated region must reference
   an existing mask file; amplitude/frequency within DIRECTION.md bounds.
   Exit 0 clean / exit 2 with a one-line violation list.
3. **`tools/flow_check.py`** — runs OpenCV optical flow on a proxy render and asserts:
   zero flow outside declared masks; in-mask amplitude within bounds; dominant
   frequency in 0.5–2 Hz; first/last frame delta under seam threshold. Prints a
   compact stats report (this report gets fed back to sessions — keep it under
   ~20 lines).
4. **`tools/contact_sheet.py`** — given an effect + parameter ranges, renders an
   N×M grid of 2-second proxy loops tiled into one video/sheet for human review.
5. **`Makefile`** — `make lint`, `make proxy SCENE=x`, `make flowcheck SCENE=x`,
   `make sheet EFFECT=leaf_sway SCENE=x`. One command per operation, no incantations.

**Definition of done for EVERY Phase-1 tool: demonstrate it FAILING.** Write a
deliberately violating manifest / render and show the tool rejecting it. A check
that has never been seen to fail is decorative and does not count as complete.

## PHASE 2 — Claude Code harness wiring

1. **`.claude/settings.json` hooks:**
   - PostToolUse on Edit|Write of `scenes/*.yaml` → run `tools/lint_manifest.py`
     (exit 2 blocks and returns violations as instructions).
   - Stop hook → `tools/acceptance_check.py`: refuses session end unless the
     session's scene has a passing lint, a proxy render newer than the last
     manifest edit, a passing flow check, and an updated PROGRESS.md.
   - PreToolUse guard: block edits to `.claude/`, `tools/`, `DIRECTION.md`, and
     this file unless env var `HARNESS_OPEN=1` is set. Work sessions cannot
     loosen their own rules; harness changes are separate, human-reviewed sessions.
2. **`.claude/agents/evaluator.md`** — skeptical visual reviewer. Read-only tools
   (view frames/montages/flow heatmaps; NO edit, NO render). Prompt: "You have
   never seen this work before. Check the sampled frames and film-strip montage
   against DIRECTION.md. List every violation with frame numbers. You may not
   approve work you have not inspected. Style opinions are out of scope — flag
   rule violations only."
3. **`CLAUDE.md`** — SHORT index, not a novel: "Manifest spec: see schema/. Rules:
   DIRECTION.md. State: PROGRESS.md. Never edit scenes/ without running make lint.
   End every session by updating PROGRESS.md and committing."

**Recursion discipline (applies to building Phase 2 itself):** every hook is proven
by a demonstrated block — attempt the forbidden action, show the refusal. Harness
files are reviewed line-by-line by the human before merge.

## PHASE 3 — Loops and taste (only after 1–2 are proven)

1. **Ralph Wiggum outer loop** (`tools/loop.sh`): fresh headless session per
   iteration (`claude -p`, --max-turns capped), state via PROGRESS.md handoffs,
   terminated by acceptance_check — never by the model's opinion. Per-scene token
   budget; on exceed, halt and queue for human.
2. **Taste protocol — the loop NEVER iterates on aesthetics:**
   - Loop builds/tunes parameterized effects and renders CONTACT SHEETS.
   - Flow checks kill the physically wrong (free). Evaluator subagent kills the
     visibly broken (cheap: sampled frames + film-strip montage, one pass per
     candidate batch, not per iteration). Human picks from survivors (seconds).
   - The chosen parameters are committed to the manifest and never re-litigated.
3. **Cost routing:** grind iterations (adjust-render-check) on a cheaper model;
   frontier model reserved for new-tool development and the vision evaluator.
   Proxy resolution inside all loops; full-res render is a human-triggered final
   step only.

## PHASE 4 — SDK migration (LATER — do not start until the triggers fire)

Migrate the orchestration to the Claude Agent SDK (`pip install claude-agent-sdk`,
Python 3.10+) only when ANY of:
- loop.sh has grown conditional logic that is miserable in bash,
- we need mid-session control (inject flow reports between turns, halt on budget),
- the same glue exists in both pipeline code and hook scripts.

Migration notes for that day: `ClaudeSDKClient` (not `query()`) enables in-process
custom tools (@tool functions — renderer/linter/flow-check become callables) and
Python hook callbacks; PostToolUse can rewrite tool output before the model sees
it (compress render logs to the lines that matter); subagents become
AgentDefinition objects with restricted tool lists (evaluator: read-only, enforced
structurally); the SDK does NOT load filesystem settings by default — pass config
explicitly; pin the SDK version (option names have had breaking renames:
ClaudeCodeOptions → ClaudeAgentOptions).

The manifest, tools/, DIRECTION.md, and the taste protocol carry over unchanged —
the SDK replaces only the outer loop and hook plumbing. Build nothing in Phase 1–3
that assumes bash forever; build nothing that assumes the SDK either.

## STANDING RULES FOR ALL SESSIONS

- One scene, one task, one session. Small diffs. Commit at session end, always.
- Knowledge learned mid-session that future sessions need goes in a repo file
  (DIRECTION.md, a tool docstring, PROGRESS.md) before the session ends — or it
  is considered lost.
- When a check blocks you, fix the WORK, not the check. Checks change only in
  HARNESS_OPEN sessions with human review.
- "Done" claims require the acceptance check passing. No narrative completions.
- If a task is ambiguous enough that you're choosing the easiest interpretation,
  stop and ask instead.

## BUILD ORDER RECAP

Phase 1 (schema → linter → flow check → contact sheets → Makefile, each proven by
failure) → Phase 2 (hooks → guard → evaluator → CLAUDE.md, each proven by a
demonstrated block) → Phase 3 (loop + taste protocol + budgets) → Phase 4 (SDK,
triggers only). One phase item per session. Update PROGRESS.md as items complete.
