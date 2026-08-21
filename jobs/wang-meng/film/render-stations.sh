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
  legs+=($J/film/${(U)${n%-*}}-${n##*-}.mp4)
done
# order by the station list, not by filename
ordered=()
for st in $(python3 -c "
import json; s=json.load(open('$J/film/stations-slow.json'))
print(' '.join(x['name'] for x in s['stations'] if x['zone']=='$z'))"); do
  for l in $legs; do [[ $l == *-$st.mp4 ]] && ordered+=($l); done
done
# 0.7 s dissolve between consecutive legs (pacing.crossfade in stations-slow.json)
n=${#ordered}; inputs=(); filt=""; prev="[0:v]"; off=0
for ((i=1;i<=n;i++)); do inputs+=(-i ${ordered[$i]}); done
for ((i=1;i<n;i++)); do
  off=$(( i*10 - i*0.7 ))
  filt+="${prev}[$i:v]xfade=transition=fade:duration=0.7:offset=$off[v$i];"; prev="[v$i]"
done
filt=${filt%;}
out=$J/film/STATIONS-$z.mp4
ffmpeg -y -loglevel error $inputs -filter_complex "$filt" -map "$prev" -c:v libx264 -crf 16 -pix_fmt yuv420p $out
ln -sfn "$PWD/$out" ~/Desktop/WANG-MENG-LATEST.mp4
echo "==== REEL -> $out ($n stations); Desktop symlink refreshed" >&2
