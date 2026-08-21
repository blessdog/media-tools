#!/usr/bin/env python3
"""Check that every claim is FINDABLE by the questions it exists to answer. One job.

WHY THIS EXISTS (2026-08-20). Ryan, an hour after the store was built:

  "Where is the system we implemented today that's going to allow us to find the
   information in the markdown? That looks an awful lot like the same system
   we've been using and not the one we've spent half the day upgrading."

He was right and the store was WRITE-MOSTLY. `find-technique.py` ranked only
`kind: procedure`, so a verdict written thirty minutes earlier — literally
titled "where does a foliage card pivot" — did not come back for the query
"where should a leaf card pivot". Everything written that day was in the store
and none of it was reachable. A store you can only write to is a diary.

Typing the claims fixed the CONFLICT problem (one live answer per question).
It did nothing for the RETRIEVAL problem, and the two are independent: a claim
can be perfectly typed, correctly retired, uniquely keyed, and still invisible
because nobody phrases the question the way the file is worded. That is the
vocabulary problem (Furnas, Landauer, Gomez & Dumais, CACM 1987): the
probability that two people choose the same term for the same thing is under
0.20. Writing the claim and writing the query are two people.

So a claim declares `asked-as:` — the questions a person would actually TYPE
when they need it, in their words, not the file's. This tool asserts each one
returns its own claim in the top N. Retrieval stops being a hope and becomes a
property with a test, and adding a claim means stating how you will look for it.

usage:
  check-retrieval.py [--dir DIR] [--top 3] [--require-asked-as] [--json]

  --require-asked-as   fail claims that declare no questions at all (default:
                       report them as UNTESTED but do not fail)

exit 0 = every declared question finds its claim; exit 1 = a claim is unfindable.
"""
import argparse, importlib.util, json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("_ck", HERE / "check-knowledge.py")
_ck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ck)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dir', default=None)
    p.add_argument('--top', type=int, default=3)
    p.add_argument('--require-asked-as', action='store_true')
    p.add_argument('--json', action='store_true')
    a = p.parse_args()

    kdir = Path(a.dir) if a.dir else _ck.find_store()
    claims = {}
    for f in sorted(kdir.rglob('*.md')):
        if f.name.upper() == 'README.MD':
            continue
        m = _ck.FM.match(f.read_text())
        if not m:
            continue
        fm = _ck.parse_front(m.group(1))
        if fm.get('id') and fm.get('status') == 'live':
            claims[fm['id']] = fm

    fails, untested, tested = [], [], 0
    for cid, fm in sorted(claims.items()):
        qs = fm.get('asked-as') or []
        if isinstance(qs, str):
            qs = [qs]
        if not qs:
            untested.append(cid)
            continue
        for q in qs:
            r = subprocess.run([sys.executable, str(HERE / 'find-technique.py'), q,
                                '--dir', str(kdir), '--top', str(a.top)],
                               capture_output=True, text=True)
            hits = [m.group(1) for m in
                    (re.match(r'^\s*\d+\.\s+(\S+)\s+\[score', ln)
                     for ln in r.stdout.split('\n')) if m]
            tested += 1
            if cid not in hits[:a.top]:
                fails.append({'claim': cid, 'question': q,
                              'got': hits[:a.top] or ['(nothing)']})

    if a.json:
        print(json.dumps({'store': str(kdir), 'claims': len(claims),
                          'questions': tested, 'unfindable': fails,
                          'untested': untested}, indent=2))
    else:
        for f in fails:
            print(f"  UNFINDABLE  {f['claim']}", file=sys.stderr)
            print(f"      asked as: {f['question']!r}", file=sys.stderr)
            print(f"      returned: {', '.join(f['got'])}", file=sys.stderr)
        if untested:
            print(f"  UNTESTED ({len(untested)}): no `asked-as:` on "
                  f"{', '.join(untested)}", file=sys.stderr)
            print("      A claim with no stated question is a claim nobody will "
                  "phrase correctly by accident.", file=sys.stderr)
        print(f"{len(claims)} live claims · {tested} questions · "
              f"{len(fails)} unfindable · {len(untested)} untested", file=sys.stderr)

    return 1 if (fails or (a.require_asked_as and untested)) else 0


if __name__ == '__main__':
    sys.exit(main())
