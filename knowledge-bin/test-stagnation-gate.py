#!/usr/bin/env python3
"""Regression test for the stagnation gate's command classifier. One job.

Every case here is a command that actually appeared in a session. The four
marked FALSE POSITIVE all fired the first version of the gate within a single
turn, on the day it was written -- reads, writes, heredoc bodies and a git mv.
A gate that fires on those gets bypassed, and a bypassed gate is worse than
none, so the classifier is pinned by a test rather than by care.

usage: test-stagnation-gate.py       (exit 0 = all cases classify correctly)
"""
import importlib.util, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "_gate", Path.home() / ".claude/hooks/stagnation_gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

CASES = [
    # (command, expected basename or None, why)
    ("python3 tools/check-routing.py --config regions.json",
     "check-routing.py", "plain execution"),
    ("cd /Users/SSDrive/projects/media-tools && python3 tools/animate-strokes.py --wobble 8",
     "animate-strokes.py", "execution after cd"),
    ("./tools/hinge-foliage.py --swing 15",
     "hinge-foliage.py", "direct invocation"),
    ("python3 /abs/path/tools/check-knowledge.py --dir knowledge",
     "check-knowledge.py", "absolute path"),
    ("ls tools/ | head && python3 tools/find-technique.py 'leaves'",
     "find-technique.py", "execution in a pipeline"),

    # ---- the four that wrongly fired, 2026-08-20 ----
    ("sed -n '46,65p' tools/check-knowledge.py",
     None, "FALSE POSITIVE: reading a tool is not running it"),
    ("cat > tools/check-routing.py <<'PYEOF'\nimport sys\nPYEOF",
     None, "FALSE POSITIVE: authoring a tool is not running it"),
    ("git mv tools/check-knowledge.py ~/.claude/knowledge/bin/check-knowledge.py",
     None, "FALSE POSITIVE: moving a tool is not running it"),
    ("python3 - <<'PYEOF'\nfrom pathlib import Path\np = Path('tools/check-routing.py')\nPYEOF",
     None, "FALSE POSITIVE: a heredoc body naming the path is not running it"),

    # ---- other shapes that must not fire ----
    ("grep -n 'add_argument' tools/hinge-foliage.py",
     None, "grep is a read"),
    ("chmod +x tools/check-routing.py",
     None, "chmod is not execution"),
    ("ls -l tools/animate-strokes.py",
     None, "ls is not execution"),
    ("echo 'run python3 tools/foo.py later'",
     None, "a quoted mention inside echo is not a command position"),
]

# writes_tool() is the other half: a command may edit the tool AND run it, and
# authoring must win. find_exec correctly reports the execution; the reset is
# what stops it counting as a tuning pass.
WRITE_CASES = [
    ("cd ~/x && python3 - <<'PYEOF'\np = Path('find-technique.py')\nPYEOF\n"
     "python3 tools/find-technique.py --brief", "find-technique.py", True,
     "edit-then-verify in ONE command is authoring"),
    ("cat > tools/check-routing.py <<'EOF'\nx\nEOF", "check-routing.py", True,
     "a redirect into the tool is authoring"),
    ("python3 tools/animate-strokes.py --wobble 8", "animate-strokes.py", False,
     "a plain run is not authoring"),
    ("python3 tools/hinge-foliage.py --out drawings/hinge-foliage.py.log",
     "hinge-foliage.py", False,
     "a FLAG naming the tool is not a redirect into it — this is a run"),
    ("python3 tools/hinge-foliage.py --swing 15 > /tmp/hinge-foliage.py.log",
     "hinge-foliage.py", True,
     "conservative: a redirect whose target merely contains the name still resets, "
     "because under-firing is the cheaper error"),
]

# flagset(): a tuning pass changes the tool's own FLAGS. Two commands that run
# the tool identically are one pass however different the surrounding line is.
FLAG_CASES = [
    ("python3 tools/check-knowledge.py", "python3 tools/check-knowledge.py; python3 tools/x.py",
     "check-knowledge.py", True, "trailing second command is not a new setting"),
    ("cd /repo && python3 tools/check-knowledge.py", "python3 tools/check-knowledge.py 2>&1 | tail -3",
     "check-knowledge.py", True, "cd prefix and a pipe are not new settings"),
    ("python3 tools/hinge-foliage.py --swing 6", "python3 tools/hinge-foliage.py --swing 10",
     "hinge-foliage.py", False, "a CHANGED FLAG VALUE is a real tuning pass"),
    ("python3 tools/hinge-foliage.py --swing 6 --flutter 0.1",
     "python3 tools/hinge-foliage.py --flutter 0.1 --swing 6",
     "hinge-foliage.py", True, "flag ORDER is not a new setting"),
]
# STAGE CASES. A multi-stage tool runs different OPERATIONS, not a knob search.
# Measured 2026-08-21: masks -> cycle -> register on build-zone-living.py fired
# the gate at the third call, blocking correct sequential work. Tuning is the
# SAME stage with different settings; a changed stage is a different operation.
STAGE_CASES = [
    ("python3 jobs/x/build-zone-living.py --zone z1 --stage masks",
     "build-zone-living.py", "masks", "the stage is the operation"),
    ("python3 jobs/x/build-zone-living.py --zone z1 --stage cycle --classes foliage",
     "build-zone-living.py", "cycle", "stage survives other flags"),
    ("python3 jobs/x/build-zone-living.py --zone z1 --stage register",
     "build-zone-living.py", "register", "third stage of the documented route"),
    ("python3 tools/hinge-foliage.py --swing 6",
     "hinge-foliage.py", "", "a single-operation tool has no stage"),
    ("python3 tools/animate-strokes.py --mode lift --field wave",
     "animate-strokes.py", "lift", "--mode names an operation too"),
]

fails = []
for cmd, tool, want, why in STAGE_CASES:
    got = gate.stage_of(cmd, tool)
    if got != want:
        fails.append((cmd[:60], want, got, why))
# and the property that matters: three DIFFERENT stages must not look like one search
_st = [gate.stage_of(c, "build-zone-living.py") for c, t, w, y in STAGE_CASES[:3]]
if len(set(_st)) != 3:
    fails.append(("masks/cycle/register", "3 distinct stages", len(set(_st)),
                  "sequential stages must partition, or the gate blocks a pipeline"))

for a_, b_, tool, same, why in FLAG_CASES:
    got = (gate.flagset(a_, tool) == gate.flagset(b_, tool))
    if got != same:
        fails.append((a_[:60], same, got, why))
for cmd, tool, want, why in WRITE_CASES:
    got = gate.writes_tool(cmd, tool)
    if got != want:
        fails.append((cmd.split(chr(10))[0][:64], want, got, why))
for cmd, want, why in CASES:
    got = gate.find_exec(cmd)
    if got != want:
        fails.append((cmd.split('\n')[0][:64], want, got, why))

for c, want, got, why in fails:
    print(f"FAIL  {c!r}\n      want={want} got={got}  ({why})", file=sys.stderr)
n = len(CASES) + len(WRITE_CASES) + len(FLAG_CASES) + len(STAGE_CASES) + 1
print(f"{n - len(fails)}/{n} cases classify correctly", file=sys.stderr)
sys.exit(1 if fails else 0)
