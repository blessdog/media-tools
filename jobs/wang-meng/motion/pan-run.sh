#!/bin/zsh
# Ge Hong walks the ledge while the camera pans with him.
#
# The recorded limit was that --travel past ~70px walks the figure out of a
# 720-wide frame. This is the cel answer to it: cut a strip of the master wider
# than the frame, walk the figure in plate space, and slide the window by the
# same amount. He never leaves frame, so the walk is as long as the painting.
#
# The path is measured off the painting, not invented: his feet sit at master
# (1452,12907) and the ledge climbs right to the cliff at master (2214,12717),
# which is +326,-81 in shot pixels.
set -eu
cd "$(dirname "$0")"
T=../../../tools
M="../../../corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png"

# --up 100 puts the strip origin 100px above the shot's, so every mask cut
# against shot-real.png needs that offset. Both tools now refuse the job rather
# than shift silently, because the silent version erases empty silk, leaves the
# real figure painted in, and still looks plausible in a contact sheet.
OFF=0,100
python3 make-strip.py --master "$M" --out pan/strip.png --right 350 --up 100

python3 $T/clean-plate.py --image pan/strip.png --masks mask/walker \
  --mask-offset $OFF --out pan/strip-clean.png

CAM=(--window 720,1280 --start 0,100 --pan 326,-81 --travel 326,-81 --frames 72)
CEL=(--plate pan/strip-clean.png --figure pan/strip.png --masks mask/walker
     --mask-offset $OFF --over mask/canopy)

python3 $T/walk-figure.py "${CEL[@]}" "${CAM[@]}" \
  --strides 1.1 --bob 4 --lean 0.9 --swing 5 --on 2 \
  --out pan/PAN-gehong.mp4

# The null. Same plate, same window, same pan, but the figure holds one drawing:
# any life the eye reads in the walk clip must not be present here.
python3 $T/walk-figure.py "${CEL[@]}" "${CAM[@]}" \
  --strides 0 --bob 0 --lean 0 --swing 0 --on 72 \
  --out pan/null-rigid.mp4
