#!/usr/bin/env zsh
# HOW OFTEN SHOULD A BRANCH SWING? Build the same hold at several --carrier
# values and stack them, so the RHYTHM is seen rather than argued.
#
# WHY THIS LADDER EXISTS. Ryan, 2026-08-25, on THE-RISE: "it's almost like the
# trees are animatronics, and then once in a while they'll wave at you."
# Diagnosed the same day: the carrier sine and the gust envelope shared one
# clock, so on a 96-drawing loop a branch took 8s for one out-and-back and the
# envelope killed it 40% through -- one wave, then 4.8s at 15% amplitude.
#
# THIS LADDER IS NOT THE SWING LADDER. swing-ladder.sh sweeps AMPLITUDE, which
# Ryan has ruled on twice. This sweeps RATE at fixed peak degrees, so a verdict
# here cannot be read as permission to move the leaf further.
#   carrier-ladder.sh <hold-name> <region> [N ...]   e.g. carrier-ladder.sh pinebridge s-pine-over-bridge 1 3 6
set -e
cd "$(dirname "$0")/../../.."
J=jobs/wang-meng; hold=$1; region=$2; shift 2
ns=($@); (( ${#ns} )) || ns=(1 3 6)
R=$J/living/regions.json; BK=$(mktemp)
cp $R $BK; trap 'cp $BK '"$R"'; rm -f $BK' EXIT INT TERM
clips=()
for n in $ns; do
  echo "==== carrier $n" >&2
  python3 - "$R" "$n" <<'PY'
import json, sys
p, n = sys.argv[1], int(sys.argv[2])
d = json.load(open(p)); d['classes']['foliage']['carrier'] = n
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
PY
  python3 $J/living/build-zone-living.py --zone z3w --stage cycle --classes foliage --region $region --keep-work > /dev/null
  python3 $J/living/build-zone-living.py --zone z3w --stage register > /dev/null
  d=$J/journey/z3w/_ab/$hold
  rm -rf $d/carrier-$n
  python3 tools/render-parallax.py --layers $J/journey/z3w/layers-filled --path $d/path.json \
    --out $d/carrier-$n --width 1920 --height 1080 --fps 24 --z-step 0.30 --plane-fit --no-base \
    --geometry $J/journey/z3w/geometry.json --living $J/living/living-z3w.json > /dev/null
  ffmpeg -y -loglevel error -framerate 24 -i $d/carrier-$n/%05d.png -c:v libx264 -crf 16 -pix_fmt yuv420p $J/living/_carrier-$hold-$n.mp4
  clips+=($J/living/_carrier-$hold-$n.mp4)
  python3 -c "
import json; c=json.load(open('$J/journey/z3w/living-work/$region/drawings/cycle.json'))
print(f\"  carrier {c['carrier']}: branch period {c['branchPeriodSec']}s, peak {c['peakAngleDeg']}deg, {c['cards']} cards\")" >&2
done
n=${#clips}; inputs=(); for c in $clips; do inputs+=(-i $c); done
w=$((1920/n))
filt=""; for ((i=0;i<n;i++)); do filt+="[$i:v]scale=$w:-2[s$i];"; done
for ((i=0;i<n;i++)); do filt+="[s$i]"; done
filt+="hstack=inputs=$n"
ffmpeg -y -loglevel error $inputs -filter_complex "$filt" -c:v libx264 -crf 16 -pix_fmt yuv420p $J/living/LADDER-CARRIER-$hold.mp4
echo "==== LADDER -> $J/living/LADDER-CARRIER-$hold.mp4  (carrier ${ns}, left to right)" >&2
