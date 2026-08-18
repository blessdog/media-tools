#!/bin/zsh
# GATE 1 — does Wan 2.2 A14B hold Wang Meng's ink?
#
# Three panels, same source still, same camera-only prompt:
#   SOURCE   the still itself, frozen — the ground truth for "did the ink survive"
#   HUNYUAN  push-real-fix1.mp4, the renderer already proven on this painting
#   WAN      GATE1-wan-ink.mp4, the candidate
#
# The frozen source is the control. Without it the eye compares two moving
# clips to each other and has no fixed reference for what the ink looked like.
#
# GOTCHA: this machine's ffmpeg is built WITHOUT libfreetype, so `drawtext`
# does not exist ("No such filter: 'drawtext'"). Labels are rendered to a PNG
# strip with PIL and composited as an overlay instead.
set -euo pipefail
cd "$(dirname "$0")"

DUR=5.1          # the longer of the two clips; Hunyuan holds its last frame
W=540; H=960     # per panel
STRIP=/tmp/gate1-labels.png

python3 - "$W" "$H" "$STRIP" <<'PY'
import sys
from PIL import Image, ImageDraw, ImageFont
W, H, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
bar = 64
img = Image.new("RGBA", (W * 3, bar), (0, 0, 0, 165))
d = ImageDraw.Draw(img)
try:
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 27)
except OSError:
    f = ImageFont.load_default()
for i, t in enumerate(["SOURCE STILL", "HUNYUAN 1.5  (proven)", "WAN 2.2 A14B  (gate 1)"]):
    x0, _, x1, _ = d.textbbox((0, 0), t, font=f)
    d.text((i * W + (W - (x1 - x0)) / 2, (bar - 34) / 2), t, font=f, fill=(255, 255, 255, 255))
img.save(out)
PY

ffmpeg -y -loglevel error \
  -loop 1 -t $DUR -i shot-real.png \
  -i push-real-fix1.mp4 \
  -i GATE1-wan-ink.mp4 \
  -i "$STRIP" \
  -filter_complex "
    [0:v]scale=${W}:${H},setsar=1,fps=24[a];
    [1:v]scale=${W}:${H},setsar=1,fps=24,tpad=stop_mode=clone:stop_duration=3,trim=duration=${DUR},setpts=PTS-STARTPTS[b];
    [2:v]scale=${W}:${H},setsar=1,fps=24,trim=duration=${DUR},setpts=PTS-STARTPTS[c];
    [a][b][c]hstack=inputs=3[s];
    [s][3:v]overlay=0:main_h-overlay_h-24[v]
  " -map "[v]" -c:v libx264 -crf 18 -pix_fmt yuv420p GATE1-COMPARE.mp4

echo "wrote GATE1-COMPARE.mp4"
