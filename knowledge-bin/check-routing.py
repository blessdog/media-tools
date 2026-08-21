#!/usr/bin/env python3
"""Check that every technique a pipeline config routes to is a LIVE procedure. One job.

WHY THIS EXISTS (2026-08-20). The knowledge store type-checks itself
(check-knowledge.py) and can be queried (find-technique.py), and neither of
those can stop a build. Measured the same day it was written: `knowledge/`
correctly recorded `foliage-motion-by-displacement` as SUPERSEDED, while all 14
foliage regions in jobs/wang-meng were still rendering through it, because the
technique was not data anywhere -- build-zone-living.py had one hardcoded
subprocess call and no branch to take. A store that cannot fail a build is
documentation, and documentation is the thing that already did not work.

So a pipeline config names its technique BY CLAIM ID, and the claim id is a
foreign key into the store. Exact lookup, no prose matching:

  classes: { sway: { technique: "foliage-motion", ... } }
                                 |
                                 +-> knowledge/foliage-motion.md
                                     kind: procedure   <- must be routable
                                     status: live      <- must not be retired

A retired technique is then not a note somebody should have read. It is a
missing key, and the build stops.

The reverse direction matters as much. `--implements` takes the list of
techniques the builder can actually run (have the builder print it, so the two
never drift), and a technique nobody implements is as broken as one nobody
believes.

usage:
  check-routing.py --config regions.json [--knowledge DIR] [--implements JSON] [--json]

  --config      pipeline config with {"classes": {...}, "regions": [...]}
  --regions     ANOTHER file whose entries carry a `class`; repeatable. Use it
                for every catalogue a pipeline reads, not just the documented
                one -- measured 2026-08-20: a decision was reverted in the
                catalogue a human reads and stayed live for a day in the one
                the builder reads, 13 regions of it.
  --knowledge   the store (default: <repo>/knowledge)
  --implements  file or '-' holding a JSON list of technique ids the builder runs
                (e.g.  build-zone-living.py --techniques | check-routing.py ... --implements -)

exit 0 = every route resolves to a live procedure; exit 1 = violations, listed.
"""
import argparse, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# the frontmatter parser is check-knowledge's; one parser for one format.
_spec = importlib.util.spec_from_file_location("_ck", HERE / "check-knowledge.py")
_ck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ck)

ROUTABLE = {'procedure'}          # laws constrain, refutations forbid; only a
                                  # procedure tells you what to actually run.


def load_store(kdir):
    claims = {}
    for f in sorted(kdir.rglob('*.md')):
        if f.name == 'README.md':
            continue
        m = _ck.FM.match(f.read_text())
        if not m:
            continue
        front = _ck.parse_front(m.group(1))
        if front.get('id'):
            claims[front['id']] = (front, f)
    return claims


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--knowledge', default=None, help='store dir (default: nearest knowledge/ above cwd)')
    p.add_argument('--regions', action='append', default=[],
                   help='extra file carrying region entries with a `class`; repeatable')
    p.add_argument('--implements', default=None)
    p.add_argument('--json', action='store_true')
    a = p.parse_args()

    cfg = json.loads(Path(a.config).read_text())
    kdir = Path(a.knowledge) if a.knowledge else _ck.find_store()
    claims = load_store(kdir)
    classes = cfg.get('classes', {})
    def entries(obj):
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict) and 'class' in x]
        out = []
        for v in (obj.values() if isinstance(obj, dict) else []):
            out += entries(v)
        return out

    sources = {Path(a.config).name: entries(cfg.get('regions', []))}
    for extra in a.regions:
        sources[Path(extra).name] = entries(json.loads(Path(extra).read_text()))
    used = {r['class'] for src in sources.values() for r in src}

    impl = None
    if a.implements:
        raw = sys.stdin.read() if a.implements == '-' else Path(a.implements).read_text()
        impl = set(json.loads(raw))

    bad = []
    for name, c in sorted(classes.items()):
        where = f"classes.{name}"
        tech = c.get('technique')
        if tech is None:
            bad.append((where, "no `technique`: the build cannot ask the store "
                               "whether this route is still believed"))
            continue
        if tech == 'none':
            # Two different reasons a class runs nothing, and conflating them
            # loses the distinction that matters. `retired-by` names a REFUTED
            # or SUPERSEDED claim and must have no regions left -- any region
            # still pointing at it is a leftover. `held-by` names a LAW and is a
            # positive decision: these regions exist and are deliberately still,
            # which is a thing the picture needs recorded, not a leftover.
            held = c.get('held-by')
            if held:
                if held not in claims:
                    bad.append((where, f"held-by '{held}' is not a claim in the store"))
                elif claims[held][0].get('status') != 'live':
                    bad.append((where, f"held-by '{held}' is not live — a still "
                                       f"region must be held by a law that still stands"))
                elif claims[held][0].get('kind') != 'law':
                    bad.append((where, f"held-by '{held}' is kind "
                                       f"'{claims[held][0].get('kind')}', not a law. "
                                       f"Stillness is a rule, not a measurement."))
                continue
            if not c.get('retired-by'):
                bad.append((where, "technique 'none' must name `retired-by` (a dead "
                                   "technique) or `held-by` (a law that holds these "
                                   "regions still)"))
            elif c['retired-by'] not in claims:
                bad.append((where, f"retired-by '{c['retired-by']}' is not a claim"))
            elif name in used:
                for sn, src in sources.items():
                    r = [x.get('id', '?') for x in src if x['class'] == name]
                    if r:
                        bad.append((where, f"retired by '{c['retired-by']}' but still "
                                           f"routed by {len(r)} region(s) in {sn}: "
                                           f"{', '.join(r[:4])}"))
            continue
        if tech not in claims:
            bad.append((where, f"technique '{tech}' is not a claim id in the store"))
            continue
        front, f = claims[tech]
        rel = f
        if front.get('status') != 'live':
            sup = ''
            for cid, (cf, _) in claims.items():
                if tech in (cf.get('supersedes') or []):
                    sup = f" -- superseded by '{cid}'"
            bad.append((where, f"technique '{tech}' is {front.get('status')}{sup} ({rel})"))
        elif front.get('kind') not in ROUTABLE:
            bad.append((where, f"technique '{tech}' is kind '{front.get('kind')}', "
                               f"not a procedure -- nothing to run ({rel})"))
        if impl is not None and tech not in impl:
            bad.append((where, f"technique '{tech}' is live but the builder "
                               f"implements no dispatch for it"))

    for sn, src in sources.items():
        for name in sorted({r['class'] for r in src} - set(classes)):
            ids = [r.get('id', '?') for r in src if r['class'] == name]
            bad.append((f"{sn}[class={name}]",
                        f"class is not defined in {Path(a.config).name} — "
                        f"{len(ids)} region(s) route to a class that no longer exists: "
                        f"{', '.join(ids[:4])}"))
    for name in sorted(set(classes) - used):
        if classes[name].get('technique') != 'none':
            bad.append((f"classes.{name}", "defined but no region uses it -- dead "
                                           "config outlives the decision that made it"))

    if a.json:
        print(json.dumps({"config": a.config, "classes": len(classes),
                          "violations": [{"at": w, "problem": m} for w, m in bad]},
                         indent=2))
    else:
        for w, m in bad:
            print(f"  {w}: {m}", file=sys.stderr)
        n_live = sum(1 for c in classes.values() if c.get('technique') not in (None, 'none'))
        srcs = ', '.join(f'{k} ({len(v)})' for k, v in sources.items())
        print(f"{Path(a.config).name}: {len(classes)} classes, {n_live} routed · "
              f"regions from {srcs} · {len(bad)} violation(s)", file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
