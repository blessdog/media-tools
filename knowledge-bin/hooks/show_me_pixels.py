#!/usr/bin/env python3
"""Stop hook: every visual named in the turn's visible text must be on screen.

Ryan, 2026-08-20: "I'm not a machine, I need pixels in front of my eyes. So if
you say, hey, take a look, put pixels up. Make that a rule. Make it more than a
rule. Make it a law." He had said it, by his own count, over and over across
sessions -- so it stops being a preference and becomes a gate.

What counts as SHOWING: `open` (or qlmanage -p / imgcat / a viewer) run on the
file, in this turn. What does not count: naming the path, printing the path,
committing the file, or reading it into the assistant's own context. Read shows
the picture to the model, not to the human -- that distinction is the whole
point of this file.

Scope is deliberately narrow so the gate is honest rather than noisy:
  - only text the human actually sees (assistant text blocks), never thinking,
    never tool input, never commit messages;
  - only this turn (everything after the last real human message);
  - only image/video extensions.
Exit 2 with the list of unshown files; the assistant then opens them and
finishes.
"""
import json
import os
import re
import sys

VISUAL = r"\.(?:png|jpe?g|gif|webp|bmp|tiff?|mp4|mov|m4v|webm|avi|mkv)"
PATH_RE = re.compile(r"[^\s`'\"()\[\]<>*]+" + VISUAL, re.IGNORECASE)
# Commands that put a file in front of a human on this machine.
# MULTILINE: a Bash tool call is usually a script, so the show command lives
# at the start of its own LINE, not at the start of the string. Without the
# flag this missed every `open` that followed a heredoc and blocked a turn
# that had in fact put the file on screen (2026-08-20, first false positive).
SHOW_RE = re.compile(r"(?:^|[;&|]\s*|\$\(\s*)(open|qlmanage|imgcat|catimg|vlc|mpv|ffplay|iina)\b",
                     re.MULTILINE)


def blocks(entry):
    msg = entry.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def is_human_turn(entry):
    """A real prompt from Ryan, not a tool result being replayed as a user msg."""
    if entry.get("type") != "user":
        return False
    bs = blocks(entry)
    if not bs:
        return False
    return all(b.get("type") == "text" for b in bs)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("stop_hook_active"):
        return 0                      # already blocked once this stop; let it go
    tpath = payload.get("transcript_path")
    if not tpath or not os.path.exists(tpath):
        return 0

    entries = []
    with open(tpath, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue

    start = 0
    for i in range(len(entries) - 1, -1, -1):
        if is_human_turn(entries[i]):
            start = i + 1
            break

    named, shown = {}, set()
    for e in entries[start:]:
        if e.get("type") != "assistant":
            continue
        for b in blocks(e):
            t = b.get("type")
            if t == "text":
                for m in PATH_RE.findall(b.get("text") or ""):
                    named[os.path.basename(m.rstrip(".,;:"))] = m.rstrip(".,;:")
            elif t == "tool_use":
                cmd = ""
                if b.get("name") == "Bash":
                    inp = b.get("input")
                    if isinstance(inp, dict):
                        cmd = inp.get("command") or ""
                if cmd and SHOW_RE.search(cmd):
                    for m in PATH_RE.findall(cmd):
                        shown.add(os.path.basename(m.rstrip(".,;:")))

    missing = [named[k] for k in named if k not in shown]
    if not missing:
        return 0

    listed = "\n  ".join(sorted(missing)[:8])
    extra = "" if len(missing) <= 8 else f"\n  ... and {len(missing) - 8} more"
    sys.stderr.write(
        "SHOW ME PIXELS (law, 2026-08-20). Your message names visuals that are "
        "not on Ryan's screen:\n  " + listed + extra + "\n"
        "He said it over and over across sessions: \"I'm not a machine, I need "
        "pixels in front of my eyes. If you say, hey, take a look, put pixels "
        "up.\"\nA path is a chore you handed him. Run `open <file>` on each one "
        "(or drop it from the message if he does not actually need to see it), "
        "then finish.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
