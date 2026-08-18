#!/bin/zsh
# The A/B that decides whether the flux fill survives motion.
#
# A single frame proved flux fills a hole better (Ryan, 2026-08-17). This asks
# the question a still cannot: does it hold for 121 frames? Because the fill
# happens ONCE in layer space, flicker is structurally impossible — the clip is
# a resampling of fixed texels, not 121 independent generations. That claim is
# free to make and worthless unless rendered, so: render it.
#
# Both stacks share the same camera, geometry and z-step. The ONLY difference is
# how the hidden band behind each occluder was painted.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
cd "$ROOT"
J=jobs/wang-meng/motion/pan
C=(--path $J/path-push-deep.json --geometry $J/geometry-shot.json
   --plane-fit --z-step 0.15 --width 720 --height 1280 --fps 24 --duration 5)

for s in layers-final layers-flux; do
  echo "== rendering $s"
  python3 tools/render-parallax.py --layers $J/$s --out $J/ab/$s "${C[@]}" >/dev/null
  ffmpeg -y -loglevel error -r 24 -i $J/ab/$s/%05d.png \
    -c:v libx264 -crf 16 -pix_fmt yuv420p $J/ab/$s.mp4
done

python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
img = Image.new("RGB", (1440, 46), (16, 16, 16))
d = ImageDraw.Draw(img)
try: f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)
except OSError: f = ImageFont.load_default()
for i, t in enumerate(["CLASSICAL  (shiftmap)", "FLUX 1 FILL"]):
    x0, _, x1, _ = d.textbbox((0, 0), t, font=f)
    d.text((i*720 + (720-(x1-x0))/2, 9), t, font=f, fill=(255, 255, 255))
img.save("/tmp/ab-labels.png")
PY

ffmpeg -y -loglevel error \
  -i $J/ab/layers-final.mp4 -i $J/ab/layers-flux.mp4 -i /tmp/ab-labels.png \
  -filter_complex "[0:v][1:v]hstack=inputs=2[s];[s][2:v]overlay=0:0[v]" \
  -map "[v]" -c:v libx264 -crf 16 -pix_fmt yuv420p $J/FLUX-VS-CLASSICAL.mp4
echo "wrote $J/FLUX-VS-CLASSICAL.mp4"
