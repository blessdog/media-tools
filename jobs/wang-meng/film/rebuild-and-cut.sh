#!/usr/bin/env zsh
# One region back to the class default, then the whole z3w station reel.
set -e
cd "$(dirname "$0")/../../.."
J=jobs/wang-meng
echo "==== rebuilding every z3w foliage cycle on the semantic masks" >&2
python3 $J/living/build-zone-living.py --zone z3w --stage cycle --classes foliage --keep-work > /dev/null
python3 $J/living/build-zone-living.py --zone z3w --stage register > /dev/null
for p in $J/film/paths/st-z3w-*.json; do
  n=$(basename $p .json)
  NO_DESKTOP=1 $J/film/render-leg.sh $n z3w
done
python3 $J/film/cut-reel.py --zone z3w >&2
ln -sfn "$PWD/$J/film/STATIONS-z3w.mp4" ~/Desktop/WANG-MENG-LATEST.mp4
echo "==== REEL DONE -> $J/film/STATIONS-z3w.mp4" >&2
