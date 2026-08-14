#!/bin/bash
# media-tools HY-WORLD rig — Vast onstart provisioning for HY-Pano-2.0 (Backend 2).
# ─────────────────────────────────────────────────────────────────────────────
# Purpose: single image → 360° equirectangular panorama, as gate A of the
# "can a world model invent in Wang Meng's language" test. If the invented
# 270° comes back as generic render, gate B (WorldMirror → 3DGS → camera push)
# is not worth provisioning, so this script deliberately installs ONLY what
# gate A needs and leaves the 3DGS half best-effort.
#
# WHY BACKEND 2 AND NOT BACKEND 1:
#   HY-Pano-2.0's headline backend is HunyuanImage-3 — 80B params (13B active
#   MoE), which Tencent specs at 8x40GB or 4x80GB. That is a four-H100 job and
#   is NOT what the consumer-GPU blog posts about this model are describing.
#   Backend 2 is a diffusers pipeline: Qwen-Image-Edit-2509 (~20B) plus a LoRA
#   adapter shipped in the HY-World-2.0 repo under HY-Pano-2.0/. At bf16 that
#   is ~40GB of weights, so this wants a 45-48GB card (L40S / A6000 / 6000 Ada).
#   On anything smaller, diffusers CPU offload is the fallback and it is slow.
#
# Same hard-won patterns as the sibling provisioners: official pytorch base,
# --break-system-packages, idempotent clones/downloads, honest markers, and
# finicky deps are best-effort so a failed extra never blocks the main path.
#
# Markers:  /var/log/prov.marker   = PANO_READY | INSTALL_FAILED
#           /var/log/models.marker = MODELS_DONE | MODELS_FAILED
set -euo pipefail

REPO=/HY-World-2.0
PIP="python3 -m pip install --break-system-packages -q"
trap 'echo "INSTALL_FAILED (line $LINENO)" > /var/log/prov.marker' ERR

# 1. SSH key (bare base does not auto-inject).
mkdir -p /root/.ssh && chmod 700 /root/.ssh
KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINNIPg4MRGLoqqO9AqtUVslYTVKbCD+RMp2jAebuMZrR rfanselman@gmail.com"
grep -qF "$KEY" /root/.ssh/authorized_keys 2>/dev/null || echo "$KEY" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# 2. System packages.
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git git-lfs wget aria2 curl \
  libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 > /var/log/prov-apt.log 2>&1

# 3. Clone (idempotent). Submodules are a gate-B concern; skip them here.
[ -d "$REPO/.git" ] || git clone --depth 1 \
  https://github.com/Tencent-Hunyuan/HY-World-2.0.git "$REPO" > /var/log/prov.log 2>&1
cd "$REPO"

# 4. Core python deps.
#
# DO NOT `pip install -r requirements.txt` (measured 2026-08-13, cost a reboot).
# Two traps in it:
#   a) It pins open3d==0.18.0, which has no wheel for Python 3.12 — and the
#      pytorch:2.11.0-cuda12.8 base ships 3.12, while HY-World's README assumes
#      a 3.11.15 conda env. The install dies there and takes the whole run with it.
#   b) open3d/gsplat/navmesh are the POINT-CLOUD half — gate B. The panorama
#      backend imports only torch, diffusers, numpy and PIL (verified by reading
#      panogen/pipeline_with_qwen_image.py's import block on the box).
# So gate A installs its real dependency set explicitly. If gate B is ever
# provisioned, give it a proper python 3.11 conda env per the README rather
# than fighting 3.12.
#
# setuptools is PINNED: torch 2.11 requires <82, and a bare `pip -U setuptools`
# installs 84 and leaves a broken resolver state.
$PIP -U pip wheel >> /var/log/prov.log 2>&1
$PIP "setuptools<82" >> /var/log/prov.log 2>&1
$PIP "diffusers>=0.36" transformers accelerate peft safetensors sentencepiece \
     huggingface_hub hf_transfer einops opencv-python-headless numpy pillow >> /var/log/prov.log 2>&1

# 5. FlashAttention — best-effort. It is a long source build on non-Hopper cards
#    and the diffusers backend runs (slower) on SDPA without it. A failed build
#    must not cost us the box.
set +e
$PIP flash-attn --no-build-isolation >> /var/log/prov.log 2>&1
[ $? -eq 0 ] && echo "flash-attn OK" >> /var/log/prov.log || echo "flash-attn SKIPPED (SDPA fallback)" >> /var/log/prov.log
set -e

# 6. Gate B (gsplat rasteriser, navmesh, open3d) is deliberately NOT installed
#    here — see the note in step 4. It needs its own python 3.11 env and is only
#    worth standing up if gate A's panorama comes back reading as ink.

echo "PANO_READY" > /var/log/prov.marker

# 7. Weights. Pre-pulled so that PANO_READY genuinely means "can run", rather
#    than "will start a 40GB download the first time you hit enter".
#      Qwen-Image-Edit-2509  — the ~20B diffusers base  (~40GB bf16)
#      HY-Pano-2.0/pytorch_lora_weights.safetensors — the panorama adapter (850MB)
#
# THE INCLUDE PATTERN IS LOAD-BEARING: do NOT use --include "HY-Pano-2.0/*" (measured
# 2026-08-13; it ate 86GB before being killed). Despite the name and despite
# what DOCUMENTATION.md implies by passing `--lora-subfolder HY-Pano-2.0`, that
# folder on HF is the BACKEND-1 model — HunyuanImage-3, 80B, 32 shards, ~170GB.
# Backend 2 reads exactly ONE file out of it, hardcoded in
# panogen/pipeline_with_qwen_image.py:153 as weight_name=
# "pytorch_lora_weights.safetensors". Fetch that file and nothing else.
set +e
export HF_HUB_ENABLE_HF_TRANSFER=1
hf download Qwen/Qwen-Image-Edit-2509 \
  --local-dir /models/qwen-image-edit-2509 >> /var/log/models.log 2>&1
Q=$?
hf download tencent/HY-World-2.0 \
  --include "HY-Pano-2.0/pytorch_lora_weights.safetensors" \
  --local-dir /models/hy-world-2.0 >> /var/log/models.log 2>&1
L=$?
set -e
if [ $Q -eq 0 ] && [ $L -eq 0 ]; then echo "MODELS_DONE" > /var/log/models.marker
else echo "MODELS_FAILED (qwen=$Q lora=$L)" > /var/log/models.marker; fi

# ── how to run gate A once this box is READY ────────────────────────────────
#   scp the crop up, then:
#     cd /HY-World-2.0/hyworld2/worldgen   # (wherever pipeline_with_qwen_image.py lives)
#     python pipeline_with_qwen_image.py \
#       --image /work/gehong-1024.png \
#       --pretrained-model-name-or-path /models/qwen-image-edit-2509 \
#       --lora-path /models/hy-world-2.0 --lora-subfolder HY-Pano-2.0 \
#       --prompt "..." --seed 42 --save /work/pano.png
#
#   What we are reading in the output, in priority order:
#     1. Does the INVENTED arc (the ~270° with no painting under it) read as
#        ink and colour on silk, or as a render of a mountain?
#     2. Does it leave 留白 — bare paper as water/mist — or does it fill every
#        empty region with substance? Filling it is the classic AI-ink tell.
#     3. Do the brush conventions survive: contour line, texture strokes,
#        the flat stacked recession? Or does it introduce cast shadow and
#        photographic aerial perspective the scroll never had?
