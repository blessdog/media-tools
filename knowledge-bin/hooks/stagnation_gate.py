#!/usr/bin/env python3
"""PreToolUse gate: stop tuning one tool's knobs and re-choose the technique.

THE FAILURE THIS EXISTS TO STOP (2026-08-20). Six parameter passes were spent
inside animate-strokes on a subject it was the wrong tool for. Every pass moved
a number and changed an image, so every pass felt like progress. The right tool
was named one line further down a routing table nobody re-read.

That is textbook local search: tuning has a gradient, tool-choice does not, so
the search never leaves the basin it started in. Metaheuristics answer it with
STAGNATION DETECTION -- N iterations without improvement triggers diversification
or a cold restart -- and with a TABU LIST of moves already tried. This hook is
both: a counter, and an injection of the refuted list.

WHY IT INJECTS A FILE RATHER THAN ASKING THE MODEL TO RECONSIDER. Kamoi et al.
(TACL, "When Can LLMs Actually Correct Their Own Mistakes?") audit the
literature and conclude that no prior work shows successful self-correction from
prompted feedback alone, except where the feedback supplies information the
generator did not have. So "are you sure?" is measurably worthless. Each of
those six passes produced a SIGNAL (still wrong) and no INFORMATION, which is
exactly why the loop was stable. The gate's whole job is to be exogenous.

It prints the full live procedure set rather than querying it, because at this
catalog size retrieval selectivity is indistinguishable from chance, and because
preloading beats discretionary retrieval for trigger rate.

Fires once at the threshold and once at twice the threshold, never in a loop.

WHAT IT MUST NOT COUNT (learned 2026-08-20, four false positives in one turn).
The first version matched the tool's PATH anywhere in a bash command, so it
fired on `sed -n` reads, `cat >` writes, heredoc bodies mentioning the path, and
`git mv`. A gate that cries wolf gets bypassed, which is worse than no gate. So
an invocation counts only when all three hold:

  EXECUTED   an interpreter runs it, or it is invoked as ./path -- not merely
             named. Reading, editing, moving and grepping a tool are not passes.
  SUCCEEDED  the previous run did not error. Re-running after a traceback or a
             wrong cwd is a crash-fix loop, which HAS a gradient and does
             terminate; only knob changes on a working tool are the target.
  UNEDITED   the tool's own source was not written since. Authoring a tool is
             write-run-fix by nature and is not a parameter search.

It is deliberately project-agnostic: the store is found by walking up from the
session's cwd, so every project gets this the moment it has a knowledge/ dir.
"""
import json, os, re, subprocess, sys

THRESHOLD = 3
_here = os.path.dirname(os.path.abspath(__file__))
# vendored copy first, home store as fallback -- see the resolver note in
# the sibling .sh hooks. A gate that only runs on one machine is not a gate.
BIN = (os.path.join(_here, '..') if os.path.exists(os.path.join(_here, '..', 'check-knowledge.py'))
       else os.path.expanduser('~/.claude/knowledge/bin'))

# The tool must be RUN, not named. Either an interpreter precedes it, or it is
# invoked directly as a path. Anchored at a command position (start, or after
# a shell separator) so `cat > tools/x.py` and `sed -n 1,5p tools/x.py` miss.
SEP = r'(?:^|[;&|]|\&\&|\|\||\$\(|`)\s*'
INTERP = r'(?:python3?|node|bun|uv\s+run|deno\s+run)\s+(?:-\S+\s+)*'
TOOLPATH = r'(?P<tool>(?:[\w./-]*/)?(?P<base>[A-Za-z0-9_-]+\.(?:py|mjs|js)))'
EXEC_RE = re.compile(SEP + r'(?:' + INTERP + r'|\./)' + TOOLPATH, re.MULTILINE)


def blocks(entry):
    msg = entry.get('message') or {}
    c = msg.get('content')
    if isinstance(c, str):
        return [{'type': 'text', 'text': c}]
    return [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []


def is_human_turn(e):
    if e.get('type') != 'user':
        return False
    bs = blocks(e)
    return bool(bs) and all(b.get('type') == 'text' for b in bs)


def find_exec(cmd):
    """Basename of the tool this command RUNS, or None."""
    m = EXEC_RE.search(cmd)
    return m.group('base') if m else None


def flagset(cmd, tool):
    """The tool's OWN arguments, normalised — the thing a tuning pass changes.

    Counting whole command lines made every verify-after-edit look like a new
    pass: `python3 tools/check-knowledge.py` and
    `python3 tools/check-knowledge.py; python3 tools/check-retrieval.py` differ
    as strings and are the same run of the same tool with the same settings.
    A PARAMETER SEARCH changes the parameters. If the flags are identical, it is
    a re-run — which is what you do after fixing the input, and it terminates.
    """
    m = EXEC_RE.search(cmd)
    if not m:
        return ''
    tail = cmd[m.end():]
    # strip redirections FIRST: `2>&1` contains both & and |'s neighbours, and
    # splitting on them naively turned "…py 2>&1 | tail" into the flag set "2>".
    tail = re.sub(r'\d?>>?\s*&?\s*\S*', ' ', tail)
    tail = re.split(r'\|\||&&|[;|\n&]', tail)[0]
    return ' '.join(sorted(tail.split()))


STAGE_RE = re.compile(r'--(?:stage|step|phase|mode|subcommand|cmd)[= ]+([a-z0-9_-]+)')


def stage_of(cmd, tool):
    """Which OPERATION of a multi-stage tool this is, or '' if it has none.

    A pipeline tool like build-zone-living.py runs `--stage masks`, then
    `--stage cycle`, then `--stage register`. Those are three different
    operations in one documented route, not three steps of a knob search, and
    counting them together made the gate fire on correct sequential work
    (measured 2026-08-21, band 02: masks -> cycle -> register blocked at the
    third). Tuning means the SAME operation with different settings, so the
    count is partitioned by stage.
    """
    m = EXEC_RE.search(cmd)
    if not m or find_exec(cmd) != tool:
        return ''
    got = STAGE_RE.search(cmd[m.end():])
    return got.group(1) if got else ''


def writes_tool(cmd, tool):
    """True if this command AUTHORS the tool (redirect into it, or a python
    heredoc that opens it for writing). Authoring resets the tuning count, and
    is checked BEFORE execution, because one command routinely does both:
    write a fix, then run it to verify."""
    return bool(re.search(r'>\s*\S*' + re.escape(tool), cmd) or
                re.search(r"Path\(\s*['\"]\S*" + re.escape(tool), cmd))


def find_store(start):
    """Nearest knowledge/ dir walking up from cwd. Project-agnostic by design."""
    d = os.path.abspath(start or os.getcwd())
    while True:
        k = os.path.join(d, 'knowledge')
        if os.path.isdir(k):
            return k
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def result_failed(entries, use_id):
    """True if this tool_use's result came back as an error."""
    for e in entries:
        if e.get('type') != 'user':
            continue
        for b in blocks(e):
            if b.get('type') == 'tool_result' and b.get('tool_use_id') == use_id:
                if b.get('is_error'):
                    return True
                c = b.get('content')
                txt = c if isinstance(c, str) else ' '.join(
                    x.get('text', '') for x in c if isinstance(x, dict)) if isinstance(c, list) else ''
                return bool(re.search(r'Traceback \(most recent|No such file or directory|'
                                      r'command not found|unrecognized arguments|'
                                      r'error:|SyntaxError', txt))
    return False


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get('tool_name') != 'Bash':
        return 0
    cmd = (payload.get('tool_input') or {}).get('command') or ''
    tool = find_exec(cmd)
    if not tool:
        return 0

    tpath = payload.get('transcript_path')
    if not tpath or not os.path.exists(tpath):
        return 0
    entries = []
    with open(tpath, errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

    start = 0
    for i in range(len(entries) - 1, -1, -1):
        if is_human_turn(entries[i]):
            start = i + 1
            break

    seen = []
    for e in entries[start:]:
        if e.get('type') != 'assistant':
            continue
        for b in blocks(e):
            if b.get('type') != 'tool_use':
                continue
            # AUTHORING RESET: editing the tool's own source ends the search.
            if b.get('name') in ('Write', 'Edit', 'NotebookEdit'):
                fp = (b.get('input') or {}).get('file_path') or ''
                if os.path.basename(fp) == tool:
                    seen = []
                continue
            if b.get('name') != 'Bash':
                continue
            c = (b.get('input') or {}).get('command', '') if isinstance(b.get('input'), dict) else ''
            # AUTHORING RESET FIRST. A command may edit the tool AND run it in
            # one line (write a fix, verify it) -- checking exec first made that
            # count as a tuning pass, which is the opposite of what it is.
            if writes_tool(c, tool):
                seen = []
                continue
            if find_exec(c) != tool:
                continue
            if result_failed(entries, b.get('id')):
                continue          # crash-fix loop, not a knob search
            seen.append((stage_of(c, tool), flagset(c, tool)))

    # DIFFERENT SETTINGS only. Re-running with the same flags is a retry after
    # fixing something else; only a changed flag set is a step in a search.
    now_stage = stage_of(cmd, tool)
    now = (now_stage, flagset(cmd, tool))
    # only passes at the SAME stage are steps in the same search
    same = {f for (st, f) in seen if st == now_stage}
    distinct = len(same)
    n = distinct + (0 if now[1] in same else 1)
    if n not in (THRESHOLD, THRESHOLD * 2):
        return 0

    store = find_store(payload.get('cwd'))
    finder = os.path.join(BIN, 'find-technique.py')
    cat = None
    if store and os.path.exists(finder):
        try:
            cat = subprocess.run([sys.executable, finder, '--all', '--dir', store],
                                 capture_output=True, text=True, timeout=10).stdout
        except Exception:
            cat = None
    if not cat:
        return 0        # no store for this project: nothing exogenous to inject,
                        # and a bare "are you sure?" is measurably worthless.

    sys.stderr.write(
        f'\nSTAGNATION GATE — pass {n} of parameter tuning on {tool}, '
        f'this turn, with no verdict between them.\n\n'
        'Tuning has a gradient and tool-choice does not, so a parameter search '
        'never leaves the basin it starts in. Six passes on the wrong tool is '
        'what 2026-08-20 cost. Before another pass, answer these in one line each:\n\n'
        '  1. What would a PRACTITIONER OF THE CRAFT do? Name a technique, not a tool.\n'
        f'  2. What does {tool} say it is NOT for? Read its docstring header.\n'
        '  3. What does the store already say about this problem?\n\n'
        'This is not a request to think harder — it is the file you did not read:\n\n'
        + cat +
        '\nIf the technique is right and only the number is wrong, say so '
        'explicitly and continue.\n')
    return 2


if __name__ == '__main__':
    sys.exit(main())
