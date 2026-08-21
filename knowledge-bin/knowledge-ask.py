#!/usr/bin/env python3
"""Record a question awaiting a human's verdict, at the moment it is asked. One job.

WHY THIS EXISTS (2026-08-20). Ryan: "Trying to solve the shape of the problems,
not the specific problems." The instance was two pending verdicts about to be
lost to a compaction. The shape is bigger:

  AN UNANSWERED QUESTION IS A DEFERRAL WHOSE OWNER IS NOT THE AGENT.

`knowledge-bookmark.py` already covers work the agent deferred. This covers the
other half, and the two fail differently. Deferred WORK is recoverable — the
agent can always start it. A deferred QUESTION is not: the evidence scrolls out
of the terminal, the image closes, the conversation compacts, and what is lost
is not a task but a decision that was one sentence away from being made. The
next session then either re-derives the answer, guesses it, or silently builds
on the wrong branch.

So a pending verdict is its own type, and its required fields make an
unanswerable ask unwritable:

  question   what is actually being decided, in one sentence
  blocks     what cannot proceed until it is answered — the cost of the delay
  evidence   what the person must LOOK AT. Required, because a verdict without
             a rendered artefact is a request to imagine something, and those
             do not get answered. SessionStart names these so they can be
             reopened; the show-me-pixels law then forces them onto the screen.
  awaiting   WHO owns it. Refused if it is the agent — if the agent can settle
             it, it is not pending, it is unfinished work.

The point is the timing, not the file. Recorded when the question is ASKED, not
when the session ends, because the end of a session is when nobody has the
attention to do it. Same principle as the bookmark: the friction has to be near
zero at the exact moment it is least welcome.

usage:
  knowledge-ask.py "the question" --blocks "what waits on it"
                   --evidence path/to/thing.png [--evidence more.mp4]
                   [--awaiting Ryan] [--options "a | b | c"] [--id slug]

  knowledge-ask.py --list            what is still awaiting a person
  knowledge-ask.py --answer ID --verdict "what they decided"
                                     settle it: archives the pending claim so
                                     it stops being asked, and prints the stub
                                     of the real claim their answer justifies

example:
  knowledge-ask.py "which branch radius, and is 5 degrees the right stir?" \\
      --blocks "rolling the foliage rig out to the other six trees" \\
      --evidence jobs/wang-meng/living/evidence-attachment-pivot.png \\
      --options "r=3 | r=5 | r=7 | more stir | less stir"
"""
import argparse, importlib.util, re, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("_ck", HERE / "check-knowledge.py")
_ck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ck)


def slug(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')[:48]


def load(kdir):
    out = {}
    for f in sorted(kdir.rglob('*.md')):
        if f.name.upper() == 'README.MD':
            continue
        m = _ck.FM.match(f.read_text())
        if m:
            fm = _ck.parse_front(m.group(1))
            if fm.get('id'):
                out[fm['id']] = (fm, f, m.group(2))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('question', nargs='*', default=[])
    p.add_argument('--blocks', default=None)
    p.add_argument('--evidence', action='append', default=[])
    p.add_argument('--awaiting', default='Ryan')
    p.add_argument('--options', default=None, help='the choices, pipe-separated')
    p.add_argument('--id', default=None)
    p.add_argument('--dir', default=None)
    p.add_argument('--list', action='store_true')
    p.add_argument('--answer', default=None, metavar='ID')
    p.add_argument('--verdict', default=None)
    a = p.parse_args()

    kdir = Path(a.dir) if a.dir else _ck.find_store()
    if not kdir.is_dir():
        sys.exit(f'no knowledge store at {kdir} — run knowledge-init.py first')

    # ── settle one ───────────────────────────────────────────────────────────
    if a.answer:
        claims = load(kdir)
        if a.answer not in claims:
            sys.exit(f'no claim {a.answer!r} in {kdir}')
        if not a.verdict:
            sys.exit('--verdict is required: what did they actually decide?')
        fm, f, body = claims[a.answer]
        (kdir / 'archive').mkdir(exist_ok=True)
        txt = f.read_text().replace('status: live', 'status: superseded', 1)
        txt += (f'\n## Answered {date.today().isoformat()} by {fm.get("awaiting","?")}\n\n'
                f'> {a.verdict}\n')
        (kdir / 'archive' / f.name).write_text(txt)
        f.unlink()
        print(f'archived {a.answer}', file=sys.stderr)
        print(f'\nNow write the claim their answer justifies — the verdict itself is\n'
              f'not the knowledge, the RULE it establishes is:\n\n'
              f'  {kdir}/<new-id>.md   kind: verdict|law\n'
              f'  supersedes: [{a.answer}]\n', file=sys.stderr)
        return 0

    # ── list ─────────────────────────────────────────────────────────────────
    if a.list or not a.question:
        n = 0
        for cid, (fm, f, body) in sorted(load(kdir).items()):
            if fm.get('kind') != 'pending' or fm.get('status') != 'live':
                continue
            n += 1
            ev = fm.get('evidence') or []
            ev = [ev] if isinstance(ev, str) else ev
            print(f'⏳ {cid}   awaiting {fm.get("awaiting")}   since {fm.get("verified-on")}')
            print(f'    Q: {fm.get("question")}')
            print(f'    blocks: {fm.get("blocks")}')
            for e in ev:
                print(f'    LOOK AT: {e}')
        print(f'\n{n} question(s) awaiting a person in {kdir}', file=sys.stderr)
        return 0

    # ── record one ───────────────────────────────────────────────────────────
    q = ' '.join(a.question)
    if not a.blocks:
        sys.exit('--blocks is required: what cannot proceed until this is answered? '
                 'A question with no cost of delay is not pending, it is curiosity.')
    if not a.evidence:
        sys.exit('--evidence is required: what must they LOOK AT? A verdict asked '
                 'without a rendered artefact is a request to imagine something, '
                 'and those do not get answered.')
    missing = [e for e in a.evidence if not Path(e).exists()]
    if missing:
        sys.exit('evidence does not exist: ' + ', '.join(missing) +
                 '\nRender it before asking. See knowledge/evidence-lands-in-the-repo.')

    cid = a.id or ('verdict-' + slug(q))
    f = kdir / f'{cid}.md'
    if f.exists():
        sys.exit(f'{f} already exists — use --answer to settle it, or a different --id')

    front = ['---', f'id: {cid}', 'kind: pending',
             f'conflict-key: verdict-on-{slug(q)}', 'status: live', 'supersedes: []',
             f'question: >\n  {q}', f'blocks: >\n  {a.blocks}',
             f'awaiting: {a.awaiting}', f'verified-on: {date.today().isoformat()}',
             'evidence:'] + [f'  - {e}' for e in a.evidence] + \
            ['asked-as:', f'  - what is {a.awaiting} deciding',
             f'  - {q[:70]}', '  - pending verdict', '---']
    body = [f'**AWAITING {a.awaiting.upper()}. Do not guess this and do not build past it.**',
            '', f'## {q}', '', f'**Blocks:** {a.blocks}', '']
    if a.options:
        body += ['**The choices:**', ''] + \
                [f'- {o.strip()}' for o in a.options.split('|')] + ['']
    body += ['**Look at:**', ''] + [f'- `{e}`' for e in a.evidence] + ['',
             'Recorded at the moment the question was asked, because a question asked',
             'near the end of a session dies with the session — the evidence scrolls',
             'away, the window closes, the context compacts, and what is lost is a',
             'decision that was one sentence from being made.', '',
             f'Settle it with `knowledge-ask.py --answer {cid} --verdict "..."`, then',
             'write the claim the answer justifies. The verdict is not the knowledge;',
             'the rule it establishes is.']
    f.write_text('\n'.join(front) + '\n\n' + '\n'.join(body) + '\n')

    r = subprocess.run([sys.executable, str(HERE / 'check-knowledge.py'),
                        '--dir', str(kdir)], capture_output=True, text=True)
    if r.returncode != 0:
        f.unlink()
        sys.exit('rejected by the type checker:\n' + r.stderr)
    print(f'{f}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
