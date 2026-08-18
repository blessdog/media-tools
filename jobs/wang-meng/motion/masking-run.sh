#!/bin/zsh
# The masking test, 2026-08-14. Locked camera; any camera move belongs to
# render-parallax.py afterwards, where the transform is known instead of guessed.
# That is what keeps a static stencil registered for all 73 frames.
#
# ONE variable across the three clips: the prompt. Same seed, same sampler, same
# cfg. Yesterday's finding was that naming a physical substance retrieves
# photographic FOOTAGE of that substance, because that is what dominates
# training. A and B test whether the retrieval key can be aimed somewhere else by
# naming the MEDIUM (ink, brush, line) instead of the material (water).
#
#   A  substance named      — predicted to go photographic
#   B  medium named         — the theory's prediction: safe
#   C  medium named, leaves — the other half of Ryan's brief
set -e
cd "$(dirname "$0")"
T=../../../tools/image-to-video.mjs
NEG="photograph, photorealistic, real water, video footage, live action, cinematic lighting, film grain, 3d render, depth of field, motion blur, morphing, texture dissolving"
COMMON=(--image shot-real.png --width 720 --height 1280 --fps 24 --duration 3
        --steps 20 --cfg 3 --seed 42 --negative "$NEG" --host http://127.0.0.1:8189)

echo "── A: substance named ─────────────────────────────────"
node $T "${COMMON[@]}" --out mask-A-substance.mp4 \
  --prompt "the water flows and ripples across the surface. the camera does not move."

echo "── B: medium named ────────────────────────────────────"
node $T "${COMMON[@]}" --out mask-B-medium.mp4 \
  --prompt "the painted ink lines of the current drift slowly downstream across the bare silk. the brushwork stays flat ink on silk. the camera does not move."

echo "── C: medium named, foliage ───────────────────────────"
node $T "${COMMON[@]}" --out mask-C-leaves.mp4 \
  --prompt "the inked leaves and pine needles sway gently, the brush strokes shifting a little as if in a slow breeze. flat ink and colour on silk. the camera does not move."

echo "done. clips: mask-A-substance.mp4 mask-B-medium.mp4 mask-C-leaves.mp4"
