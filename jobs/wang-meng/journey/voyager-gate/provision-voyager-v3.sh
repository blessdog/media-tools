#!/bin/bash
# Voyager gate attempt 3 — corrected after two measured failures (see
# MORNING-REPORT.md). Assumes the box was rented with a torch-2.4/cu12.4/
# py3.11 docker image (pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel), so no
# venv and no torch install happen here. Weights start FIRST (long pole).
set -euo pipefail
cd /workspace

echo "=== [1/4] weights download starts immediately (parallel long pole) ==="
pip install -q "huggingface_hub[cli]"
mkdir -p /workspace/ckpts
nohup huggingface-cli download tencent/HunyuanWorld-Voyager \
  --local-dir /workspace/ckpts > /workspace/weights.log 2>&1 &
WPID=$!

echo "=== [2/4] repo + deps (py3.11 wheels exist for these) ==="
test -d HunyuanWorld-Voyager || git clone --depth 1 https://github.com/Tencent-Hunyuan/HunyuanWorld-Voyager
cd HunyuanWorld-Voyager
pip install -q -r requirements.txt || true
pip install -q "transformers==4.39.3" "xfuser==0.4.2" pandas

echo "=== [3/4] flash-attn: exact prebuilt wheel, never a compile ==="
FA=flash_attn-2.6.3+cu123torch2.4cxx11abiFALSE-cp311-cp311-linux_x86_64.whl
wget -q "https://github.com/Dao-AILab/flash-attention/releases/download/v2.6.3/$FA"
pip install -q "./$FA"

echo "=== [4/4] wait for weights + smoke ==="
wait $WPID
ln -sfn /workspace/ckpts ./ckpts
python - <<'EOF'
import torch, flash_attn, pandas
print("torch", torch.__version__, "| cuda", torch.cuda.is_available(),
      "|", torch.cuda.get_device_name(0))
EOF
echo "PROVISION-OK"
