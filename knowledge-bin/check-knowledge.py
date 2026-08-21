#!/usr/bin/env python3
"""Parse and type-check the knowledge store. One job. Exits nonzero on violation.

WHY THIS EXISTS (2026-08-20). Every line of a markdown file has type `string`.
A law, a measured verdict, a refuted hypothesis and somebody's Tuesday guess
are the same type, so nothing can tell them apart and nothing can check them.
Three failures in one week came from exactly that:

  a verdict lost its scope    a canopy detector proven on ONE part of a picture
                              was applied 2000px away, where it claimed a whole
                              mountainside
  a plan became a spec        a region catalogued "UNPROVEN, control-first" was
                              inherited by a later session and built against as
                              a requirement; there was nothing there to animate
  a dead belief stayed live   "the summits hold perfectly still" was recorded as
                              an open defect. It was the painting being correct.

The fix is a TAGGED UNION: a claim is one of a fixed set of shapes, and each
shape demands different fields. A verdict cannot be written without a scope; a
refutation cannot be written without a mechanism; a plan is structurally marked
as unproven. The illegal states are not rejected, they are unwritable.

  Claim = law       { text }
        | verdict   { text, scope, evidence }
        | refuted   { text, mechanism }
        | procedure { text, applies-when, not-when, route, sibling }
        | open      { text, proven: false }

AND A COLLECTOR. Measured (TEPA, arXiv 2608.07429): under a reversal, append-only
memory scores 0.210 and NO MEMORY AT ALL scores 0.309 -- an append-only store is
worse than amnesia, because amnesia fails honestly and a stale note fails
persuasively. Explicit revocation scores 0.950. So every entry carries a
`conflict-key` naming the question it answers, and THIS TOOL REFUSES more than
one live entry per key. Superseding means moving the old file to archive/ and
naming it in `supersedes:` -- git keeps the audit trail for free.

Liveness here is reachability, not age: an archived entry is still readable, it
just cannot be reached by a query.

usage:
  check-knowledge.py [--dir knowledge] [--json]

exit 0 = the store type-checks; exit 1 = violations, printed with file and field.
"""
import argparse, json, os, re, sys
from pathlib import Path


UNIVERSAL = Path.home() / '.claude/knowledge/store'


def stores(start=None, universal=True):
    """Every store a query should search: the project's, then the universal one.

    A new project starts with an EMPTY store and would re-learn every
    cross-project lesson from scratch -- which is the failure this whole
    mechanism exists to stop, reappearing one level up. So laws that are about
    engineering rather than about this subject live in ~/.claude/knowledge/store
    and are searched from every project, forever.

    Order matters: the project's own store is more specific and is listed first,
    which is also the tie-break when two claims score equally.
    """
    out = []
    p = find_store(start)
    if p.is_dir():
        out.append(p)
    if universal and UNIVERSAL.is_dir() and UNIVERSAL.resolve() not in [x.resolve() for x in out]:
        out.append(UNIVERSAL)
    return out or [p]


def find_store(start=None):
    """Nearest knowledge/ dir walking up from cwd.

    The store is PER PROJECT and the tools are GLOBAL, so a tool can never
    default to a path next to itself -- that resolved to the installer's own
    directory the moment these moved out of media-tools/tools/.
    """
    d = Path(start or os.getcwd()).resolve()
    for cand in [d, *d.parents]:
        k = cand / 'knowledge'
        # ~/.claude/knowledge is the HOME of the universal store, never a
        # project. Walking up from inside it found it as both, and every
        # universal law then failed its own conflict-key check (22 false
        # violations, measured 2026-08-21 with cwd inside ~/.claude/knowledge).
        if k.is_dir() and k.resolve() != UNIVERSAL.parent.resolve():
            return k
    return d / 'knowledge'

KINDS = {
    'law':       (),
    'verdict':   ('scope', 'evidence'),
    'refuted':   ('mechanism',),
    'procedure': ('applies-when', 'not-when', 'route', 'sibling'),
    'open':      ('proven',),
    # PENDING: the work is DONE and a human has to look. Structurally different
    # from `open`, which means the work is not done -- different remedy, and
    # crucially a different OWNER. Recorded at the moment the question is asked,
    # because a question asked at the end of a session dies with the session.
    # `evidence` is required: you may not ask for a verdict without naming what
    # the person has to look at, which is what makes it answerable later.
    'pending':   ('question', 'blocks', 'evidence', 'awaiting'),
}
ALWAYS = ('id', 'kind', 'conflict-key', 'status', 'asked-as')
# asked-as: the questions a PERSON would type to find this, in their words.
# Required since 2026-08-20, when the store turned out to be write-mostly --
# 44 real questions, 44 of which returned the wrong claim or nothing. A claim
# with no stated question is a claim nobody will phrase correctly by accident,
# and the vocabulary problem (Furnas et al. 1987) says the odds are under 0.20.
# check-retrieval.py asserts each one actually returns its own claim.
STATUS = {'live', 'superseded'}


FM = re.compile(r'\A---\n(.*?)\n---\n(.*)\Z', re.S)

def parse_scalar(v):
    v = v.strip()
    if v in ('true', 'false'):
        return v == 'true'
    if v.startswith('[') and v.endswith(']'):
        inner = v[1:-1].strip()
        return [x.strip().strip('"\'') for x in inner.split(',')] if inner else []
    return v.strip('"\'')

def parse_front(text):
    """A deliberately small YAML subset: key: scalar, key: >-block, key: - list.

    No yaml dependency, because the checker must run in a git hook on any
    machine, and the store is ours -- we control the shape it is written in.
    """
    out, key, buf, mode = {}, None, [], None
    for raw in text.split('\n'):
        if mode == 'block':
            if raw.startswith('  ') or not raw.strip():
                buf.append(raw.strip()); continue
            out[key] = ' '.join(x for x in buf if x).strip(); key, buf, mode = None, [], None
        if mode == 'list':
            if raw.strip().startswith('- '):
                buf.append(raw.strip()[2:].strip()); continue
            out[key] = buf; key, buf, mode = None, [], None
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        m = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', raw)
        if not m:
            continue
        k, v = m.group(1), m.group(2)
        if v.strip() in ('>', '|', '>-', '|-'):
            key, buf, mode = k, [], 'block'
        elif v.strip() == '':
            key, buf, mode = k, [], 'list'
        else:
            out[k] = parse_scalar(v)
    if mode == 'block' and key:
        out[key] = ' '.join(x for x in buf if x).strip()
    if mode == 'list' and key:
        out[key] = buf
    return out

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=None, help='store dir (default: nearest knowledge/ above cwd)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    root = Path(a.dir) if a.dir else find_store()

    errors, claims = [], []
    files = sorted(root.rglob('*.md'))
    for f in files:
        if f.name.upper() == 'README.MD':
            continue
        rel = f.relative_to(root.parent)
        m = FM.match(f.read_text())
        if not m:
            errors.append((rel, '—', 'no YAML frontmatter; every claim must be typed'))
            continue
        fm, body = parse_front(m.group(1)), m.group(2).strip()
        fm['_file'], fm['_archived'] = str(rel), ('archive' in f.parts)
        claims.append(fm)

        for k in ALWAYS:
            if not fm.get(k):
                errors.append((rel, k, 'required on every claim'))
        kind = fm.get('kind')
        if kind and kind not in KINDS:
            errors.append((rel, 'kind', f'not one of {"|".join(KINDS)}'))
        elif kind:
            for k in KINDS[kind]:
                if fm.get(k) in (None, '', []):
                    errors.append((rel, k, f'REQUIRED for kind: {kind} — '
                                           f'a {kind} without {k} is the bug this store exists to stop'))
        if fm.get('status') and fm['status'] not in STATUS:
            errors.append((rel, 'status', f'not one of {"|".join(sorted(STATUS))}'))
        if kind == 'pending' and fm.get('awaiting', '').strip().lower() in ('', 'claude', 'me', 'agent'):
            errors.append((rel, 'awaiting', 'a pending verdict is owned by a PERSON — '
                                            'if the agent can settle it, it is not pending, '
                                            'it is unfinished work'))
        if kind == 'open' and fm.get('proven') is not False:
            errors.append((rel, 'proven', 'an open item is a PLAN: proven must be false'))
        if fm.get('status') == 'superseded' and not fm.get('_archived'):
            errors.append((rel, 'status', 'superseded claims live in knowledge/archive/'))
        if fm.get('_archived') and fm.get('status') != 'superseded':
            errors.append((rel, 'status', 'a claim in archive/ must be status: superseded'))
        _ = 0
        aa = fm.get('asked-as')
        if isinstance(aa, str) or (isinstance(aa, list) and len(aa) < 2):
            errors.append((rel, 'asked-as', 'give at least TWO phrasings — one person '
                                            'writing both the claim and its only query '
                                            'is exactly the vocabulary problem'))
        if not body:
            errors.append((rel, 'body', 'the RAW trace goes here — agents condition on raw '
                                        'experience and disregard condensed experience'))

    # ── the collector: at most one live claim per conflict key ───────────────────
    # ACROSS BOTH STORES. A project claim that shadows a universal law is not a
    # local override, it is two live answers to one question -- exactly what the
    # conflict-key exists to prevent, reappearing one level up. If a project
    # genuinely disagrees with a cross-project law, that disagreement should be
    # visible and resolved, not silently shadowed by search order.
    if root.resolve() != UNIVERSAL.resolve() and UNIVERSAL.is_dir():
        for uf in sorted(UNIVERSAL.rglob('*.md')):
            if uf.name.upper() == 'README.MD':
                continue
            um = FM.match(uf.read_text())
            if not um:
                continue
            ufm = parse_front(um.group(1))
            ufm['_file'] = f'~/.claude/knowledge/store/{uf.name}'
            ufm['_archived'] = 'archive' in uf.parts
            ufm['_universal'] = True
            claims.append(ufm)

    live = {}
    for c in claims:
        if c.get('status') != 'live':
            continue
        live.setdefault(c.get('conflict-key'), []).append(c)
    for key, group in sorted(live.items()):
        if len(group) > 1:
            for c in group:
                errors.append((c['_file'], 'conflict-key',
                               f'{len(group)} LIVE claims answer "{key}" — '
                               'duplicate entries put the wrong sibling in the top 3 about '
                               '69% of the time. Retire all but one to archive/.'))

    ids = {c.get('id') for c in claims}
    for c in claims:
        for s in (c.get('supersedes') or []):
            if s not in ids:
                errors.append((c['_file'], 'supersedes', f'names "{s}", which is not in the store'))

    if a.json:
        print(json.dumps({'files': len(files), 'claims': len(claims),
                          'live': sum(len(g) for g in live.values()),
                          'keys': len(live), 'errors': [list(e) for e in errors]}, indent=1))
    else:
        for f, field, msg in errors:
            print(f'{f}\n    {field}: {msg}', file=sys.stderr)
        print(f'\n{len(claims)} claims · {sum(len(g) for g in live.values())} live '
              f'across {len(live)} conflict keys · {len(errors)} violations',
              file=sys.stderr)

    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
