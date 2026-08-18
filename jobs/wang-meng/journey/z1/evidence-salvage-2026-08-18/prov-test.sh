#!/bin/bash
# Voyager gate attempt 3 — corrected after two measured failures (see
# MORNING-REPORT.md). Assumes the box was rented with a torch-2.4/cu12.4
# docker image (pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel), so no venv and
# no torch install happen here. Weights start FIRST (long pole).
#
# Everything below was verified OFFLINE on 2026-08-18 before renting:
#   - docker tag exists on Docker Hub (7.9GB)
#   - flash-attn v2.6.3 prebuilt wheels exist for cp310 AND cp311 (URL → 200)
#   - main requirements.txt pins checked; data_engine/requirements.txt pins
#     torch 2.3.1 → NEVER installed (would downgrade the box's torch)
#   - create_input.py needs only MoGe (+ numpy renderer); VGGT/Metric3D are
#     training-engine-only, skipped entirely
set -euo pipefail
cd /workspace

echo "=== [1/5] weights download starts immediately (parallel long pole) ==="
pip install -q "huggingface_hub[cli]"
mkdir -p /workspace/ckpts
nohup huggingface-cli download tencent/HunyuanWorld-Voyager \
  --local-dir /workspace/ckpts > /workspace/weights.log 2>&1 &
WPID=$!

echo "=== [2/5] repo + inference deps (torch lines filtered out) ==="
test -d HunyuanWorld-Voyager || git clone --depth 1 https://github.com/Tencent-Hunyuan/HunyuanWorld-Voyager
cd HunyuanWorld-Voyager
grep -viE '^(torch|torchvision|torchaudio)' requirements.txt > /tmp/req-safe.txt
pip install -q -r /tmp/req-safe.txt || {
  # pyexr needs OpenEXR; wheel usually suffices, apt lib is the fallback
  apt-get update -q && apt-get install -y -q libopenexr-dev
  pip install -q -r /tmp/req-safe.txt
}
pip install -q "transformers==4.39.3" "xfuser==0.4.2"

echo "=== [3/5] flash-attn: exact prebuilt wheel for THIS python, never a compile ==="
PYTAG="cp$(python3 -c 'import sys;print(f"{sys.version_info[0]}{sys.version_info[1]}")')"
FA="flash_attn-2.6.3+cu123torch2.4cxx11abiFALSE-${PYTAG}-${PYTAG}-linux_x86_64.whl"
wget -q "https://github.com/Dao-AILab/flash-attention/releases/download/v2.6.3/$FA"
pip install -q "./$FA"

echo "=== [4/5] MoGe for the conditions stage (the ONLY data_engine dep we need) ==="
cd data_engine
test -d MoGe || git clone --depth 1 https://github.com/microsoft/MoGe.git
pip install -q click scipy matplotlib trimesh \
  "git+https://github.com/EasternJournalist/utils3d.git@3fab839f0be9931dac7c8488eb0e1600c236e183"
cd ..

echo "=== [5/5] wait for weights + smoke ==="
wait $WPID
ln -sfn /workspace/ckpts ./ckpts
python3 - <<'EOF'
import torch, flash_attn
print("torch", torch.__version__, "| cuda", torch.cuda.is_available(),
      "|", torch.cuda.get_device_name(0))
EOF
cd data_engine && python3 -c "from MoGe.moge.model.v1 import MoGeModel; print('moge import ok')" && cd ..
echo "PROVISION-OK"
