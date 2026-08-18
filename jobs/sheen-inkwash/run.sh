#!/bin/zsh
# jobs/sheen-inkwash — the phase-5 proof: a 43s Parliament cigarette ad with no
# dialogue, turned into words by describe-video, then repainted shot by shot by
# the real inkwash renderer (USO on a Vast box).
#
# Composition only. Every step is a toolbox CLI; nothing here is a capability.
#
# Prerequisites:
#   node ../../tools/gpu-box.mjs up --rent     # box (billing starts)
#   node ../../tools/gpu-box.mjs forward --port 8189 &
#   ... and when done:  node ../../tools/gpu-box.mjs down
set -e
cd "$(dirname "$0")"
T=~/projects/media-tools/tools

# 1. footage → a written script (this clip has loud music and ZERO speech, so
#    transcribe returns nothing; the script has to come from the pixels)
[ -f shots.json ] || node $T/describe-video.mjs --video source.mp4 --out shots.json --threshold 0.15 --every 4

# 2. each described shot → an inkwash frame. The style channel is the LOCKED
#    swatch; the text is content only. The prompt files carry a "Shot N — 12 s"
#    header for human reading — strip it before it reaches the model.
mkdir -p renders
for f in regen/shot-*.txt; do
  n=${${f:t:r}#shot-}
  node $T/generate-image.mjs \
    --style inkwash \
    --prompt "$(tail -n +3 "$f")" \
    --out "renders/shot-$n.png"
  open "renders/shot-$n.png"
done

# 3. Ryan's eyes decide. Re-run a single shot with a different --seed to reroll.
