#!/bin/bash
# PostToolUse: type-check a knowledge store whenever one of its claim files is
# touched — in ANY project. Parse, don't validate: the check runs at WRITE time
# so everything downstream can assume a claim already has its required fields.
#
# Project-agnostic by design (2026-08-20). The first version matched only
# */media-tools/knowledge/* and called that repo's copy of the checker, which
# meant the whole mechanism existed for exactly one project. Ryan: "I need to
# know that the mechanism will be hard coded and will carry on no matter what
# project or what I decide to work on."

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
f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty' 2>/dev/null)
case "$f" in
  */knowledge/*.md) ;;
  *) exit 0 ;;
esac

# the store is the knowledge/ dir containing this file, whatever project it is in
store="${f%%/knowledge/*}/knowledge"
[ -d "$store" ] || exit 0

out=$(python3 "$KBIN/check-knowledge.py" --dir "$store" 2>&1) || {
  echo "$out" >&2
  exit 2
}
# TYPED IS NOT THE SAME AS FINDABLE. The two failures are independent: a claim
# can be perfectly typed, uniquely keyed, correctly retired -- and still
# invisible because nobody phrases the question the way the file is worded.
out=$(python3 "$KBIN/check-retrieval.py" --dir "$store" 2>&1) || {
  echo "$out" >&2
  exit 2
}
exit 0
