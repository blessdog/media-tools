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
import argparse, json, re, sys
from pathlib import Path

KINDS = {
    'law':       (),
    'verdict':   ('scope', 'evidence'),
    'refuted':   ('mechanism',),
    'procedure': ('applies-when', 'not-when', 'route', 'sibling'),
    'open':      ('proven',),
}
ALWAYS = ('id', 'kind', 'conflict-key', 'status')
STATUS = {'live', 'superseded'}

ap = argparse.ArgumentParser()
ap.add_argument('--dir', default=str(Path(__file__).resolve().parents[1] / 'knowledge'))
ap.add_argument('--json', action='store_true')
a = ap.parse_args()
root = Path(a.dir)

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
    if kind == 'open' and fm.get('proven') is not False:
        errors.append((rel, 'proven', 'an open item is a PLAN: proven must be false'))
    if fm.get('status') == 'superseded' and not fm.get('_archived'):
        errors.append((rel, 'status', 'superseded claims live in knowledge/archive/'))
    if fm.get('_archived') and fm.get('status') != 'superseded':
        errors.append((rel, 'status', 'a claim in archive/ must be status: superseded'))
    if not body:
        errors.append((rel, 'body', 'the RAW trace goes here — agents condition on raw '
                                    'experience and disregard condensed experience'))

# ── the collector: at most one live claim per conflict key ───────────────────
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
sys.exit(1 if errors else 0)
