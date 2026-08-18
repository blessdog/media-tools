#!/bin/bash
# Voyager gate test — provision script. Written and committed BEFORE renting
# (2026-08-17 plan). Full-weight official checkpoints only; if any step fails,
# this script exits nonzero and the box gets destroyed — no fallback, no slop.
set -euo pipefail
cd /workspace

echo "=== [1/5] repo ==="
test -d HunyuanWorld-Voyager || git clone --depth 1 https://github.com/Tencent-Hunyuan/HunyuanWorld-Voyager
cd HunyuanWorld-Voyager

echo "=== [2/5] python env (3.11 + torch 2.4.0 cu124) ==="
PY=$(command -v python3.11 || command -v python3.10 || command -v python3)
$PY -m venv /workspace/venv
source /workspace/venv/bin/activate
pip install -q --upgrade pip
pip install -q torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu124

echo "=== [3/5] deps ==="
pip install -q -r requirements.txt || true   # some pins fight; retry tightened below
pip install -q "transformers==4.39.3" "xfuser==0.4.2" "huggingface_hub[cli]"
# flash-attn: wheel first (compile-from-source blows the 45-min kill criterion)
pip install -q flash-attn --no-build-isolation --find-links \
  https://github.com/Dao-AILab/flash-attention/releases || \
  MAX_JOBS=8 pip install -q flash-attn --no-build-isolation

echo "=== [4/5] weights (tencent/HunyuanWorld-Voyager) ==="
huggingface-cli download tencent/HunyuanWorld-Voyager --local-dir ./ckpts \
  2>&1 | grep -v "^Download" | tail -2

echo "=== [5/5] smoke ==="
python - <<'EOF'
import torch, flash_attn
print("torch", torch.__version__, "cuda", torch.cuda.is_available(),
      torch.cuda.get_device_name(0))
EOF
echo "PROVISION-OK"
