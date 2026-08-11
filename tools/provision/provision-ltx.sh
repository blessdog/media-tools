#!/bin/bash
# Bongpot LTX-2.3 LipDub rig — Vast onstart provisioning (roll-our-own, official base)
# ─────────────────────────────────────────────────────────────────────────────
# Base image: pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime  (CUDA 12.8 / torch
# 2.11 — the tier LTX-2.3 fp8 actually needs; ai-dock's 12.1.1 is too old). Official
# PyTorch image + our own auditable provisioning — never a stranger's bundle.
#
# This is the production replacement for the bare-base flailing of 2026-06-03. The
# ONE problem that beat us then was keeping ComfyUI alive (nohup/tmux died on SSH
# disconnect). Fixed here with **supervisord** — a real daemon that starts ComfyUI,
# restarts it if it crashes, and survives our disconnects.
#
# Everything else is the hard-won knowledge from that day, encoded:
#   - python3 -m pip --break-system-packages   (PEP-668 silently eats bare pip)
#   - idempotent clones + downloads            (Vast re-runs onstart every start)
#   - kornia `pad` patch (upstream PR #498)    (kornia>=0.8.3 dropped the re-export)
#   - the exact LTX-2.3 LipDub model manifest  (correct folders: latent_upscale_models,
#                                               loras/ltxv/ltx2; fp8 needs separate audio VAE)
#
# Markers (so the box never lies about readiness):
#   /var/log/prov.marker   = COMFY_UP   (8188 answers) | INSTALL_FAILED
#   /var/log/models.marker = MODELS_DONE | MODELS_FAILED
set -euo pipefail

COMFY=/ComfyUI
PIP="python3 -m pip install --break-system-packages -q"
VARIANT="${LTX_VARIANT:-fp8}"   # fp8 (fast, needs separate audio VAE) | bf16 (audio bundled, heavy)
trap 'echo "INSTALL_FAILED (line $LINENO)" > /var/log/prov.marker' ERR

# 1. SSH key (bare base does not auto-inject; do it ourselves).
mkdir -p /root/.ssh && chmod 700 /root/.ssh
KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINNIPg4MRGLoqqO9AqtUVslYTVKbCD+RMp2jAebuMZrR rfanselman@gmail.com"
grep -qF "$KEY" /root/.ssh/authorized_keys 2>/dev/null || echo "$KEY" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# 2. System packages (supervisor = the process babysitter).
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git wget aria2 supervisor curl \
  libxcb1 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 > /var/log/prov-apt.log 2>&1

# 3. ComfyUI core (idempotent).
[ -d "$COMFY/.git" ] || git clone --depth 1 \
  https://github.com/comfyanonymous/ComfyUI.git "$COMFY" > /var/log/prov.log 2>&1
cd "$COMFY"
$PIP -r requirements.txt >> /var/log/prov.log 2>&1

# 4. LTX-2.3 node pack + KJNodes (idempotent). KJNodes is REQUIRED by the IA2V and
#    lipdub workflows (GetImageSizeAndCount, ResizeImageMaskNode, etc.).
[ -d custom_nodes/ComfyUI-LTXVideo/.git ] || git clone --depth 1 \
  https://github.com/Lightricks/ComfyUI-LTXVideo.git custom_nodes/ComfyUI-LTXVideo >> /var/log/prov.log 2>&1
$PIP -r custom_nodes/ComfyUI-LTXVideo/requirements.txt >> /var/log/prov.log 2>&1
[ -d custom_nodes/ComfyUI-KJNodes/.git ] || git clone --depth 1 \
  https://github.com/kijai/ComfyUI-KJNodes.git custom_nodes/ComfyUI-KJNodes >> /var/log/prov.log 2>&1
[ -f custom_nodes/ComfyUI-KJNodes/requirements.txt ] && $PIP -r custom_nodes/ComfyUI-KJNodes/requirements.txt >> /var/log/prov.log 2>&1

# 4b. LTX Director (WhatDreamsCost) — the timeline COCKPIT (per-shot prompts + refs +
#     durations + audio sync, all native). It REQUIRES latest LTXVideo + KJNodes, so
#     refresh those to tip first, then clone Director (idempotent). The kornia patch in
#     §5 re-applies after this update, so updating LTXVideo can't reintroduce that bug.
for r in ComfyUI-LTXVideo ComfyUI-KJNodes; do
  [ -d "custom_nodes/$r/.git" ] && ( cd "custom_nodes/$r" && git fetch -q --depth 1 origin && git checkout -qf FETCH_HEAD ) >> /var/log/prov.log 2>&1 || true
done
[ -d custom_nodes/WhatDreamsCost-ComfyUI/.git ] || git clone --depth 1 \
  https://github.com/WhatDreamsCost/WhatDreamsCost-ComfyUI.git custom_nodes/WhatDreamsCost-ComfyUI >> /var/log/prov.log 2>&1
[ -f custom_nodes/WhatDreamsCost-ComfyUI/requirements.txt ] && $PIP -r custom_nodes/WhatDreamsCost-ComfyUI/requirements.txt >> /var/log/prov.log 2>&1

# 5. kornia pad patch (PR #498) — pack imports `pad` from kornia, which >=0.8.3
#    removed; it is just torch.nn.functional.pad. Idempotent.
PB="$COMFY/custom_nodes/ComfyUI-LTXVideo/pyramid_blending.py"
if [ -f "$PB" ] && grep -qE "^[[:space:]]*pad,[[:space:]]*$" "$PB"; then
  sed -i "/^[[:space:]]*pad,[[:space:]]*$/d" "$PB"
  sed -i "/^from torch import Tensor/a from torch.nn.functional import pad" "$PB"
  echo "PATCHED kornia pad import (PR #498)" >> /var/log/prov.log
fi

# 6. supervisord: run ComfyUI as a managed service (the fix for the launch nightmare).
cat > /etc/supervisor/conf.d/comfyui.conf <<EOF
[program:comfyui]
command=python3 -u main.py --listen 127.0.0.1 --port 8188
directory=/ComfyUI
autostart=true
autorestart=true
startretries=9999
startsecs=20
stdout_logfile=/var/log/comfyui.log
stderr_logfile=/var/log/comfyui.log
EOF
pgrep -x supervisord >/dev/null || supervisord -c /etc/supervisor/supervisord.conf
supervisorctl reread >/dev/null 2>&1 || true
supervisorctl update >/dev/null 2>&1 || true
supervisorctl restart comfyui >/dev/null 2>&1 || true

# 7. Wait for ComfyUI to actually answer, then stamp the COMFY_UP marker.
for i in $(seq 1 50); do
  if curl -s -m 5 -o /dev/null http://127.0.0.1:8188/ 2>/dev/null; then
    echo "COMFY_UP" > /var/log/prov.marker
    break
  fi
  sleep 6
  [ "$i" -eq 50 ] && { echo "INSTALL_FAILED (:8188 never answered)" > /var/log/prov.marker; exit 1; }
done

# 8. Models — downloaded AFTER ComfyUI is up (it serves while these stream in).
#    Land directly in /ComfyUI/models/<folder> (persists on the Vast disk across
#    stop→start; idempotent skip-if-present). HF_TOKEN comes from the onstart env.
fetch() {  # fetch <url> <comfy-subdir> [rename]
  local url="$1" sub="$2" rename="${3:-}"
  local fname="${rename:-$(basename "${url%%\?*}")}"
  local dir="$COMFY/models/$sub" target
  mkdir -p "$dir"; target="$dir/$fname"
  if [ -f "$target" ]; then echo "✓ cached $sub/$fname" >> /var/log/prov.log; return 0; fi
  local auth=()
  [ -n "${HF_TOKEN:-}" ] && [[ "$url" == *huggingface.co* ]] && auth=(--header="Authorization: Bearer $HF_TOKEN")
  echo "↓ $sub/$fname" >> /var/log/prov.log
  wget "${auth[@]}" -q --show-progress -O "$target" "$url" 2>> /var/log/prov.log \
    || { rm -f "$target"; echo "FAILED $url" >> /var/log/prov.log; return 1; }
}

set +e  # a single model failure shouldn't abort the rest; we report via marker
if [ "$VARIANT" = "bf16" ]; then
  fetch "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-dev.safetensors" checkpoints
else
  fetch "https://huggingface.co/Lightricks/LTX-2.3-fp8/resolve/main/ltx-2.3-22b-dev-fp8.safetensors" checkpoints
  fetch "https://huggingface.co/unsloth/LTX-2.3-GGUF/resolve/main/vae/ltx-2.3-22b-dev_audio_vae.safetensors" checkpoints
fi
fetch "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp8_scaled.safetensors" text_encoders "comfy_gemma_3_12B_it.safetensors"
fetch "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-spatial-upscaler-x2-1.1.safetensors" latent_upscale_models
fetch "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-distilled-lora-384-1.1.safetensors" loras/ltxv/ltx2

# USO keyframe stack (tools/_uso.mjs graph): flux1-dev-fp8 + the USO identity/style
# conditioning set. The primary box renders keyframes AND clips; shards skip this.
if [ "${CLIPS_ONLY:-0}" != "1" ]; then
fetch "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" checkpoints
fetch "https://huggingface.co/Comfy-Org/USO_1.0_Repackaged/resolve/main/split_files/loras/uso-flux1-dit-lora-v1.safetensors" loras
fetch "https://huggingface.co/Comfy-Org/USO_1.0_Repackaged/resolve/main/split_files/model_patches/uso-flux1-projector-v1.safetensors" model_patches
fetch "https://huggingface.co/Comfy-Org/sigclip_vision_384/resolve/main/sigclip_vision_patch14_384.safetensors" clip_vision
fi

# CLIPS_ONLY=1 → a SHARD box for generate-clips --box vast, nothing else. That path
# overrides every model-filename input in the IA2V graph (applyBoxModelFix), so only
# the five files above are ever loaded; everything below is the Director / template /
# lipdub tooling (~18GB) that a render shard never touches. Skipping it cuts standup
# by ~5 min and the disk by ~18GB per shard.
if [ "${CLIPS_ONLY:-0}" != "1" ]; then
fetch "https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-LipDub/resolve/main/ltx-2.3-22b-ic-lora-lipdub-0.9.safetensors" loras/ltxv/ltx2

# IA2V (Image+Audio→Video) model variants — the PROVEN audio-driven path (see memory
# project_ia2v_is_the_lipsync_tool). The comfy.org video_ltx2_3_ia2v template wants these
# exact files: a dynamic distilled LoRA, the fp4_mixed Gemma encoder, and an abliterated
# Gemma LoRA for prompt-enhance (or set prompt_enhance off to skip the last).
fetch "https://huggingface.co/Comfy-Org/ltx-2.3/resolve/main/split_files/loras/ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors" loras
fetch "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors" text_encoders
fetch "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/loras/gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors" loras

# LTX Director (WhatDreamsCost) example-workflow models — Kijai/LTX2.3_comfy distribution.
# The Director graph names these exact files: the joint audio+video VAEs (the audio-driven
# lipsync path needs the audio VAE), the text projection, and the taeltx2_3 preview.
KJ="https://huggingface.co/Kijai/LTX2.3_comfy/resolve/main"
fetch "$KJ/vae/LTX23_audio_vae_bf16.safetensors" vae
fetch "$KJ/vae/LTX23_video_vae_bf16.safetensors" vae
fetch "$KJ/vae/taeltx2_3.safetensors" vae
fetch "$KJ/text_encoders/ltx-2.3_text_projection_bf16.safetensors" text_encoders
fi  # CLIPS_ONLY
RC=$?
[ $RC -eq 0 ] && echo "MODELS_DONE" > /var/log/models.marker || echo "MODELS_FAILED (see prov.log)" > /var/log/models.marker

# 9. Restart ComfyUI so it indexes the freshly-downloaded models.
supervisorctl restart comfyui >/dev/null 2>&1 || true
echo "provisioning finished (variant=$VARIANT)" >> /var/log/prov.log
