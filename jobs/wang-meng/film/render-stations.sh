#!/usr/bin/env zsh
# Render every st-<zone>-*.json leg, then cut them into one reel with a short
# dissolve between stations, and put the reel on the Desktop.
#   render-stations.sh z3w
set -e
cd "$(dirname "$0")/../../.."          # media-tools
J=jobs/wang-meng; z=$1
[[ -n $z ]] || { echo "usage: render-stations.sh <zone>" >&2; exit 2; }
legs=()
for p in $J/film/paths/st-$z-*.json; do
  n=$(basename $p .json)
  NO_DESKTOP=1 $J/film/render-leg.sh $n $z
  legs+=($J/film/ST-${n#st-}.mp4)
done
python3 $J/film/cut-reel.py --zone $z >&2
out=$J/film/STATIONS-$z.mp4
ln -sfn "$PWD/$out" ~/Desktop/WANG-MENG-LATEST.mp4
echo "==== REEL -> $out; Desktop symlink refreshed" >&2
