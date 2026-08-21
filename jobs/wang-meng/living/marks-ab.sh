#!/bin/zsh
# A/B the leaf-mark rig against the plain card hinge on ONE region, same swing.
# Left  = cards only  (a spray is one rigid blob on a hinge)
# Right = cards + leaf marks (each mark rotates, narrows and jitters on its own phase)
set -e
ROOT=/Users/SSDrive/projects/media-tools
REGION=${1:-s-pine-over-bridge}
SWING=${2:-12}
D=$ROOT/jobs/wang-meng/journey/z3w/living-work/$REGION
OUT=$ROOT/jobs/wang-meng/evidence
mkdir -p $OUT
COMMON=(--plate $D/clean.png --source $D/plate.png --cards $D/mask
        --frames 96 --on 2 --swing $SWING --flutter 0.15 --angle 8
        --gust 0.10,0.08,0.22 --gust-travel 1500 --gust-rest 0.15
        --min-px 80 --branch-radius auto --branch-ratio 0.55 --attach-max 14
        --ink-offset 0.11 --ink-close 1 --from-ink)
echo "== A: cards only, ${SWING}deg"
python3 $ROOT/tools/hinge-foliage.py $COMMON \
  --out /tmp/ab-cards --preview $OUT/_ab-cards.mp4 2>&1 | tail -2
echo "== B: cards + leaf marks, ${SWING}deg"
python3 $ROOT/tools/hinge-foliage.py $COMMON --leaf-marks \
  --mark-swing ${3:-3} --mark-rate ${4:-3.0} --mark-twinkle ${5:-0.25} --mark-shift ${6:-0.6} \
  --out /tmp/ab-marks --preview $OUT/_ab-marks.mp4 2>&1 | tail -2
ffmpeg -y -i $OUT/_ab-cards.mp4 -i $OUT/_ab-marks.mp4 \
  -filter_complex hstack=inputs=2 -c:v libx264 -crf 16 -pix_fmt yuv420p \
  $OUT/AB-leafmarks-$REGION.mp4 2>&1 | tail -1
rm -f $OUT/_ab-cards.mp4 $OUT/_ab-marks.mp4
echo "-> $OUT/AB-leafmarks-$REGION.mp4   (left cards only | right leaf marks)"
