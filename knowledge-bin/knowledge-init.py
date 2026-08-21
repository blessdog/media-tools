#!/usr/bin/env python3
"""Create a typed knowledge store in a project that does not have one. One job.

WHY A BOOTSTRAP AND NOT A README (2026-08-20). The store only works if it is
present before the first discovery is made, because the failure it prevents is
a discovery being written somewhere untyped and unqueryable. Ryan has years of
projects that predate it: "a lot of this is gonna end up in every project I've
done up until now." A convention does not retrofit; a command does.

It writes the directory, the README that states the type system, and a first
claim seeded from whatever the project already asserts (CLAUDE.md's laws), so
the store is never an empty folder nobody adds to.

WHAT IT IS NOT FOR. Migrating prose. It cannot read a STATE.md and know which
paragraph is a law and which is a Tuesday guess -- that judgement is the whole
point of the type system, and it is a human-or-agent call made one claim at a
time. This tool makes the place for them to go.

usage:
  knowledge-init.py [--project DIR] [--force]

  --project  where to create knowledge/ (default: cwd, or its git root)
  --force    write even if the directory already exists (never overwrites claims)
"""
import argparse, subprocess, sys
from pathlib import Path

README = '''# knowledge/

The project's **typed claims**. One file per claim, frontmatter is the type.

Why this exists: markdown notes gave every statement the type `string`, so a
law, a measured verdict, a refuted hypothesis and somebody's guess were
indistinguishable, and nothing could check or retire any of them. Discoveries
were re-derived session after session, and worse, dead beliefs kept being acted
on. Measured (TEPA, arXiv 2608.07429): under a reversal, append-only memory
scores 0.210 and NO MEMORY AT ALL scores 0.309 — an append-only store is worse
than amnesia, because amnesia fails honestly and a stale note fails
persuasively. Explicit revocation scores 0.950.

## The type

    Claim = law       { text }
          | verdict   { text, scope, evidence }
          | refuted   { text, mechanism }
          | procedure { text, applies-when, not-when, route, sibling }
          | open      { text, proven: false }

Every claim also carries `id`, `kind`, `conflict-key`, `status`, and
**`asked-as`** — at least two questions a PERSON would actually type to find it,
in their words rather than the file's. That gap is the vocabulary problem
(Furnas, Landauer, Gomez & Dumais, CACM 1987: under 0.20 that two people pick
the same term for the same thing), and one person writing both the claim and its
only query is exactly the trap. `check-retrieval.py` asserts every declared
question returns its own claim in the top 3, so findability is a tested property
rather than a hope — measured on the day it was added, 44 of 44 real questions
returned the wrong claim or nothing.

- **law** — absolute, no exceptions. Usually the user's own words.
- **verdict** — measured, and only true inside `scope`. A verdict proven on one
  part of a problem is a *hypothesis* about the rest of it.
- **refuted** — a dead end someone already paid for. `mechanism` says WHY, so
  the lesson transfers instead of just the outcome.
- **procedure** — a route that is currently believed. `sibling` names the
  confusable one, because the classic failure is picking the neighbour.
- **open** — a plan. `proven: false` is mandatory. Do not build against it.

## The collector

`conflict-key` names the QUESTION a claim answers, and **at most one live claim
may answer each question**. Superseding means moving the old file to `archive/`,
setting `status: superseded`, and naming it in the new claim's `supersedes:`.
Git keeps the audit trail for free. Liveness here is reachability, not age: an
archived claim is still readable, it just cannot be reached by a query.

## Tools (global, work in any project)

    ~/.claude/knowledge/bin/check-knowledge.py            # type-check the store
    ~/.claude/knowledge/bin/find-technique.py "<situation>"  # query it
    ~/.claude/knowledge/bin/find-technique.py --brief     # the one-line index
    ~/.claude/knowledge/bin/check-routing.py --config X   # pipeline configs must
                                                          # name a LIVE claim id
    ~/.claude/knowledge/bin/check-retrieval.py            # is every claim findable
    ~/.claude/knowledge/bin/knowledge-bookmark.py "..."   # record a deferral NOW
    ~/.claude/knowledge/bin/state-report.py               # regenerate STATE.md

A PostToolUse hook type-checks AND retrieval-tests this directory on every
write; a SessionStart hook puts the index into every session's context; a Stop
hook regenerates STATE.md.

## Three layers, and only one is typed by hand

| layer | what it holds | where | who writes it |
|---|---|---|---|
| **CLAIM** | a rule, a measurement, a dead end, a route | `knowledge/` | you, typed |
| **NARRATIVE** | what was tried and what happened | `docs/journal/`, commits | you, as a story |
| **STATUS** | what exists right now | `STATE.md` | GENERATED from the repo |

`status.sh` in this directory is an executable that prints whatever THIS project
counts; `state-report.py` runs it and inlines the output. Hand edits to
`STATE.md` are destroyed on the next run — a status file written by hand is a
cache of the repository with no invalidation.
'''

SEED = '''---
id: {pid}-store-exists
kind: open
conflict-key: what-does-this-project-know
status: live
supersedes: []
proven: false
verified-on: {date}
asked-as:
  - what does this project know
  - is there a knowledge store here
---

**This is a PLAN, not a finding. Do not build against it.**

The store was created on {date} and is empty. Nothing here has been measured
yet.

Delete this file once the first real claim lands. It exists so the directory is
never an empty folder that nobody adds to — the failure mode this whole
mechanism is aimed at is a discovery going somewhere untyped, and an empty
store invites exactly that.

First things worth writing down, in rough order of how expensive they are to
re-derive:

1. Any **law** the user has stated in their own words. Quote them.
2. Any **refuted** approach already tried in this project — with the MECHANISM,
   not just the outcome.
3. The **procedures** that currently work, each naming its confusable sibling.
'''


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project', default=None)
    p.add_argument('--force', action='store_true')
    a = p.parse_args()

    root = Path(a.project).resolve() if a.project else Path.cwd().resolve()
    if not a.project:
        try:
            root = Path(subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                                       capture_output=True, text=True, cwd=root,
                                       check=True).stdout.strip())
        except Exception:
            pass

    store = root / 'knowledge'
    if store.exists() and not a.force:
        print(f'{store} already exists (use --force to add missing files)', file=sys.stderr)
        return 1

    from datetime import date
    (store / 'archive').mkdir(parents=True, exist_ok=True)
    wrote = []
    status = '''#!/usr/bin/env bash
# What THIS project counts. Run from the repo root by state-report.py and
# inlined into STATE.md, so the status section is MEASURED, not remembered.
# Generic tool, specific project: print built artefacts, passing tests, live
# endpoints -- whatever tells you where the work actually stands.
set -u
echo "  (nothing measured yet -- edit knowledge/status.sh)"
'''
    for rel, text in (('README.md', README), ('status.sh', status),
                      (f'_seed.md', SEED.format(pid=root.name.lower().replace(' ', '-'),
                                                date=date.today().isoformat()))):
        f = store / rel
        if f.exists():
            continue
        f.write_text(text)
        if f.name == 'status.sh':
            f.chmod(0o755)
        wrote.append(str(f.relative_to(root)))

    print(f'{store}', file=sys.stderr)
    for w in wrote:
        print(f'  + {w}', file=sys.stderr)
    if not wrote:
        print('  (nothing to write — all files present)', file=sys.stderr)
    print('\nNext: write the project\'s LAWS first (the user\'s own words), then the\n'
          'REFUTED list. Verify with check-knowledge.py, query with find-technique.py.',
          file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
