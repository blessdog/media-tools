#!/usr/bin/env zsh
# STILL-CAMERA holds on each authored living body, living vs static.
# Optional args select a subset by name:  ./render-holds.sh summitcrest summitpeaks
# The camera does not move in any of these: the only thing that can differ
# between the two halves is the water. That is the point (MOTION BEFORE CAMERA).
set -e
cd "$(dirname "$0")/../../.."          # media-tools
J=jobs/wang-meng
holds=(
  "midstream z3w 0.2505 0.7838 1.40"
  "gorgefall z3w 0.2323 0.6328 2.00"
  "lowerpool z3w 0.1974 0.9183 2.20"
  "compoundfall z5w 0.6620 0.5525 2.00"
  # WATER AND FOLIAGE IN ONE FRAME, 2026-08-20. Ryan: "It's like you'll either
  # animate a little bit of water or the tree, you won't put both together in a
  # picture. Is there a reason for that?" There was not. Every hold until now
  # framed ONE body, which is a testing artifact that leaked into review.
  "waterandtrees z5w 0.6000 0.4600 1.25"
  "gorgecanopy z3w 0.5466 0.4933 1.60"
  "fallandpines z3w 0.2277 0.6709 1.60"
  # the summits, added 2026-08-20 -- the band above y~3850 master had no
  # living region at all, so the highest stations framed a still picture
  "summitcrest z6w 0.2580 0.2500 1.60"
  "summitdome z6w 0.3430 0.3160 1.50"
  "summitpeaks z6w 0.8200 0.2720 1.80"
)
if (( $# )); then
  want=("$@")
  filtered=()
  for h in "${holds[@]}"; do
    hn=${h%% *}
    for w in "${want[@]}"; do [[ $hn == $w ]] && filtered+=("$h"); done
  done
  holds=("${filtered[@]}")
  shift $#
fi
for h in "${holds[@]}"; do
  set -- ${=h}; name=$1; z=$2; x=$3; y=$4; fov=$5
  d=$J/journey/$z/_ab/$name
  mkdir -p $d
  cat > $d/path.json <<JSON
{"fps": 24, "duration": 8.0,
 "keys": [{"t": 0.0, "x": $x, "y": $y, "z": 0.0, "fov": $fov},
          {"t": 8.0, "x": $x, "y": $y, "z": 0.0, "fov": $fov}]}
JSON
  for mode in static living; do
    args=(--layers $J/journey/$z/layers-filled --path $d/path.json
          --out $d/$mode --width 1920 --height 1080 --fps 24
          --z-step 0.30 --plane-fit --no-base
          --geometry $J/journey/$z/geometry.json)
    [[ $mode == living ]] && args+=(--living $J/living/living-$z.json)
    if [[ $(ls $d/$mode 2>/dev/null | wc -l) -eq 192 ]]; then
      echo "== $name/$mode already rendered" >&2
    else
      echo "== $name/$mode" >&2
      python3 tools/render-parallax.py $args > /dev/null
    fi
  done
  ffmpeg -y -framerate 24 -i $d/static/%05d.png -framerate 24 -i $d/living/%05d.png \
    -filter_complex "[0:v]scale=960:540[a];[1:v]scale=960:540[b];[a][b]hstack" \
    -c:v libx264 -crf 16 -pix_fmt yuv420p $J/living/AB-HOLD-$name.mp4
  echo "-> $J/living/AB-HOLD-$name.mp4" >&2
done
