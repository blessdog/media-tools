#!/bin/bash
# media-tools HUNYUAN 1.5 I2V rig — Vast onstart provisioning for the motion renderer.
# ─────────────────────────────────────────────────────────────────────────────
# Stands up ComfyUI + the exact five files tools/_hunyuan.mjs's graph loads, so
# `image-to-video.mjs --provider comfy` (the default, the good one) has a box to
# talk to. Before this script the manifest lived nowhere — the 2026-08-12 timing
# in benchmarks.json came off a box provisioned BY HAND, which meant the good
# renderer could not be stood up twice. That is what this fixes.
#
# SIZING (do not rent a 48GB card for this): benchmarks.json records the 720p
# fp16 workload at 43.3/49GB MEASURED on a 6000 Ada — already offloading — so
# 48GB is the floor and not a comfortable one. plan-gpu asks for >=53GB and
# picks an 80GB card; H100_SXM came out both cheapest-per-job and fastest.
#
# Manifest verified against the HF tree API 2026-08-13 (every path + size below
# was listed before it was written here). ~30GB total. Needs HF_TOKEN in the
# onstart env only for rate-limit headroom; the repo itself is not gated.
#
# Markers:  /var/log/prov.marker   = COMFY_UP | INSTALL_FAILED
#           /var/log/models.marker = MODELS_DONE | MODELS_FAILED
#
# Then, from the laptop:  ssh -L 8189:localhost:8188 -p <port> root@<host>
# and image-to-video.mjs finds it at its default http://127.0.0.1:8189.
set -euo pipefail

COMFY=/ComfyUI
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
apt-get install -y -qq git wget aria2 supervisor curl \
  libxcb1 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 > /var/log/prov-apt.log 2>&1

# 3. ComfyUI core (idempotent). HunyuanVideo 1.5 uses NATIVE nodes
#    (UNETLoader / DualCLIPLoader type=hunyuan_video_15 / HunyuanVideo15ImageToVideo)
#    so there is no custom node pack to install and no wrapper to break.
[ -d "$COMFY/.git" ] || git clone --depth 1 \
  https://github.com/comfyanonymous/ComfyUI.git "$COMFY" > /var/log/prov.log 2>&1
cd "$COMFY"
$PIP -r requirements.txt >> /var/log/prov.log 2>&1

# 4. supervisord: keep ComfyUI alive across SSH disconnects.
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

# 5. Wait for ComfyUI to actually answer, then stamp COMFY_UP.
for i in $(seq 1 50); do
  if curl -s -m 5 -o /dev/null http://127.0.0.1:8188/ 2>/dev/null; then echo "COMFY_UP" > /var/log/prov.marker; break; fi
  sleep 6
  [ "$i" -eq 50 ] && { echo "INSTALL_FAILED (:8188 never answered)" > /var/log/prov.marker; exit 1; }
done

# 6. Models — exactly what buildHunyuanI2VGraph loads, nothing else.
fetch() {  # fetch <url> <comfy-subdir>
  local url="$1" sub="$2"
  local fname; fname="$(basename "${url%%\?*}")"
  local dir="$COMFY/models/$sub" target
  mkdir -p "$dir"; target="$dir/$fname"
  if [ -f "$target" ]; then echo "✓ cached $sub/$fname" >> /var/log/prov.log; return 0; fi
  local auth=()
  [ -n "${HF_TOKEN:-}" ] && [[ "$url" == *huggingface.co* ]] && auth=(--header=Authorization:\ Bearer\ "$HF_TOKEN")
  echo "↓ $sub/$fname" >> /var/log/prov.log
  aria2c -q -x8 -s8 --allow-overwrite=true -d "$dir" -o "$fname" "$url" >> /var/log/prov.log 2>&1 \
    || wget "${auth[@]}" -q -O "$target" "$url" 2>> /var/log/prov.log \
    || { rm -f "$target"; echo "FAILED $url" >> /var/log/prov.log; return 1; }
}

R=https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/split_files
set +e
fetch "$R/diffusion_models/hunyuanvideo1.5_720p_i2v_fp16.safetensors" diffusion_models   # 16.65 GB
fetch "$R/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"        text_encoders      #  9.38 GB
fetch "$R/text_encoders/byt5_small_glyphxl_fp16.safetensors"          text_encoders      #  0.44 GB
fetch "$R/vae/hunyuanvideo15_vae_fp16.safetensors"                    vae                #  2.52 GB
fetch "$R/clip_vision/sigclip_vision_patch14_384.safetensors"         clip_vision
RC=$?
set -e
[ $RC -eq 0 ] && echo "MODELS_DONE" > /var/log/models.marker || echo "MODELS_FAILED (see prov.log)" > /var/log/models.marker

supervisorctl restart comfyui >/dev/null 2>&1 || true
echo "hunyuan 1.5 i2v provisioning finished" >> /var/log/prov.log
