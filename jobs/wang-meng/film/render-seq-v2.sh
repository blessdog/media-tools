#!/bin/zsh
# SEQ-Z1-v2: render all seven shots with the locked recipe, encode each,
# then stitch against chowder-julius.mp3. Composition lives here, not in tools.
set -e
cd "$(dirname "$0")/../../.."   # repo root
Z=jobs/wang-meng/journey/z1
F=jobs/wang-meng/film
for s in 1 2 3 4 5 6 7; do
  p=$(ls $F/paths/shot$s-*.json)
  echo "=== shot $s: $p" >&2
  python3 tools/render-parallax.py --layers $Z/layers-filled --path $p \
    --out $F/frames/shot$s --width 1920 --height 1080 --fps 24 \
    --z-step 0.30 --plane-fit --no-base --geometry $Z/geometry.json \
    --living jobs/wang-meng/living/living-gust.json --relief $Z/relief.json \
    >/dev/null
  ffmpeg -y -framerate 24 -i $F/frames/shot$s/%05d.png -c:v libx264 -crf 15 \
    -pix_fmt yuv420p $F/shot$s.mp4 2>/dev/null
done
for s in 1 2 3 4 5 6 7; do echo "shot$s.mp4"; done > $F/shots.txt
node tools/stitch.mjs --list $F/shots.txt --music jobs/wang-meng/music/chowder-julius.mp3 \
  --out $F/SEQ-Z1-v2.mp4 --fps 24 >/dev/null
echo "SEQ-Z1-v2 DONE"
