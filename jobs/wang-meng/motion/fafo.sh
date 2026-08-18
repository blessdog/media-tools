#!/bin/bash
# Motion FAFO sweep. fix1 (already running) = camera-only prompt + hard negative
# + cfg 3 on the REAL painting. These three probe the axes around it.
#
# The failure being chased: at cfg 6 with a prompt naming running water and
# drifting mist, HunyuanVideo 1.5 overwrote the painting with photographic
# waterfall footage inside ~2 seconds. Prompt was the prime suspect; these
# separate prompt from the other candidates.
#
#   fix2  same settings, GENERATED 高遠 still instead of real silk.
#         Does an image already in the model's own idiom resist drift better
#         than a 14th-century scan it has never seen anything like?
#   fix3  cfg 2 and a prompt that leans INTO the medium rather than merely
#         forbidding photography. Positive style pressure vs negative.
#   fix4  CONTROL: no camera move at all. If a static prompt still dissolves
#         into photography, the problem is not the prompt and not the motion —
#         it is that 73 frames of i2v cannot hold this image at all. That is
#         the single most important number in the sweep, which is why it runs.
set -uo pipefail
cd /Users/SSDrive/projects/media-tools
S=/private/tmp/claude-501/-Users-SSDrive-projects/97d5de3b-38f7-4ffa-8a43-dd56553f8732/scratchpad
O=jobs/wang-meng/motion

NEG="photograph, photorealistic, real water, video footage, live action, cinematic lighting, film grain, 3d render, depth of field, motion blur, morphing, texture dissolving"
CAM="the camera pushes slowly and steadily forward, a smooth dolly move deeper into the scene. nothing else changes."

echo "### fix2 — generated still, same recipe as fix1"
node tools/image-to-video.mjs --image "$S/shot-gen.png" \
  --prompt "$CAM" --negative "$NEG" \
  --width 720 --height 1280 --seed 42 --duration 3 --cfg 3 \
  --out $O/push-gen-fix2.mp4 2>&1 | tail -4

echo "### fix3 — real painting, cfg 2, medium-reinforcing prompt"
node tools/image-to-video.mjs --image "$S/shot-real.png" \
  --prompt "a slow forward camera push across an antique Chinese ink painting on silk. the brushwork, ink washes and bare silk stay exactly as painted; the flat painted surface is preserved throughout." \
  --negative "$NEG" \
  --width 720 --height 1280 --seed 42 --duration 3 --cfg 2 \
  --out $O/push-real-fix3.mp4 2>&1 | tail -4

echo "### fix4 — CONTROL: no camera motion, find the drift floor"
node tools/image-to-video.mjs --image "$S/shot-real.png" \
  --prompt "the image is completely still. no camera movement. nothing moves." \
  --negative "$NEG" \
  --width 720 --height 1280 --seed 42 --duration 3 --cfg 3 \
  --out $O/still-control-fix4.mp4 2>&1 | tail -4

echo "### SWEEP DONE"
ls -la $O/*.mp4
