#!/usr/bin/env zsh
# Rebuild every foliage cycle on the attachment-pivot rig (regions.json class
# `foliage`: branchRadius/attachMax), re-register each zone, then re-render the
# four foliage A/B holds so the judgement is made on the rig that will ship.
set -e
cd "$(dirname "$0")/../../.."          # media-tools
J=jobs/wang-meng
# usage: rebuild-foliage.sh [hold ...]   default: the four foliage holds
holds=("$@"); (( ${#holds} )) || holds=(pinebridge greattrees bigcanopy fallandpines)
for z in z3w z4w z5w z6w; do
  echo "==== $z cycle (foliage)" >&2
  python3 $J/living/build-zone-living.py --zone $z --stage cycle --classes foliage --keep-work > $J/living/logs/cycle-foliage-$z.json
  echo "==== $z register" >&2
  python3 $J/living/build-zone-living.py --zone $z --stage register > /dev/null
  if [[ $z == z3w ]]; then
    # every near tree's hinge, one sheet, for the eye: the attached COUNT cannot
    # tell a pivot at a twig from a pivot inside a leaf blob
    python3 $J/living/pivot-sheet.py --work $J/journey/z3w/living-work --out $J/living/evidence-branch-pivots-z3w.png >&2
  fi
done
# force the LIVING half of each foliage hold to re-render; the static half is unchanged
for h in $holds; do rm -rf $J/journey/z3w/_ab/$h/living; done
$J/living/render-holds.sh $holds
echo "==== DONE" >&2
