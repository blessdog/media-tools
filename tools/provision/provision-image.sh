#!/bin/bash
# Bongpot IMAGE rig — Vast onstart provisioning for the Pass-1 STILLS harness.
# ─────────────────────────────────────────────────────────────────────────────
# The still-side sibling of provision-ltx.sh. Stands up ComfyUI + the PuLID-Flux
# coherence node on a cheap 24GB card so we can generate identity-locked, watercolor
# keyframe stills (the i2v first frames). Lead recipe: PuLID-Flux on Flux.1-dev (fp8)
# via the FaceNet path (no InsightFace compilation pain) + a watercolor LoRA later.
#
# Same hard-won patterns as the LTX script: official pytorch base, supervisord keeps
# ComfyUI alive across disconnects, --break-system-packages, idempotent clones/downloads,
# honest markers. The finicky face deps are best-effort (continue on failure) and finished
# live over SSH if needed — ComfyUI coming up is what the marker guarantees.
#
# Markers:  /var/log/prov.marker = COMFY_UP | INSTALL_FAILED   ·  /var/log/models.marker = MODELS_DONE | MODELS_FAILED
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

# 3. ComfyUI core (idempotent).
[ -d "$COMFY/.git" ] || git clone --depth 1 \
  https://github.com/comfyanonymous/ComfyUI.git "$COMFY" > /var/log/prov.log 2>&1
cd "$COMFY"
$PIP -r requirements.txt >> /var/log/prov.log 2>&1

# 4. ComfyUI-Manager (lets us add/repair nodes live) + the PuLID-Flux node pack.
[ -d custom_nodes/ComfyUI-Manager/.git ] || git clone --depth 1 \
  https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager >> /var/log/prov.log 2>&1
[ -d custom_nodes/ComfyUI_PuLID_Flux_ll/.git ] || git clone --depth 1 \
  https://github.com/lldacing/ComfyUI_PuLID_Flux_ll.git custom_nodes/ComfyUI_PuLID_Flux_ll >> /var/log/prov.log 2>&1

# 5. PuLID-Flux python deps — FaceNet path (commercial-friendly, NO InsightFace compile).
#    best-effort: a failed face dep must NOT abort ComfyUI coming up (we finish live).
set +e
$PIP facenet-pytorch --no-deps >> /var/log/prov.log 2>&1
$PIP facexlib timm onnxruntime ftfy >> /var/log/prov.log 2>&1
[ -f custom_nodes/ComfyUI_PuLID_Flux_ll/requirements.txt ] && \
  $PIP -r custom_nodes/ComfyUI_PuLID_Flux_ll/requirements.txt >> /var/log/prov.log 2>&1
set -e

# 6. supervisord: run ComfyUI as a managed service on :8188.
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

# 7. Wait for ComfyUI to actually answer, then stamp COMFY_UP.
for i in $(seq 1 50); do
  if curl -s -m 5 -o /dev/null http://127.0.0.1:8188/ 2>/dev/null; then echo "COMFY_UP" > /var/log/prov.marker; break; fi
  sleep 6
  [ "$i" -eq 50 ] && { echo "INSTALL_FAILED (:8188 never answered)" > /var/log/prov.marker; exit 1; }
done

# 8. Models — the lead-recipe manifest (downloaded AFTER ComfyUI is up; persist on disk).
fetch() {  # fetch <url> <comfy-subdir> [rename]
  local url="$1" sub="$2" rename="${3:-}"
  local fname="${rename:-$(basename "${url%%\?*}")}"
  local dir="$COMFY/models/$sub" target
  mkdir -p "$dir"; target="$dir/$fname"
  if [ -f "$target" ]; then echo "✓ cached $sub/$fname" >> /var/log/prov.log; return 0; fi
  local auth=()
  [ -n "${HF_TOKEN:-}" ] && [[ "$url" == *huggingface.co* ]] && auth=(--header="Authorization: Bearer $HF_TOKEN")
  echo "↓ $sub/$fname" >> /var/log/prov.log
  wget "${auth[@]}" -q -O "$target" "$url" 2>> /var/log/prov.log || { rm -f "$target"; echo "FAILED $url" >> /var/log/prov.log; return 1; }
}

set +e
# Flux.1-dev (fp8, all-in-one) — non-gated Comfy-Org mirror; CheckpointLoaderSimple loads MODEL+CLIP+VAE.
fetch "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" checkpoints
# PuLID-Flux identity model.
fetch "https://huggingface.co/guozinan/PuLID/resolve/main/pulid_flux_v0.9.1.safetensors" pulid
# EVA-CLIP for PuLID (node also auto-downloads, but cache it here).
fetch "https://huggingface.co/QuanSun/EVA-CLIP/resolve/main/EVA02_CLIP_L_336_psz14_s6B.pt" clip
RC=$?
[ $RC -eq 0 ] && echo "MODELS_DONE" > /var/log/models.marker || echo "MODELS_FAILED (see prov.log)" > /var/log/models.marker

# Watercolor LoRA is added LIVE (Civitai needs a token) → models/loras/. Deferred on purpose.

supervisorctl restart comfyui >/dev/null 2>&1 || true
echo "image provisioning finished" >> /var/log/prov.log
