#!/usr/bin/env python3
"""Answer "which technique does this situation want?" from the knowledge store. One job.

It does not run anything, choose anything, or edit anything. It prints the live
`procedure` claims ranked against a situation, plus the `refuted` claims for the
same area -- the tabu list, so an approach already ruled out is not retried.

WHY IT RANKS THE WAY IT DOES. Two people spontaneously choose the same term for
the same thing with probability under 0.20 (Furnas, Landauer, Gomez & Dumais,
CACM 1987). So keyword overlap alone is how "the leaves should stir" beat "a
branch should swing" and cost half a day. The mitigations here are deliberately
not embeddings -- at this catalog size retrieval selectivity is indistinguishable
from chance, and the real fix is catalog hygiene:

  * ALWAYS print the top-3, never the top-1. Stopping at the first match is the
    failure mode itself.
  * Score `applies-when` and `not-when` as well as the id, because applicability
    -- not topical similarity -- is what decides whether a procedure fits.
  * A hit on a claim's `not-when` SUBTRACTS. Being described by the exclusion is
    evidence against.
  * Print each claim's `sibling`, always, so the nearest confusable entry is on
    screen even when it did not rank.

usage:
  find-technique.py "make the leaves move" [--dir knowledge] [--top 3]
  find-technique.py --all
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib.machinery import SourceFileLoader
_ck = SourceFileLoader('_ck', str(Path(__file__).resolve().parent / 'check-knowledge.py'))

ap = argparse.ArgumentParser()
ap.add_argument('situation', nargs='*', default=[])
ap.add_argument('--dir', default=str(Path(__file__).resolve().parents[1] / 'knowledge'))
ap.add_argument('--top', type=int, default=3)
ap.add_argument('--all', action='store_true')
a = ap.parse_args()

FM = re.compile(r'\A---\n(.*?)\n---\n(.*)\Z', re.S)
STOP = {'the','a','an','is','be','to','of','and','or','it','this','that','should','make','i','we'}

def parse_front(text):
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
            out[k] = v.strip().strip('"\'')
    if mode == 'block' and key: out[key] = ' '.join(x for x in buf if x).strip()
    if mode == 'list' and key:  out[key] = buf
    return out

claims = []
for f in sorted(Path(a.dir).rglob('*.md')):
    if f.name.upper() == 'README.MD':
        continue
    m = FM.match(f.read_text())
    if not m:
        continue
    fm = parse_front(m.group(1)); fm['_file'] = str(f); fm['_body'] = m.group(2).strip()
    claims.append(fm)

live = [c for c in claims if c.get('status') == 'live']
procs = [c for c in live if c.get('kind') == 'procedure']
tabu  = [c for c in live if c.get('kind') == 'refuted']

def toks(s): return {w for w in re.findall(r'[a-z]{3,}', (s or '').lower()) if w not in STOP}

q = toks(' '.join(a.situation))
def score(c):
    pos = len(q & (toks(c.get('id')) | toks(c.get('applies-when')) | toks(c.get('conflict-key'))))
    neg = len(q & toks(c.get('not-when')))
    return pos - neg

W = 78
def rule(ch='─'): print(ch * W)

if a.all or not q:
    ranked = [(0, c) for c in procs]
else:
    ranked = sorted(((score(c), c) for c in procs), key=lambda t: -t[0])[:max(a.top, 3)]

rule('═')
print(f'  TECHNIQUE  ·  {" ".join(a.situation) or "all live procedures"}')
print('  top-3 always. rank 1 alone is how 2026-08-20 happened.')
rule('═')
for i, (s, c) in enumerate(ranked, 1):
    print(f'\n{i}. {c.get("id")}    [score {s}]   answers: {c.get("conflict-key")}')
    print(f'   USE WHEN   {c.get("applies-when","")}')
    print(f'   NOT WHEN   {c.get("not-when","")}')
    print(f'   ROUTE      {c.get("route","")}')
    print(f'   SIBLING    {c.get("sibling","—")}  ← the confusable one. Read it before choosing.')
if tabu:
    print()
    rule()
    print('  ALREADY REFUTED — do not retry these')
    rule()
    for c in tabu:
        print(f'\n  ✗ {c.get("id")}  ({c.get("conflict-key")})')
        print(f'    {c.get("mechanism","")}')
print()
