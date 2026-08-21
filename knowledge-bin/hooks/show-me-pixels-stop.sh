#!/bin/bash
# SHOW ME PIXELS (law, 2026-08-20 — Ryan, after saying it "over and over and
# over" across sessions):
#
#   "I'm not a machine, I need pixels in front of my eyes. So if you say, hey,
#    take a look, put pixels up. Make that a rule. Make it more than a rule.
#    Make it a law."
#
# Naming a path is not showing. A file path in a message is a chore assigned to
# a human; `open` is the deliverable. This hook refuses to end a turn whose
# visible text names an image or video that was never put on screen.
#
# Written as a Stop hook rather than a note because the failure is a habit:
# every session drifts back to "it's at jobs/.../evidence-foo.png" because that
# costs the assistant nothing and costs him a file dive. Prose laws are read;
# gates are executed.

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
exec python3 "$KHOOKS/show_me_pixels.py"
