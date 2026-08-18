#!/bin/zsh
# Runs D and E: the CROP arm of the masking test, 2026-08-14.
#
# Clip A proved the text channel has no steering authority at cfg 3 -- the
# prompt named water, the water sat perfectly still (selectivity 0.48) and the
# model animated Ge Hong and the deer instead (hijack 3.15). cfg is one volume
# knob on the text, and turning it down to save the painting also turned off
# aiming.
#
# So these two raise cfg back to 6 -- the setting that destroyed the painting --
# but hand the model a CROP that contains nothing except river and rock. If the
# only thing in frame is water, then text strong enough to command water can no
# longer dissolve a face, because there is no face. That is the whole wager of
# masking, moved from the compositor to the conditioning image.
#
#   D  cfg 6, substance named   — maximum steering, maximum risk
#   E  cfg 6, medium named      — does naming ink instead of water still aim?
set -e
cd "$(dirname "$0")"
T=../../../tools/image-to-video.mjs
NEG="photograph, photorealistic, real water, video footage, live action, cinematic lighting, film grain, 3d render, depth of field, motion blur, morphing, texture dissolving"
COMMON=(--image crop-river.png --width 704 --height 640 --fps 24 --duration 3
        --steps 20 --cfg 6 --seed 42 --negative "$NEG" --host http://127.0.0.1:8189)

echo "── D: crop, cfg 6, substance named ────────────────────"
node $T "${COMMON[@]}" --out crop-D-substance.mp4 \
  --prompt "the river water flows and ripples slowly downstream. the camera does not move."

echo "── E: crop, cfg 6, medium named ───────────────────────"
node $T "${COMMON[@]}" --out crop-E-medium.mp4 \
  --prompt "the painted ink current lines drift slowly downstream across the bare silk, flat ink on silk, a Yuan dynasty hanging scroll. the camera does not move."

echo "done. clips: crop-D-substance.mp4 crop-E-medium.mp4"
