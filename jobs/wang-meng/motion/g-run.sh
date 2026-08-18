#!/bin/zsh
# G: E's amplitude without E's re-inking.
# D (motion-only wording) kept Wang Meng's dry line but moved little. E added
# style words -- "flat ink on silk, a Yuan dynasty hanging scroll" -- and at
# cfg 6 those words acted on the picture: twice the motion, but the lines came
# back bolder and the rock darker. So G keeps cfg 6 and E's stronger current,
# and says NOTHING about style. If it lands between them, the rule is: at high
# cfg the prompt carries motion only, never look.
set -e
cd "$(dirname "$0")"
NEG="photograph, photorealistic, real water, video footage, live action, cinematic lighting, film grain, 3d render, depth of field, motion blur, morphing, texture dissolving, bold ink, heavy brushwork, dark outlines"
node ../../../tools/image-to-video.mjs --image crop-river.png --width 704 --height 640 \
  --fps 24 --duration 3 --steps 20 --cfg 6 --seed 42 --negative "$NEG" \
  --host http://127.0.0.1:8189 --out crop-G-motiononly.mp4 \
  --prompt "the current runs steadily downstream and the ripple lines stream along with it. the camera does not move."
