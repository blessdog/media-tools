---
id: gates-must-survive-a-clone
kind: verdict
conflict-key: how-do-project-gates-survive-leaving-this-machine
status: live
supersedes:
  - verdict-tier-1-hardening
scope: >
  Any repo whose correctness depends on hooks, checkers or generated files.
  Measured on media-tools and ~/.claude/knowledge, 2026-08-21. NOT a claim about
  Tier 2 or Tier 3 of the hardening audit, which remain unbuilt.
verified-on: 2026-08-21
evidence:
  - docs/reports/2026-08-20-hardening-the-knowledge-store.html
  - Makefile
  - knowledge-bin/VENDORED-FROM
asked-as:
  - how do I make the hooks work on another machine
  - the gates only run on my machine
  - how do I vendor the knowledge tools
  - what does make check run
  - do the hooks survive a clone
---

## A gate that runs in one place is a habit, not a gate

Ryan approved Tier 1 on 2026-08-21: *"hardenign looks good as far as i can tell
glancing over it."* Before it, every gate in every project was an absolute
symlink into `/Users/SSDrive/.claude/`, so a clone inherited nothing and the
username was in the git objects.

**What Tier 1 installed.** `knowledge-bin/` holds real copies of the store tools
and hooks; `tools/*.py` are RELATIVE symlinks into it; `.claude/settings.json`
wires the four hooks on `$CLAUDE_PROJECT_DIR` paths (project settings merge over
user settings, so the authoring machine keeps working); `make check` is the ONE
definition of passing, called by human, hook, pre-push gate and CI alike.

**Three failures found in the doing, all the same shape — something that LOOKS
installed but only works in one place.** This is the shape to hunt for:

1. **A vendored hook that still reaches into `$HOME` is not vendored.** All five
   copied hooks resolved their tools through `$HOME/.claude` and would have
   failed silently on any clone. Fix: resolve NEXT TO THIS FILE first, fall back
   to the home store. One identical file then works in both places — which is
   also what makes the drift check a plain `diff`.
2. **A hook in `.git/hooks` does not survive a clone.** Moved to a versioned
   `githooks/` wired by `core.hooksPath`.
3. **A checker run in the wrong directory checks nothing and exits 0.** The
   first pre-push hook printed `0 live claims · 0 unfindable` and called it a
   pass, because both checkers walk up looking for a PROJECT store and correctly
   refuse to treat the universal store's own home as one. `--dir` is now
   explicit, and there is a tripwire that BLOCKS on "checked zero claims".

**The tripwire generalises: a gate must fail when it cannot find its subject.**
Silence and success are indistinguishable otherwise, and the failure is
invisible precisely because the output looks green.

**Vendoring costs a second copy, so the copy is checked.** `make check-vendor`
diffs `knowledge-bin/` against `~/.claude/knowledge` and fails on drift; the
knowledge repo stays the single source of truth. Where the source is absent
(CI), it reports that drift was NOT checked rather than passing quietly — same
rule as the tripwire.

**Still open:** the CI workflow file could not be pushed — the `gh` OAuth token
lacks the `workflow` scope. One command from Ryan unblocks it:
`gh auth refresh -h github.com -s workflow`. Until then CI exists in the repo
but has never run. Tiers 2 and 3 remain unbuilt.
