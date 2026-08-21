#!/usr/bin/env zsh
# Rebuild every foliage cycle on the attachment-pivot rig (regions.json class
# `foliage`: branchRadius/attachMax), re-register each zone, then re-render the
# four foliage A/B holds so the judgement is made on the rig that will ship.
set -e
cd "$(dirname "$0")/../../.."          # media-tools
J=jobs/wang-meng
for z in z3w z4w z5w z6w; do
  echo "==== $z cycle (foliage)" >&2
  python3 $J/living/build-zone-living.py --zone $z --stage cycle --classes foliage > $J/living/logs/cycle-foliage-$z.json
  echo "==== $z register" >&2
  python3 $J/living/build-zone-living.py --zone $z --stage register > /dev/null
done
# force the LIVING half of each foliage hold to re-render; the static half is unchanged
for h in pinebridge greattrees bigcanopy fallandpines; do rm -rf $J/journey/z3w/_ab/$h/living; done
$J/living/render-holds.sh pinebridge greattrees bigcanopy fallandpines
echo "==== DONE" >&2
