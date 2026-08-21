#!/usr/bin/env zsh
# A/B the multiplane truck against the pan it replaces. One job.
#   ab-truck.sh <truck> <truck-max px> [seconds]   e.g.  ab-truck.sh 0.25 36 10
#
# Same camera path, same plane stack, same living layer -- the ONLY difference
# is whether the planes translate at different rates. Left is what the film did
# for weeks (every plane on one sheet: a pan). Right is the truck.
#
# Labels are composited as PIL-rendered PNG overlays, NOT ffmpeg drawtext: this
# machine's ffmpeg is built without libfreetype, so drawtext fails at the very
# last step after both legs have already rendered.
set -e
cd "$(dirname "$0")/../../.."          # media-tools
J=jobs/wang-meng
F=$J/film
T=${1:-0.25}
CAP=${2:-36}
SECS=${3:-10}
P=$F/paths/_ab-truck.json
TMP=${TMPDIR:-/tmp}/ab-truck.$$
mkdir -p $TMP

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

render() {  # render <outdir> <truck> <truck-max>
  rm -rf $1; mkdir -p $1
  python3 tools/render-parallax.py \
    --layers $J/journey/z1/layers-filled --path $P --out $1 \
    --width 1920 --height 1080 --fps 24 --z-step 0.30 --plane-fit --no-base \
    --truck $2 --truck-max $3 --geometry $J/journey/z1/geometry.json \
    --living $J/living/living-z1.json > /dev/null
}
print -u2 "== pan"
render $F/frames/_ab-truck-pan 0 0
print -u2 "== truck $T cap ${CAP}px"
render $F/frames/_ab-truck-$T-$CAP $T $CAP

python3 - "$TMP" "$T" "$CAP" <<'PY'
import os, sys
from PIL import Image, ImageDraw, ImageFont
tmp, t, cap = sys.argv[1], sys.argv[2], sys.argv[3]
font = next((ImageFont.truetype(c, 24) for c in
             ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc"] if os.path.exists(c)), None)
for name, text in (("a", "PAN  —  every plane on one sheet"),
                   ("b", f"MULTIPLANE TRUCK {t}  ·  capped {cap}px")):
    im = Image.new("RGBA", (560, 44), (0, 0, 0, 150))
    ImageDraw.Draw(im).text((14, 9), text, fill=(255, 255, 255, 255), font=font)
    im.save(f"{tmp}/lab-{name}.png")
PY

OUT=$J/evidence/$(date +%Y-%m-%d)-AB-pan-vs-truck-$T-cap$CAP.mp4
ffmpeg -y -loglevel error \
  -framerate 24 -i $F/frames/_ab-truck-pan/%05d.png \
  -framerate 24 -i $F/frames/_ab-truck-$T-$CAP/%05d.png \
  -i $TMP/lab-a.png -i $TMP/lab-b.png \
  -filter_complex "[0:v]scale=960:540[a];[1:v]scale=960:540[b];\
[a][b]hstack=inputs=2[h];[h][2:v]overlay=14:14[h2];[h2][3:v]overlay=974:14,format=yuv420p" \
  -c:v libx264 -crf 16 $OUT
rm -rf $TMP
print -u2 "-> $OUT"
