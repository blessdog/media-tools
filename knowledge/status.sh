#!/usr/bin/env bash
# What THIS project counts. Run by state-report.py at generation time, from the
# repo root, so STATE.md's status section is measured rather than remembered.
# Generic tool, specific project: every project writes its own.
set -u
J=jobs/wang-meng

echo "LIVING LAYER — cycles registered per zone"
for f in $J/living/living-z*.json; do
  [ -e "$f" ] || continue
  z=$(basename "$f" .json | sed 's/living-//')
  python3 - "$f" "$z" <<'PY'
import json, sys, collections
from pathlib import Path
# living-<zone>.json is keyed by PLANE, each carrying a patch list
d = json.load(open(sys.argv[1]))
pat = [q for v in d.values() for q in v.get('patches', [])]
reg = collections.Counter(Path(q['dir']).name.split('__')[-1] for q in pat)
live = {x['id'] for x in json.load(open('jobs/wang-meng/living/living-polys.json'))['polys']
        if x['class'] != 'still'}
stale = sorted({r.rsplit('-', 1)[0] if r[-3:-2] == '-' and r[-2:].isdigit() else r
                for r in reg} - live)
print(f"  {sys.argv[2]:5s} {len(pat):3d} patches · {len(d)} planes · {len(reg)} regions")
if stale:
    print(f"        ⚠ STALE, no longer an animated region: {', '.join(stale)}")
PY
done

echo
echo "REGIONS — by class, from the file the builder reads"
python3 - <<'PY'
import json, collections
p = json.load(open('jobs/wang-meng/living/living-polys.json'))['polys']
for k, v in sorted(collections.Counter(x['class'] for x in p).items()):
    print(f"  {k:10s} {v}")
PY

echo
echo "ROUTING — knowledge store vs config vs implementation"
python3 $J/living/build-zone-living.py --techniques 2>/dev/null \
  | python3 ~/.claude/knowledge/bin/check-routing.py \
      --config $J/living/regions.json --regions $J/living/living-polys.json \
      --implements - 2>&1 | sed 's/^/  /'

echo
echo "DELIVERABLES"
ls -t $J/living/AB-*.mp4 $J/film/*.mp4 2>/dev/null | head -6 | sed 's|^|  |'
printf "  Desktop symlink: "; readlink ~/Desktop/WANG-MENG-LATEST.mp4 2>/dev/null || echo "(none)"

echo
echo "RELIEF — within-plane surface shape, per zone (the 2026-08-19 verdict)"
python3 - <<'PY2'
import json, glob, os
tot_r = tot_p = 0
for d in sorted(glob.glob('jobs/wang-meng/journey/z*/')):
    z = os.path.basename(d.rstrip('/'))
    lj = os.path.join(d, 'layers-filled', 'layers.json')
    if not os.path.exists(lj):
        continue
    planes = json.load(open(lj)).get('planes', 0)
    rj = os.path.join(d, 'relief.json')
    n = len(json.load(open(rj))) if os.path.exists(rj) else 0
    tot_r += n; tot_p += planes
    flag = '' if n else '   ⚠ NO relief.json'
    print(f"  {z:5s} {n:3d} of {planes:3d} planes{flag}")
pct = 100.0 * tot_r / tot_p if tot_p else 0
print(f"  TOTAL {tot_r:3d} of {tot_p:3d} planes = {pct:.0f}%")
if pct < 90:
    print(f"        ⚠ relief WON its A/B on 2026-08-19 and joined the 'locked recipe',")
    print(f"        but journey/build-zone.sh has no relief step, so the six zones")
    print(f"        built after the verdict never got it. See")
    print(f"        knowledge/a-verdict-is-not-landed-until-the-builder-changes.md")
PY2
