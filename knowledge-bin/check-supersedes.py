#!/usr/bin/env python3
"""Does any LIVE claim still route through a RETIRED one? One job. Exit 1 if so.

    check-supersedes.py [--dir knowledge/] [--quiet]

WHY THIS EXISTS. `supersedes:` is a link BACKWARDS, and nothing walked it
forwards. Measured 2026-08-21: `leaf-marks-are-the-second-scale` was archived,
the superseding law was written, the flag was flipped in the job config and the
film was re-rendered -- and the live PROCEDURE `foliage-motion` still carried
`-> hinge-foliage --leaf-marks ... see leaf-marks-are-the-second-scale` in its
route. The store held the correction AND would still have handed the next
session the rejected technique.

It was caught by accident: an unrelated stagnation gate dumped every live
procedure in full and a human-shaped read spotted it. Two calls instead of three
and it would have survived. That is not a mechanism, so this is the mechanism.

TWO CHECKS.

  1. NAME. A live claim mentions an archived claim's id outside `supersedes:`.
     Exact, no false positives worth the name.

  2. RETIRED TOKEN. An archived claim may declare `retires:` -- the flags,
     tools or technique names its retirement kills. A live claim that
     RECOMMENDS one is a violation. Negated mentions are fine and expected:
     "do NOT pass --leaf-marks" is the corrected route, not a violation.

     `retires:` is DECLARED, never guessed. A first version inferred it by
     scraping `--flags` out of archived claims, and measurement killed it: the
     claim that caused the real bug contains ZERO flag tokens (it says "leaf
     marks" in prose), so the scrape missed the only case it existed for -- while
     flagging --field, --limbs and --mode, three flags that are still perfectly
     live and merely mentioned in passing. A heuristic that misses every true
     positive and produces only false ones is not a weak check, it is a broken
     one.

WHAT THIS IS NOT FOR: deciding whether a claim SHOULD be retired (that is a
verdict, and a person's), or checking that claims are findable (check-retrieval).
"""
import argparse, re, sys
from pathlib import Path

# NEGATION WORDS, and the list is load-bearing -- keep it narrow.
# 'without' was in here and broke control A: the buggy route read "see
# leaf-marks-are-the-second-scale, WITHOUT which a spray is one rigid blob",
# which is an ENDORSEMENT, and the checker read it as a retraction and went
# silent on the exact defect it was built for. A word that appears in
# recommending prose is not a negation, however negative it looks.
NEG = re.compile(r'\b(not|never|no longer|rejected?|avoid|retired|superseded|dead end)\b', re.I)
FLAG = re.compile(r'--[a-z][a-z0-9-]{2,}')
SKIP_FIELDS = {'supersedes', 'superseded-by', 'id'}

def split_front(text):
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    return (m.group(1), m.group(2)) if m else ('', text)

def field_of(front, key):
    """crude but sufficient: the lines belonging to one top-level YAML key"""
    out, grab = [], False
    for ln in front.split('\n'):
        if re.match(r'^[a-z-]+:', ln):
            grab = ln.split(':', 1)[0] == key
            if grab:
                out.append(ln.split(':', 1)[1])
            continue
        if grab:
            out.append(ln)
    return '\n'.join(out)

def negated_near(text, tok):
    """is every occurrence of tok inside a sentence that negates it?

    The window is the whole SENTENCE, both sides. Looking only backwards was
    wrong and the control proved it: the superseding law says "--leaf-marks stays
    as an off-by-default flag ... NOT for animating existing brushwork" -- the
    negation trails the token, and a backwards-only window called that a
    violation. A claim that names a retired thing in order to bury it is the
    correct state, not a defect.
    """
    for m in re.finditer(re.escape(tok), text):
        lo = text.rfind('.', 0, m.start()) + 1
        nl = text.rfind('\n\n', 0, m.start()) + 1
        lo = max(lo, nl, 0)
        end = text.find('.', m.end())
        hi = len(text) if end < 0 else end + 1
        if not NEG.search(text[lo:hi]):
            return False
    return True

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=None, help='the knowledge dir (default: walk up to find one)')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(argv)

    root = Path(a.dir) if a.dir else None
    if root is None:
        for c in [Path.cwd(), *Path.cwd().parents]:
            if (c / 'knowledge').is_dir():
                root = c / 'knowledge'; break
    if root is None or not root.is_dir():
        print('check-supersedes: no knowledge dir found', file=sys.stderr); return 0

    arch_dir = root / 'archive'
    archived = {}
    for f in sorted(arch_dir.glob('*.md')) if arch_dir.is_dir() else []:
        front, body = split_front(f.read_text())
        m = re.search(r'^id:\s*(\S+)', front, re.M)
        if m:
            # keep front and body SEPARATE. A first version stored them joined and
            # re-split later, which silently produced an empty frontmatter (no
            # closing ---) and made every `retires:` list read as empty. The
            # control caught it: the tool reported clean on a route that still
            # carried the retired flag.
            archived[m.group(1)] = (f, front, body)
    if not archived:
        if not a.quiet:
            print('check-supersedes: nothing archived; nothing to check')
        return 0

    # what each retirement DECLARES it kills -- never inferred
    tokens = {}
    for cid, (f, front, body) in archived.items():
        for raw in field_of(front, 'retires').split('\n'):
            t = raw.strip().lstrip('-').strip().strip('"\'')
            if t:
                tokens.setdefault(t, set()).add(cid)

    errs = []
    for f in sorted(root.glob('*.md')):
        text = f.read_text()
        front, body = split_front(text)
        if re.search(r'^status:\s*superseded', front, re.M):
            continue
        rel = f.name
        checkable = body + '\n' + '\n'.join(
            field_of(front, k) for k in ('route', 'applies-when', 'not-when', 'scope', 'mechanism'))

        for cid in archived:
            if cid in checkable and not negated_near(checkable, cid):
                errs.append((rel, 'names', f'{cid} — retired, and not named as retired'))

        route = field_of(front, 'route') + '\n' + body
        for tok, owners in tokens.items():
            if tok in route and not negated_near(route, tok):
                errs.append((rel, 'routes through', f'{tok} — retired by {", ".join(sorted(owners))}'))

    if errs:
        print(f'\ncheck-supersedes: {len(errs)} LIVE claim(s) still point at retired work\n', file=sys.stderr)
        for rel, kind, what in errs:
            print(f'  {rel}\n      {kind}: {what}', file=sys.stderr)
        print('\n  supersedes: is a link BACKWARDS. Retiring a claim is not finished until'
              '\n  every live claim that ROUTES through it has been re-read.\n', file=sys.stderr)
        return 1
    if not a.quiet:
        print(f'supersedes: {len(archived)} retired claim(s), no live claim routes through them')
    return 0

if __name__ == '__main__':
    sys.exit(main())
