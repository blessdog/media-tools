#!/bin/bash
# Gate A: Ge Hong crop → 360° equirectangular panorama, via HY-Pano-2.0 Backend 2
# (Qwen-Image-Edit-2509 + the HY-Pano LoRA).
#
# A/B on the prompt channel, SAME SEED, because the question is not "can it make
# a panorama" but "in whose visual language does it invent the part Wang Meng
# never painted". Run 1 gives it almost nothing to go on and lets the LoRA's own
# prior show. Run 2 loads the prompt with the painting's actual idiom. If run 2
# is the only one that reads as ink, that tells us the reference channel is weak
# here and the style is riding on text — which is the opposite of what we want.
set -euo pipefail

cd /HY-World-2.0/hyworld2/panogen   # relative import: `from qwen_image import ...`

BASE=/models/qwen-image-edit-2509
LORA=/models/hy-world-2.0
IMG=/work/gehong-1024.png
SEED=42

common=(--image "$IMG"
        --pretrained-model-name-or-path "$BASE"
        --lora-path "$LORA" --lora-subfolder HY-Pano-2.0
        --seed "$SEED")

echo "=== RUN 1/2 — minimal prompt (what does the LoRA do unaided) ==="
python3 pipeline_with_qwen_image.py "${common[@]}" \
  --prompt "A mountain landscape." \
  --save /work/pano-minimal.png

echo "=== RUN 2/2 — idiom-loaded prompt ==="
python3 pipeline_with_qwen_image.py "${common[@]}" \
  --prompt "A Yuan dynasty Chinese landscape painting on silk in the manner of Wang Meng: ink and pale mineral colour, dense hemp-fibre texture strokes over layered rock, ochre and muted blue-green pigment, pine and deciduous trees, a wooden trestle bridge over a rocky stream, large areas of bare unpainted silk reading as mist and water, no cast shadows, flat stacked recession." \
  --negative-prompt "photograph, 3d render, cgi, cast shadows, volumetric lighting, oil painting, thick impasto, saturated colour, digital art" \
  --save /work/pano-idiom.png

echo "=== DONE ==="
ls -la /work/pano-*.png
