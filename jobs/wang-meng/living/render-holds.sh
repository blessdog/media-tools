#!/usr/bin/env zsh
# STILL-CAMERA holds on each authored water body, living vs static.
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
)
for h in "${holds[@]}"; do
  set -- ${=h}; name=$1; z=$2; x=$3; y=$4; fov=$5
  d=$J/journey/$z/_ab/$name
  mkdir -p $d
  cat > $d/path.json <<JSON
{"fps": 24, "duration": 6.0,
 "keys": [{"t": 0.0, "x": $x, "y": $y, "z": 0.0, "fov": $fov},
          {"t": 6.0, "x": $x, "y": $y, "z": 0.0, "fov": $fov}]}
JSON
  for mode in static living; do
    args=(--layers $J/journey/$z/layers-filled --path $d/path.json
          --out $d/$mode --width 1920 --height 1080 --fps 24
          --z-step 0.30 --plane-fit --no-base
          --geometry $J/journey/$z/geometry.json)
    [[ $mode == living ]] && args+=(--living $J/living/living-$z.json)
    echo "== $name/$mode" >&2
    python3 tools/render-parallax.py $args > /dev/null
  done
  ffmpeg -y -framerate 24 -i $d/static/%05d.png -framerate 24 -i $d/living/%05d.png \
    -filter_complex "[0:v]scale=960:540,drawtext=text='':x=0:y=0[a];[1:v]scale=960:540[b];[a][b]hstack" \
    -c:v libx264 -crf 16 -pix_fmt yuv420p $J/living/AB-HOLD-$name.mp4 2>/dev/null
  echo "-> $J/living/AB-HOLD-$name.mp4" >&2
done
