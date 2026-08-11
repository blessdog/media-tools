#!/bin/bash
# Bongpot Wan 2.2 rig — Vast onstart provisioning (roll-our-own, official base)
# ─────────────────────────────────────────────────────────────────────────────
# The call-2 probe stack (docs/next-pipeline-research-2026-06.md): Wan 2.2 i2v
# A14B fp8 (motion shots, P3 claymation audition) + LongCat-Video-Avatar-1.5
# GGUF (mechanical lipsync, P1 gate) — BOTH via kijai's ComfyUI-WanVideoWrapper.
# kijai's own readme says use native nodes for plain i2v, but LongCat has no
# native path, so one wrapper ecosystem runs both; Comfy-Org native repackage
# is the documented fallback lane if a wrapper update breaks (saves nothing to
# pre-download it — +36GB).
#
# Same base + same hard-won structure as provision-ltx.sh (official PyTorch
# image, supervisord babysitter, idempotent everything, honest markers):
#   /var/log/prov.marker   = COMFY_UP | INSTALL_FAILED
#   /var/log/models.marker = MODELS_DONE | MODELS_FAILED
#
# Manifest verified 2026-06-10 (HEAD 200 / HF tree listings) — every URL below
# was checked before it was written here. ~63GB total, no HF token required;
# CIVITAI_TOKEN (onstart env) is only needed for the LuisaP stop-motion alt LoRA.
set -euo pipefail

COMFY=/ComfyUI
PIP="python3 -m pip install --break-system-packages -q"
trap 'echo "INSTALL_FAILED (line $LINENO)" > /var/log/prov.marker' ERR

# 1. SSH key (bare base does not auto-inject; do it ourselves).
mkdir -p /root/.ssh && chmod 700 /root/.ssh
KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINNIPg4MRGLoqqO9AqtUVslYTVKbCD+RMp2jAebuMZrR rfanselman@gmail.com"
grep -qF "$KEY" /root/.ssh/authorized_keys 2>/dev/null || echo "$KEY" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# 2. System packages.
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git wget aria2 supervisor curl unzip \
  libxcb1 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 > /var/log/prov-apt.log 2>&1

# 3. ComfyUI core (idempotent). Wrapper tracks current comfy_api io schema →
#    clone tip now; pin BOTH at known-good SHAs once the box renders (standing
#    clone-at-pin rule, memory project_pin_comfyui_for_node_packs).
[ -d "$COMFY/.git" ] || git clone --depth 1 \
  https://github.com/comfyanonymous/ComfyUI.git "$COMFY" > /var/log/prov.log 2>&1
cd "$COMFY"
$PIP -r requirements.txt >> /var/log/prov.log 2>&1

# 4. Node packs. WanVideoWrapper = the engine (Wan 2.2 i2v + LongCat-Avatar-1.5;
#    LongCat support landed 2026-05-23, commit 5437b01 — tip required, .gguf loads
#    in its own model loader, NO ComfyUI-GGUF pack needed). MelBandRoFormer =
#    vocal separation for the avatar workflow. KJNodes + VideoHelperSuite = the
#    util nodes every kijai example workflow leans on.
for repo in kijai/ComfyUI-WanVideoWrapper kijai/ComfyUI-MelBandRoFormer kijai/ComfyUI-KJNodes Kosinkadink/ComfyUI-VideoHelperSuite; do
  name=$(basename "$repo")
  [ -d "custom_nodes/$name/.git" ] || git clone --depth 1 \
    "https://github.com/$repo.git" "custom_nodes/$name" >> /var/log/prov.log 2>&1
  [ -f "custom_nodes/$name/requirements.txt" ] && $PIP -r "custom_nodes/$name/requirements.txt" >> /var/log/prov.log 2>&1
done

# 5. supervisord: ComfyUI as a managed service.
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

# 6. Wait for ComfyUI to answer, stamp the marker.
for i in $(seq 1 50); do
  if curl -s -m 5 -o /dev/null http://127.0.0.1:8188/ 2>/dev/null; then
    echo "COMFY_UP" > /var/log/prov.marker
    break
  fi
  sleep 6
  [ "$i" -eq 50 ] && { echo "INSTALL_FAILED (:8188 never answered)" > /var/log/prov.marker; exit 1; }
done

# 7. Models (after ComfyUI is up; idempotent skip-if-present).
fetch() {  # fetch <url> <comfy-subdir> [rename]
  local url="$1" sub="$2" rename="${3:-}"
  local fname="${rename:-$(basename "${url%%\?*}")}"
  local dir="$COMFY/models/$sub" target
  mkdir -p "$dir"; target="$dir/$fname"
  if [ -f "$target" ]; then echo "✓ cached $sub/$fname" >> /var/log/prov.log; return 0; fi
  echo "↓ $sub/$fname" >> /var/log/prov.log
  wget -q --show-progress -O "$target" "$url" 2>> /var/log/prov.log \
    || { rm -f "$target"; echo "FAILED $url" >> /var/log/prov.log; return 1; }
}

set +e  # one model failure shouldn't abort the rest; the marker reports honestly
KJM="https://huggingface.co/Kijai/WanVideo_comfy/resolve/main"

# Wan 2.2 i2v A14B fp8-scaled MoE (high+low) — the motion engine. ~30GB.
fetch "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors" diffusion_models
fetch "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors" diffusion_models
fetch "$KJM/umt5-xxl-enc-fp8_e4m3fn.safetensors" text_encoders
# GOTCHA: Wan 2.2 14B MoE uses the WAN **2.1** VAE (2.2 VAE is only for the 5B TI2V).
fetch "$KJM/Wan2_1_VAE_bf16.safetensors" vae

# lightx2v 4-step distill LoRAs (high+low) — the speed lane. ~1.3GB.
fetch "$KJM/LoRAs/Wan22_Lightx2v/Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_260412_rank_64_fp16.safetensors" loras
fetch "$KJM/LoRAs/Wan22_Lightx2v/Wan_2_2_I2V_A14B_LOW_lightx2v_4step_lora_260412_rank_64_fp16.safetensors" loras

# LongCat-Video-Avatar-1.5 — the lipsync engine (P1). Q8_0 fits 48GB w/ block
# swap. Whisper encoder feeds LongCatAvatarWhisperEmbeds; dmd_lora = 8-step
# distill (stack via WanVideoLoraSelect if the GGUF isn't pre-merged — open
# question from the manifest); MelBandRoformer = vocal separation. ~24GB.
fetch "https://huggingface.co/vantagewithai/LongCat-Video-Avatar-1.5-GGUF-ComfyUI/resolve/main/LongCat-Avatar-15_comfy-Q8_0.gguf" diffusion_models
fetch "$KJM/HuMo/whisper_large_v3_encoder_fp16.safetensors" audio_encoders
fetch "https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/resolve/main/lora/dmd_lora.safetensors" loras "LongCat-Avatar-1.5_dmd_lora.safetensors"
fetch "https://huggingface.co/Kijai/MelBandRoFormer_comfy/resolve/main/MelBandRoformer_fp16.safetensors" diffusion_models

# Claymation LoRAs (P3 lead style). Civitai 1659949 v2.0 Wan2.2-I2V ships as a
# ZIP (public, no token as of 2026-06-10); unzip into its own subdir for
# idempotence. LuisaP stop-motion alt (2105908) is token-gated — fetched only
# if CIVITAI_TOKEN is in the onstart env.
CLAY_DIR="$COMFY/models/loras/wan-claymation"
if [ ! -d "$CLAY_DIR" ] || [ -z "$(ls -A "$CLAY_DIR" 2>/dev/null)" ]; then
  mkdir -p "$CLAY_DIR"
  curl -sL "https://civitai.com/api/download/models/2234375" -o /tmp/clay.zip \
    && unzip -o /tmp/clay.zip -d "$CLAY_DIR" >> /var/log/prov.log 2>&1 \
    && rm -f /tmp/clay.zip \
    || echo "FAILED claymation zip (civitai 2234375)" >> /var/log/prov.log
fi
if [ -n "${CIVITAI_TOKEN:-}" ]; then
  [ -f "$COMFY/models/loras/wan2.2STOPMOTION_v2_high_noise.safetensors" ] || curl -sL \
    "https://civitai.com/api/download/models/2382461?token=$CIVITAI_TOKEN" \
    -o "$COMFY/models/loras/wan2.2STOPMOTION_v2_high_noise.safetensors"
  [ -f "$COMFY/models/loras/wan2.2STOPMOTION_v2_low_noise.safetensors" ] || curl -sL \
    "https://civitai.com/api/download/models/2382506?token=$CIVITAI_TOKEN" \
    -o "$COMFY/models/loras/wan2.2STOPMOTION_v2_low_noise.safetensors"
fi
echo "MODELS_DONE" > /var/log/models.marker

# 8. Restart ComfyUI so it indexes the fresh models.
supervisorctl restart comfyui >/dev/null 2>&1 || true
echo "provisioning finished (wan stack)" >> /var/log/prov.log
