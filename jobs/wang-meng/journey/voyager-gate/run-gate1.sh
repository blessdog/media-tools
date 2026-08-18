#!/bin/bash
# Voyager gate — RUN 1 (stock MoGe conditions, baseline). Two stages so the
# operator can pull samples between them (checkpoint B: conditions; C: output).
# Prompt is camera-only per Law 5. Full-weight fp16, 50 steps — no shortcuts.
set -euo pipefail
# no venv — the box's docker image (pytorch/pytorch:2.4.0-cuda12.4) IS the env
cd /workspace/HunyuanWorld-Voyager

STAGE="${1:-conditions}"

if [ "$STAGE" = "conditions" ]; then
  cd data_engine
  python3 create_input.py \
    --image_path /workspace/input-bridge.png \
    --render_output_dir /workspace/gate1 \
    --type forward
  echo "CONDITIONS-DONE: $(ls /workspace/gate1/video_input/ | head -3)"
fi

if [ "$STAGE" = "infer" ]; then
  python3 sample_image2video.py \
    --model HYVideo-T/2 \
    --input-path /workspace/gate1 \
    --prompt "the camera pushes slowly and steadily forward, a smooth dolly move deeper into the scene. nothing else changes." \
    --negative-prompt "photograph, photorealistic, real water, video footage, live action, cinematic lighting, film grain, 3d render, depth of field, motion blur, morphing, texture dissolving" \
    --i2v-stability \
    --infer-steps 50 \
    --flow-reverse \
    --flow-shift 7.0 \
    --seed 0 \
    --embedded-cfg-scale 6.0 \
    --use-cpu-offload \
    --save-path /workspace/gate1/results
  echo "INFER-DONE: $(ls /workspace/gate1/results/ 2>/dev/null | head -3)"
fi
