#!/bin/bash
# Krea-2 rig — Vast onstart provisioning (roll-our-own, official base)
# ─────────────────────────────────────────────────────────────────────────────
# Written 2026-08-12 for the Krea-2 ink-wash test. This is a NEW project: it
# inherits NO assets, NO swatch and NO style strings from bongpot. The only
# things on this box are Krea-2, its text encoder and VAE, and the two ink
# LoRAs Ryan picked out himself.
#
# Why its own script: provision-ltx.sh pulls LTX's 29GB checkpoint before
# anything else and provision-wan.sh pulls ~63GB — both are dead weight here,
# and on a job whose whole stack is 18GB the download would cost more than the
# render. STATUS.md has been asking for a lean path since 2026-08-12.
#
# Same hard-won structure as its siblings (official PyTorch base, supervisord
# babysitter, idempotent everything, honest markers):
#   /var/log/prov.marker   = COMFY_UP | INSTALL_FAILED
#   /var/log/models.marker = MODELS_DONE | MODELS_FAILED
#
# Manifest verified 2026-08-12 by tools/preflight-models.mjs — every URL below
# returned 206 with no gate before it was written here. ~30GB with both bases.
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

# 3. ComfyUI core (idempotent). Krea-2 runs on NATIVE nodes — no wrapper pack,
#    which is why this box needs so little. Tip is required: Krea-2 support is
#    recent, and the official workflow template ships with ComfyUI itself.
[ -d "$COMFY/.git" ] || git clone --depth 1 \
  https://github.com/comfyanonymous/ComfyUI.git "$COMFY" > /var/log/prov.log 2>&1
cd "$COMFY"
$PIP -r requirements.txt >> /var/log/prov.log 2>&1

# 4. Node packs. Deliberately minimal — every custom node is a stranger's code
#    and the top cause of provisioning failure. KJNodes for utilities, Manager
#    so Ryan can browse the official Krea-2 template in the UI and export it.
for repo in kijai/ComfyUI-KJNodes ltdrdata/ComfyUI-Manager; do
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

# 6. Wait for ComfyUI to answer, stamp the marker. ComfyUI comes up BEFORE the
#    weights land, so the UI is reachable while the downloads run.
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
CO="https://huggingface.co/Comfy-Org/Krea-2/resolve/main"

# TURBO FIRST — it is what both LoRAs are tagged against (base_model:
# krea/Krea-2-Turbo), and darkbrush's every published preview is a *_turbo
# render. So turbo is the evidence-backed default, not a shortcut.
fetch "$CO/diffusion_models/krea2_turbo_fp8_scaled.safetensors" diffusion_models

# Text encoder (Qwen3-VL 4B) + VAE (Qwen's). Krea-2 is Qwen-adjacent underneath.
fetch "$CO/text_encoders/qwen3vl_4b_fp8_scaled.safetensors" text_encoders
fetch "$CO/vae/qwen_image_vae.safetensors" vae

# RAW — NOT a quality A/B against turbo (Ryan, 2026-08-12: "RAW is specifically
# intended for control and LoRA training"). Turbo is the inference model; raw is
# the substrate you fine-tune against and the one control conditioning targets.
# Pulled on the same box because the two jobs it unlocks are the project's next
# two problems:
#   1. training a style LoRA on frames Ryan approves in THIS project, instead of
#      inheriting a look from another one.
#   2. structural control (see thedeoxen/Krea-2-pose-controlnet, apache-2.0) —
#      the answer to a video model inventing motion when given none.
# 12GB now beats a second provisioning cycle later.
fetch "$CO/diffusion_models/krea2_raw_fp8_scaled.safetensors" diffusion_models

# The two ink LoRAs Ryan picked. Note the '-comfy' suffix on the linen scroll —
# the plain .safetensors in that repo is diffusers format and will not load.
fetch "https://huggingface.co/krea/Krea-2-LoRA-darkbrush/resolve/main/darkbrush.safetensors" loras
fetch "https://huggingface.co/ilkerzgi/krea-2-chinese-ink-linen-scroll-lora/resolve/main/chinese-ink-linen-scroll-comfy.safetensors" loras

# 8. Honest marker: did every expected file actually land?
MISSING=0
for f in \
  "diffusion_models/krea2_turbo_fp8_scaled.safetensors" \
  "diffusion_models/krea2_raw_fp8_scaled.safetensors" \
  "text_encoders/qwen3vl_4b_fp8_scaled.safetensors" \
  "vae/qwen_image_vae.safetensors" \
  "loras/darkbrush.safetensors" \
  "loras/chinese-ink-linen-scroll-comfy.safetensors" ; do
  [ -s "$COMFY/models/$f" ] || { echo "MISSING $f" >> /var/log/prov.log; MISSING=1; }
done
if [ "$MISSING" -eq 0 ]; then echo "MODELS_DONE" > /var/log/models.marker
else echo "MODELS_FAILED" > /var/log/models.marker; fi

du -sh "$COMFY/models"/* >> /var/log/prov.log 2>&1
echo "provisioning finished $(date -u +%FT%TZ)" >> /var/log/prov.log
