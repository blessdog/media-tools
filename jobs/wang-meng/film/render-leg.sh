#!/usr/bin/env zsh
# Render ONE camera leg over a zone's living layer.
#   render-leg.sh <path-name> <zone>      e.g.  render-leg.sh leg-light-z3w z3w
# Reads film/paths/<path-name>.json, writes film/<PATH-NAME>.mp4 (upper-cased)
# and refreshes ~/Desktop/WANG-MENG-LATEST.mp4 to it. Same projection flags as
# living/render-holds.sh, so a hold and a leg are the same picture with a
# different camera. The LIVING GATE lives in compile-flight.py; this script is
# for one leg at a time and always renders WITH the living layer.
set -e
cd "$(dirname "$0")/../../.."          # media-tools
J=jobs/wang-meng
name=$1; z=$2
[[ -n $name && -n $z ]] || { echo "usage: render-leg.sh <path-name> <zone>" >&2; exit 2; }
[[ -f $J/living/living-$z.json ]] || { echo "LIVING GATE: no living-$z.json -- author the motion first" >&2; exit 3; }
d=$J/film/frames/$name
rm -rf $d; mkdir -p $d
python3 tools/render-parallax.py \
  --layers $J/journey/$z/layers-filled --path $J/film/paths/$name.json \
  --out $d --width 1920 --height 1080 --fps 24 \
  --z-step 0.30 --plane-fit --no-base \
  --geometry $J/journey/$z/geometry.json \
  --living $J/living/living-$z.json > /dev/null
out=$J/film/${(U)name}.mp4
ffmpeg -y -loglevel error -framerate 24 -i $d/%05d.png -c:v libx264 -crf 16 -pix_fmt yuv420p $out
ln -sfn "$PWD/$out" ~/Desktop/WANG-MENG-LATEST.mp4
echo "-> $out  ($(ls $d | wc -l | tr -d ' ') frames); Desktop symlink refreshed" >&2
