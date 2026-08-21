#!/usr/bin/env python3
"""Write a deferred-work bookmark into the knowledge store as a typed `open` claim. One job.

WHY THIS EXISTS (2026-08-20). Ryan, catching the sentence "the deeper merge is a
separate surgery I won't do mid-session":

  "don't forget about it, we need to be able to make bookmark notes. That's what
   computers are good for… You're more forgetful than me, and you're billions of
   times my storage capacity."

Deferring work is correct and constant -- scope discipline requires it. What
fails is the RECORD of the deferral, and it fails for one reason: at the moment
you defer, you are mid-task and writing a file feels like the interruption you
just decided not to take. So the friction has to be near zero, which is the only
thing this tool is for. One line, and the intention is in the store instead of
in a sentence in a transcript nobody will re-read.

It writes `kind: open` with `proven: false`, which is the type that means A PLAN,
NOT A SPEC -- so a later session inheriting it cannot mistake it for a
requirement. That distinction is load-bearing: a region catalogued "mist --
UNPROVEN, control-first" was inherited as a spec and built against, and there
was nothing there to animate.

Bookmarks surface in every session automatically, in the OPEN section of
`find-technique.py --brief`, which the SessionStart hook injects.

usage:
  knowledge-bookmark.py "short title" --why "what breaks if nobody does it"
                        [--where path/to/file.py:120] [--how "first concrete step"]
                        [--blocked-on "what has to be true first"]
                        [--id slug] [--dir knowledge]

  Print the open list instead:  knowledge-bookmark.py --list

example:
  knowledge-bookmark.py "merge the two region catalogues" \\
      --why "regions.json and living-polys.json both carry a class per region; \\
             the summit revert hit one and missed the other for a day" \\
      --where jobs/wang-meng/living/build-zone-living.py:193 \\
      --how "make living-polys.json the only region list; join params by class"
"""
import argparse, importlib.util, re, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("_ck", HERE / "check-knowledge.py")
_ck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ck)


def slug(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')[:48]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('title', nargs='*', default=[])
    p.add_argument('--why', default=None, help='what breaks if nobody does it')
    p.add_argument('--where', default=None, help='file:line where the work lands')
    p.add_argument('--how', default=None, help='first concrete step')
    p.add_argument('--blocked-on', default=None)
    p.add_argument('--id', default=None)
    p.add_argument('--dir', default=None)
    p.add_argument('--list', action='store_true', help='show the open bookmarks')
    a = p.parse_args()

    kdir = Path(a.dir) if a.dir else _ck.find_store()
    if not kdir.is_dir():
        sys.exit(f"no knowledge store at {kdir} — run knowledge-init.py first")

    if a.list or not a.title:
        n = 0
        for f in sorted(kdir.rglob('*.md')):
            m = _ck.FM.match(f.read_text())
            if not m:
                continue
            fm = _ck.parse_front(m.group(1))
            if fm.get('kind') == 'open' and fm.get('status') == 'live':
                n += 1
                print(f"? {fm.get('id')}   ({fm.get('verified-on','?')})")
                lines = [x.strip() for x in m.group(2).split('\n')]
                head = next((x[3:].strip() for x in lines if x.startswith('## ')),
                            next((x for x in lines if x and not x.startswith('**This is a PLAN')), ''))
                print(f"    {head[:110]}")
                why = next((x for x in lines if x.startswith('**Why it matters:**')), '')
                if why:
                    print(f"    why: {why[19:].strip()[:104]}")
        print(f"\n{n} open bookmark(s) in {kdir}", file=sys.stderr)
        return 0

    title = ' '.join(a.title)
    cid = a.id or slug(title)
    f = kdir / f'{cid}.md'
    if f.exists():
        sys.exit(f"{f} already exists — edit it, or pass a different --id")

    if not a.why:
        sys.exit("--why is required. A bookmark without a consequence is a wish, "
                 "and a later session has no way to judge whether to act on it.")

    body = ['**This is a PLAN, not a finding. `proven: false`. Do not build against it.**',
            '', f'## {title}', '', f'**Why it matters:** {a.why}']
    if a.where:
        body += ['', f'**Where it lands:** `{a.where}`']
    if a.how:
        body += ['', f'**First step:** {a.how}']
    if a.blocked_on:
        body += ['', f'**Blocked on:** {a.blocked_on}']
    body += ['', f'Bookmarked {date.today().isoformat()} at the moment of deferral, '
                 'because the record of a deferral is what fails, not the decision to defer.']

    # asked-as is REQUIRED on every claim, and a bookmark filed in one line will
    # never have it typed by hand -- so derive it. The title is how you would
    # search for the work; the id is how a cold session refers to it; --where
    # names the file someone will be looking at when they wonder about it.
    # Measured 2026-08-20: without this every new bookmark failed the type check
    # and was silently unlinked, i.e. the tool for not losing things lost them.
    aa = [title, cid.replace('-', ' ')]
    if a.where:
        aa.append(f"why is {Path(a.where.split(':')[0]).name} like this")
    if a.blocked_on:
        aa.append(f"what is blocking {title[:40]}")
    seen, uniq = set(), []
    for x in aa:
        k = x.lower().strip()
        if k and k not in seen:
            seen.add(k); uniq.append(x)
    while len(uniq) < 2:
        uniq.append(f"open item: {title}")

    f.write_text('---\n'
                 f'id: {cid}\n'
                 'kind: open\n'
                 f'conflict-key: should-we-{cid}\n'
                 'status: live\n'
                 'supersedes: []\n'
                 'proven: false\n'
                 f'verified-on: {date.today().isoformat()}\n'
                 'asked-as:\n' + ''.join(f'  - {x}\n' for x in uniq) +
                 '---\n\n' + '\n'.join(body) + '\n')

    import subprocess
    r = subprocess.run([sys.executable, str(HERE / 'check-knowledge.py'), '--dir', str(kdir)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        f.unlink()
        sys.exit('bookmark rejected by the type checker:\n' + r.stderr)
    print(f'{f}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
