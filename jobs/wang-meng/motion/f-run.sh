#!/bin/zsh
# F: the null for D. Same crop, same prompt, same seed — cfg 3 instead of 6.
# Without it, D's ripple motion could be the crop's doing rather than cfg's, and
# "the crop restored the prompt's authority" would be a story, not a finding.
set -e
cd "$(dirname "$0")"
NEG="photograph, photorealistic, real water, video footage, live action, cinematic lighting, film grain, 3d render, depth of field, motion blur, morphing, texture dissolving"
node ../../../tools/image-to-video.mjs --image crop-river.png --width 704 --height 640 \
  --fps 24 --duration 3 --steps 20 --cfg 3 --seed 42 --negative "$NEG" \
  --host http://127.0.0.1:8189 --out crop-F-cfg3.mp4 \
  --prompt "the river water flows and ripples slowly downstream. the camera does not move."
