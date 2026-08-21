#!/bin/bash
# Stop: regenerate STATE.md so it cannot be stale, in ANY project that has a
# knowledge store. Silent and exit 0 everywhere else.
#
# WHY A HOOK (2026-08-20). The old STATE.md carried the instruction "update this
# file at every milestone and before every session end" — and it drifted anyway,
# to 896 append-only lines with two of its own laws re-derived at real cost. A
# status file is a cache of the repository with no invalidation; asking a person
# (or an agent) to invalidate it by hand is the part that fails. So it is rebuilt
# from the repo at the end of every turn, and hand edits are destroyed, which is
# the only way a generated file stays generated.

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
GEN="$KBIN/state-report.py"
[ -f "$GEN" ] || exit 0

d=$(pwd -P); store=""
while [ "$d" != "/" ]; do
  if [ -d "$d/knowledge" ] && [ -n "$(ls "$d/knowledge"/*.md 2>/dev/null)" ]; then
    store="$d/knowledge"; break
  fi
  d=$(dirname "$d")
done
[ -n "$store" ] || exit 0
root=$(dirname "$store")

# Where does STATE.md live? Honour an existing one anywhere in the tree before
# inventing a new location — a project that already has one has already decided.
existing=$(find "$root" -maxdepth 4 -name STATE.md -not -path "*/node_modules/*" \
             -not -path "*/.git/*" 2>/dev/null | head -1)
out="${existing:-$root/STATE.md}"

python3 "$GEN" --dir "$store" --out "$out" >/dev/null 2>&1 || exit 0
exit 0
