#!/bin/bash
# Stop tuning one tool's knobs and re-choose the technique.
# Stagnation detection + a tabu list, as a PreToolUse gate. See the python file.

# --- VENDORED RESOLVER (added 2026-08-21, Tier 1 hardening) ------------------
# A vendored hook that still reaches into $HOME is not vendored -- it works only
# on the author's machine, which is the exact failure this vendoring exists to
# fix. Resolve tools NEXT TO THIS FILE first, and fall back to the home store
# only when this copy is incomplete.
_KHERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ -f "$_KHERE/../check-knowledge.py" ]; then
  KBIN="$_KHERE/.."
  KHOOKS="$_KHERE"
else
  KBIN="$HOME/.claude/knowledge/bin"
  KHOOKS="$HOME/.claude/hooks"
fi
KUNIVERSAL="${KUNIVERSAL:-$KUNIVERSAL}"
# ----------------------------------------------------------------------------

set -u
exec python3 "$KHOOKS/stagnation_gate.py"
