#!/bin/bash
# Gate A2: can HY-Pano hold 高遠 (gaoyuan, "high distance") when the container
# stops imposing a horizon?
#
# Gate A1 established that the ink survives but the COMPOSITION does not: an
# equirectangular panorama is defined by a horizon, and Wang Meng's scroll is
# built on the refusal of one. Recession there runs UP the picture plane.
#
# Two candidate causes, so this is a 2x2 minus one cell — isolate each lever:
#
#                     | square input (A1's) | vertical input 1:2.33
#   ------------------+---------------------+-----------------------
#   vertical canvas   |   run 1 (canvas)    |   run 2 (both)
#   square canvas     |        —            |   run 3 (input only)
#
#   run 1 vs A1  → does the OUTPUT canvas shape drive it?
#   run 3 vs A1  → does the REFERENCE image shape drive it?
#   run 2        → both levers, the best case
#
# If all three still come back as level-distance river valleys, the horizon is
# baked into the pano LoRA below the geometry, and Stage 1 is unusable for this
# painting no matter how it is framed. That is a clean negative and sends us to
# the Stage-3 bypass with the question settled instead of assumed.
set -euo pipefail
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

cd /HY-World-2.0/hyworld2/panogen

BASE=/models/qwen-image-edit-2509
LORA=/models/hy-world-2.0
SEED=42

PROMPT="A Yuan dynasty Chinese hanging scroll landscape in the manner of Wang Meng: tall vertical composition, high-distance 高遠 recession climbing up the picture plane, no horizon line, jammed overlapping cliffs and a narrow gorge, dense hemp-fibre texture strokes, ink and pale mineral colour, ochre and muted blue-green pigment, pine and deciduous trees, a wooden trestle bridge, waterfall, large areas of bare unpainted silk reading as mist and water, no cast shadows, flat stacked recession."
NEG="horizon line, wide river valley, open sky, level distance, panorama, photograph, 3d render, cgi, cast shadows, volumetric lighting, saturated colour"

run () {  # name  image  width  height
  echo "=== $1  (${3}x${4}, input $(basename "$2")) ==="
  python3 pipeline_with_qwen_image.py \
    --image "$2" \
    --pretrained-model-name-or-path "$BASE" \
    --lora-path "$LORA" --lora-subfolder HY-Pano-2.0 \
    --seed "$SEED" --width "$3" --height "$4" \
    --prompt "$PROMPT" --negative-prompt "$NEG" \
    --save "/work/$1.png" || echo "!! $1 FAILED (continuing)"
}

run vert1-canvas /work/gehong-1024.png       960 1952
run vert2-both   /work/gehong-vert-960.png   960 1952
run vert3-input  /work/gehong-vert-960.png  1408 1408

echo "=== DONE ==="
ls -la /work/vert*.png 2>/dev/null
