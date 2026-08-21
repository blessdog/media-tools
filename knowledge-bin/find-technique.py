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
_ck = SourceFileLoader('_ck', str(Path(__file__).resolve().parent / 'check-knowledge.py')).load_module()

ap = argparse.ArgumentParser()
ap.add_argument('situation', nargs='*', default=[])
ap.add_argument('--dir', default=None, help='store dir (default: nearest knowledge/ above cwd)')
ap.add_argument('--top', type=int, default=3)
ap.add_argument('--all', action='store_true')
ap.add_argument('--no-universal', action='store_true',
                help='search only this project, not the cross-project laws')
ap.add_argument('--brief', action='store_true',
                help='one-line index of the whole store, for session injection')
a = ap.parse_args()

FM = _ck.FM
STOP = {'the','a','an','is','be','to','of','and','or','it','this','that','should',
        'make','i','we','for','on','in','at','with','how','do','does','can','my',
        'you','are','was','not','but','from','they','its','has','have','will',
        'when','what','why','where','which','one','two','all','any','use','used',
        'using','get','got','out','into','than','then','there','here','look',
        'looks','like','just','only','also','same','more','most','some','such',
        'per','via','see','new','old','way','ways'}

parse_front = _ck.parse_front

claims = []
KDIRS = [Path(a.dir)] if a.dir else _ck.stores(universal=not a.no_universal)
KDIR = KDIRS[0]
for kd in KDIRS:
  for f in sorted(kd.rglob('*.md')):
    if f.name.upper() == 'README.MD':
        continue
    m = FM.match(f.read_text())
    if not m:
        continue
    fm = parse_front(m.group(1)); fm['_file'] = str(f); fm['_body'] = m.group(2).strip()
    fm['_scope'] = 'universal' if kd == _ck.UNIVERSAL else kd.parent.name
    claims.append(fm)

live = [c for c in claims if c.get('status') == 'live']
procs = [c for c in live if c.get('kind') == 'procedure']
tabu  = [c for c in live if c.get('kind') == 'refuted']
# RANK EVERY KIND. Ranking only procedures made the store WRITE-MOSTLY:
# measured 2026-08-20, "where should a leaf card pivot" did not return the
# verdict written thirty minutes earlier answering exactly that, because a
# verdict is not a procedure. A law, a verdict and a refutation are all answers
# to a situation; only their SHAPE differs, which is what `kind` is for.
# OPEN items are searchable too. Excluding them looked principled -- a plan is
# not an answer -- but the open items ARE the bookmarks, and a bookmark you
# cannot find is not a bookmark. They come back clearly labelled "a plan, not a
# spec" so they cannot be mistaken for a verdict, which is what the type is for.
searchable = live

def toks(s): return {w for w in re.findall(r'[a-z]{3,}', (s or '').lower()) if w not in STOP}

q = toks(' '.join(a.situation))
# ---------------------------------------------------------------- BM25 ------
# Raw token overlap ranked a long claim above a short exact one, because a big
# body matches everything a little. Measured 2026-08-20: `camera-light-parallax`
# came back in the top 3 for "make the water move", "add a mist layer" and "how
# do I mask a whole tree". Two standard corrections, both from BM25:
#
#   IDF            a term in half the claims carries almost no information.
#                  "move" and "animate" are in nearly every claim here; "torch",
#                  "pivot" and "inpaint" are in one each. Weight by rarity.
#   LENGTH NORM    divide by document length so a long claim cannot win on bulk
#                  alone. b=0.75 is the usual setting; k1=1.2 saturates repeats,
#                  so mentioning a word nine times is not nine times the match.
#
# FIELDS ARE WEIGHTED, and `asked-as` weighs most, because it holds the words a
# PERSON would type rather than the words the file happens to use. That gap is
# the vocabulary problem (Furnas et al. 1987, p < 0.20 that two people pick the
# same term) and the only real fix is to index both vocabularies.
import math
K1, B = 1.2, 0.75
FIELDW = {'asked-as': 4.0, 'id': 3.0, 'conflict-key': 3.0,
          'applies-when': 2.0, 'scope': 2.0, 'mechanism': 2.0, 'route': 1.5,
          'sibling': 0.5, '_body': 1.0}

def field_toks(c, f):
    v = c.get(f)
    if isinstance(v, list):
        v = ' '.join(v)
    return re.findall(r'[a-z]{3,}', (v or '').lower())

def bag(c):
    """weighted term frequencies for one claim"""
    tf = {}
    for f, w in FIELDW.items():
        for t in field_toks(c, f):
            if t in STOP:
                continue
            tf[t] = tf.get(t, 0.0) + w
    return tf

BAGS = {c['id']: bag(c) for c in live if c.get('id')}
_N = max(1, len(BAGS))
_df = {}
for b in BAGS.values():
    for t in b:
        _df[t] = _df.get(t, 0) + 1
_avgdl = sum(sum(b.values()) for b in BAGS.values()) / _N or 1.0

def idf(t):
    n = _df.get(t, 0)
    return math.log(1 + (_N - n + 0.5) / (n + 0.5))

def score(c):
    b = BAGS.get(c.get('id'), {})
    dl = sum(b.values()) or 1.0
    s = 0.0
    for t in q:
        f = b.get(t, 0.0)
        if f:
            s += idf(t) * (f * (K1 + 1)) / (f + K1 * (1 - B + B * dl / _avgdl))
    # not-when is a REPULSOR: a claim that names your situation as out of scope
    # should sink, not float, and that is information the sibling needs.
    for t in q & set(x for x in field_toks(c, 'not-when') if x not in STOP):
        s -= 0.6 * idf(t)
    return round(s, 2)

W = 78
def rule(ch='─'): print(ch * W)

def first_line(c):
    """The claim's own statement, in one line.

    Prose first, heading second. A law states itself in its opening sentence
    ("A card with a soft edge is still a card") and its headings are commentary,
    so preferring '## Title' printed the commentary. A bookmark is the reverse:
    it opens with the same boilerplate disclaimer on every one, so there the
    heading is the only thing that identifies it.
    """
    DISCLAIM = ('**This is a PLAN',)
    body = (c.get('_body') or '').split('\n')
    for ln in body:
        t = ln.strip().lstrip('> ').strip()
        if t and not t.startswith('#') and not t.startswith(DISCLAIM):
            t = re.sub(r'\*\*|`|\*', '', t)
            return (t[:150].strip('"') + ('…' if len(t) > 150 else ''))
    for ln in body:
        if ln.strip().startswith('## '):
            return ln.strip()[3:].strip()
    return ''

if a.brief:
    # PROGRESSIVE DISCLOSURE: this index is cheap enough to sit in every session's
    # context; the bodies are one command away. A store nobody knows exists is a
    # store nobody queries, and discretionary retrieval is the failure mode.
    laws  = [c for c in live if c.get('kind') == 'law']
    verds = [c for c in live if c.get('kind') == 'verdict']
    opens = [c for c in live if c.get('kind') == 'open']
    nu = sum(1 for c in live if c.get('_scope') == 'universal')
    print(f'KNOWLEDGE — {len(live)} live claims: {len(live)-nu} from this project '
          f'({KDIR}), {nu} universal (~/.claude/knowledge/store)')
    print('Query before choosing any technique:  '
          'python3 ~/.claude/knowledge/bin/find-technique.py "<your situation>"')
    if laws:
        print('\nLAWS — absolute, no exceptions')
        for c in laws:
            print(f'  · {c["id"]}: {first_line(c)}')
    if procs:
        print('\nPROCEDURES — the routes that are currently believed')
        for c in procs:
            print(f'  · {c["id"]:<22} answers {c.get("conflict-key","")}'
                  f'   (sibling: {c.get("sibling","—")})')
    if verds:
        print('\nVERDICTS — measured, and SCOPED; check the scope before reusing')
        for c in verds:
            print(f'  · {c["id"]:<22} {c.get("scope","")[:90]}')
    if tabu:
        print('\nREFUTED — already tried, do NOT retry')
        for c in tabu:
            print(f'  ✗ {c["id"]:<22} {(c.get("mechanism") or "")[:100]}')
    if opens:
        print('\nOPEN — plans, NOT specs. proven: false. Do not build against these.')
        for c in opens:
            print(f'  ? {c["id"]:<22} {first_line(c)[:90]}')
    raise SystemExit(0)

if a.all or not q:
    ranked = [(0, c) for c in procs]
else:
    ranked = sorted(((score(c), c) for c in searchable),
                    key=lambda t: -t[0])[:max(a.top, 3)]
    # A zero score is not a weak answer, it is NO answer. Printing it in the
    # same shape as a hit makes an unrelated claim read as advice -- measured
    # 2026-08-21: "how to make bread" returned two laws at score 0.0.
    ranked = [(s, c) for s, c in ranked if s > 0]
    if not ranked:
        rule('═')
        print(f'  TECHNIQUE  ·  {" ".join(a.situation)}')
        rule('═')
        print('\n  NO CLAIM ANSWERS THIS. Not one word of the question matches any')
        print('  live claim. Either the question is genuinely new -- then the answer')
        print('  you find belongs in the store -- or it is phrased in words no claim')
        print('  declares in `asked-as`. Try --brief to read the index by eye.')
        raise SystemExit(0)

rule('═')
print(f'  TECHNIQUE  ·  {" ".join(a.situation) or "all live procedures"}')
print('  top-3 always. rank 1 alone is how 2026-08-20 happened.')
rule('═')
KINDLINE = {'law': '⛔ LAW — absolute, no exceptions',
            'verdict': '📐 VERDICT — true ONLY inside its scope',
            'refuted': '✗ REFUTED — already paid for, do not retry',
            'procedure': '→ PROCEDURE — a route that is currently believed',
            'open': '? OPEN — a plan, not a spec'}
def show(k, v):
    if v:
        print(f'   {k:<10} {v}')
for i, (s, c) in enumerate(ranked, 1):
    sc = c.get('_scope', '')
    tag = '  ⟨universal⟩' if sc == 'universal' else f'  ⟨{sc}⟩'
    print(f'\n{i}. {c.get("id")}    [score {s}]{tag}   answers: {c.get("conflict-key")}')
    print(f'   {KINDLINE.get(c.get("kind"), c.get("kind"))}')
    show('USE WHEN', c.get('applies-when'))
    show('ONLY FOR', c.get('scope'))
    show('BECAUSE', c.get('mechanism'))
    show('NOT WHEN', c.get('not-when'))
    show('ROUTE', c.get('route'))
    if c.get('kind') == 'law':
        show('SAYS', first_line(c))
    show('EVIDENCE', ', '.join(c['evidence']) if isinstance(c.get('evidence'), list) else c.get('evidence'))
    if c.get('sibling'):
        print(f'   {"SIBLING":<10} {c["sibling"]}  ← the confusable one. Read it before choosing.')
if tabu:
    print()
    rule()
    print('  ALREADY REFUTED — do not retry these')
    rule()
    for c in tabu:
        print(f'\n  ✗ {c.get("id")}  ({c.get("conflict-key")})')
        print(f'    {c.get("mechanism","")}')
print()
