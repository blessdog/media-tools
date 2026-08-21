#!/usr/bin/env zsh
# A/B the multiplane truck against the pan it replaces. One job.
#   ab-truck.sh <truck> [seconds]      e.g.  ab-truck.sh 0.25 10
#
# Same camera path, same plane stack, same living layer -- the ONLY difference
# is whether the planes translate at different rates. Left is what the film has
# been doing for weeks (every plane on one sheet: a pan). Right is the truck.
set -e
cd "$(dirname "$0")/../../.."          # media-tools
J=jobs/wang-meng
F=$J/film
T=${1:-0.25}
SECS=${2:-10}
P=$F/paths/_ab-truck.json

python3 - "$SECS" > $P <<'PY'
import json, sys
secs = float(sys.argv[1])
k = json.load(open("jobs/wang-meng/film/paths/rise-z1.json"))["keys"]
# a stretch of PURE TRAVERSE from the rise: z is 0.0 at both ends, so nothing
# but the translation can be responsible for what the A/B shows.
json.dump({"fps": 24, "duration": secs,
           "keys": [dict(k[0], t=0.0),
                    {"t": secs, "x": k[1]["x"], "y": k[1]["y"],
                     "z": 0.0, "fov": k[1]["fov"]}]}, sys.stdout, indent=1)
PY

for tr in 0.0 $T; do
  d=$F/frames/_ab-truck-$tr
  rm -rf $d; mkdir -p $d
  print -u2 "== rendering truck $tr"
  python3 tools/render-parallax.py \
    --layers $J/journey/z1/layers-filled --path $P --out $d \
    --width 1920 --height 1080 --fps 24 --z-step 0.30 --plane-fit --no-base \
    --truck $tr --geometry $J/journey/z1/geometry.json \
    --living $J/living/living-z1.json > /dev/null
done

ffmpeg -y -loglevel error \
  -framerate 24 -i $F/frames/_ab-truck-0.0/%05d.png \
  -framerate 24 -i $F/frames/_ab-truck-$T/%05d.png \
  -filter_complex "\
    [0:v]scale=960:540,drawtext=text='PAN — every plane on one sheet':x=16:y=16:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=6[a];\
    [1:v]scale=960:540,drawtext=text='MULTIPLANE TRUCK $T':x=16:y=16:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=6[b];\
    [a][b]hstack=inputs=2,format=yuv420p" \
  -c:v libx264 -crf 16 $J/evidence/$(date +%Y-%m-%d)-AB-pan-vs-truck-$T.mp4

print -u2 "-> $J/evidence/$(date +%Y-%m-%d)-AB-pan-vs-truck-$T.mp4"
