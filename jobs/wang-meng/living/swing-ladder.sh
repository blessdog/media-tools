#!/usr/bin/env zsh
# HOW MUCH SHOULD A LEAF MOVE? Build the same hold at several swing angles and
# stack them, so the amount is SEEN rather than nudged. Reports ink loss per
# angle -- the cost of a bigger swing.
#
# WHAT THIS LADDER CANNOT SETTLE (measured 2026-08-21): the value the FILM should
# use. Ryan picked 12 off this ladder on one tight hold of one tree, and reversed
# it to 6 within the hour on seeing the cut. Tip travel in screen px scales with
# fov, the reel spans fov 1.0-1.6, and its seven trees differ 3x in card radius --
# so an angle that reads as lively in a tight hold is nearly double the travel in
# a wide one. Use the ladder to understand the RANGE; set the value in the reel.
# See knowledge/leaf-travel-is-measured-on-screen.md.
#   swing-ladder.sh <hold-name> <region> [deg ...]     e.g. swing-ladder.sh pinebridge s-pine-over-bridge 6 12 18
set -e
cd "$(dirname "$0")/../../.."
J=jobs/wang-meng; hold=$1; region=$2; shift 2
degs=($@); (( ${#degs} )) || degs=(6 12 18)
R=$J/living/regions.json; BK=$(mktemp)
cp $R $BK; trap 'cp $BK '"$R"'; rm -f $BK' EXIT INT TERM
clips=()
for deg in $degs; do
  echo "==== swing $deg" >&2
  python3 - "$R" "$deg" <<'PY'
import json, sys
p, deg = sys.argv[1], float(sys.argv[2])
d = json.load(open(p)); d['classes']['foliage']['swing'] = deg
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
PY
  python3 $J/living/build-zone-living.py --zone z3w --stage cycle --classes foliage --region $region --keep-work > /dev/null
  python3 $J/living/build-zone-living.py --zone z3w --stage register > /dev/null
  d=$J/journey/z3w/_ab/$hold
  rm -rf $d/living-$deg
  python3 tools/render-parallax.py --layers $J/journey/z3w/layers-filled --path $d/path.json \
    --out $d/living-$deg --width 1920 --height 1080 --fps 24 --z-step 0.30 --plane-fit --no-base \
    --geometry $J/journey/z3w/geometry.json --living $J/living/living-z3w.json > /dev/null
  ffmpeg -y -loglevel error -framerate 24 -i $d/living-$deg/%05d.png -c:v libx264 -crf 16 -pix_fmt yuv420p $J/living/_ladder-$hold-$deg.mp4
  clips+=($J/living/_ladder-$hold-$deg.mp4)
  python3 -c "
import json; c=json.load(open('$J/journey/z3w/living-work/$region/drawings/cycle.json'))
print(f\"  swing {c['swingDeg']}deg: {c['cards']} cards, peak {c['peakAngleDeg']}deg\")" >&2
done
n=${#clips}; inputs=(); for c in $clips; do inputs+=(-i $c); done
w=$((1920/n))
filt=""; for ((i=0;i<n;i++)); do filt+="[$i:v]scale=$w:-2[s$i];"; done
for ((i=0;i<n;i++)); do filt+="[s$i]"; done
filt+="hstack=inputs=$n"
ffmpeg -y -loglevel error $inputs -filter_complex "$filt" -c:v libx264 -crf 16 -pix_fmt yuv420p $J/living/LADDER-$hold.mp4
echo "==== LADDER -> $J/living/LADDER-$hold.mp4  (${degs} degrees, left to right)" >&2
