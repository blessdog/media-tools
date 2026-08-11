#!/bin/bash
# Bongpot LTX rig — Vast onstart provisioning (the OFFICIAL path, our own auditable
# script — never a random community image; see memory
# feedback_official_images_not_random_bundles).
#
# Builds: official ComfyUI (current core, has comfy_api/latest → 2.3 nodes register)
# + the official Lightricks/ComfyUI-LTXVideo node pack, on a clean pytorch/CUDA base.
#
# Runs on a BARE pytorch base where:
#   - pip is PEP-668 "externally managed" → every install MUST pass
#     --break-system-packages or it is SILENTLY skipped (this exact gap left
#     ComfyUI 0.24's sqlalchemy dep missing and crashed boot, 2026-06-03).
#   - Vast re-runs onstart on EVERY container start (stop→start), so clones MUST be
#     idempotent or `git clone` into an existing dir aborts the boot under set -e.
#
# Marker contract (so the box can never LIE about being ready):
#   /var/log/prov.marker = INSTALL_DONE   → ONLY after :8188 actually answers
#   /var/log/prov.marker = INSTALL_FAILED → any step aborted (trap)
set -euo pipefail

COMFY_DIR=/ComfyUI
# Use `python3 -m pip`, NOT bare `pip`: on this base bare pip partially PEP-668-blocks
# even with --break-system-packages, leaving deps like SQLAlchemy missing; `python3 -m
# pip` installs into the exact interpreter that runs main.py and takes the override.
PIP="python3 -m pip install --break-system-packages -q"
MARKER=/var/log/prov.marker

# On ANY error, stamp FAILED so a watcher/poller knows the truth instead of hanging.
trap 'echo "INSTALL_FAILED (line $LINENO)" > "$MARKER"' ERR

# 1. SSH key (belt-and-suspenders; Vast injects account keys on supported images,
#    but a bare base may not run that entrypoint).
mkdir -p /root/.ssh && chmod 700 /root/.ssh
KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINNIPg4MRGLoqqO9AqtUVslYTVKbCD+RMp2jAebuMZrR rfanselman@gmail.com"
grep -qF "$KEY" /root/.ssh/authorized_keys 2>/dev/null || echo "$KEY" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# 2. System packages.
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git wget aria2 > /var/log/prov-apt.log 2>&1

# 3. ComfyUI core (idempotent: skip clone if already present from a prior start).
[ -d "$COMFY_DIR/.git" ] || git clone --depth 1 \
  https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR" > /var/log/prov.log 2>&1
cd "$COMFY_DIR"
$PIP -r requirements.txt >> /var/log/prov.log 2>&1

# 4. LTXVideo node pack (idempotent).
[ -d custom_nodes/ComfyUI-LTXVideo/.git ] || git clone --depth 1 \
  https://github.com/Lightricks/ComfyUI-LTXVideo.git custom_nodes/ComfyUI-LTXVideo >> /var/log/prov.log 2>&1
$PIP -r custom_nodes/ComfyUI-LTXVideo/requirements.txt >> /var/log/prov.log 2>&1

# 5. Launch ComfyUI (127.0.0.1 only — reached via SSH tunnel, never exposed to the
#    internet). python3 is the base binary.
pkill -f main.py 2>/dev/null || true
sleep 1
nohup python3 main.py --listen 127.0.0.1 --port 8188 > /var/log/comfy.log 2>&1 &

# 6. Marker is written ONLY after :8188 actually answers (node import can take ~2-3
#    min). Until then the box is NOT ready, and we don't pretend it is.
for i in $(seq 1 40); do
  if curl -s -m 5 -o /dev/null http://127.0.0.1:8188/ 2>/dev/null; then
    echo "INSTALL_DONE" > "$MARKER"
    exit 0
  fi
  sleep 6
done
echo "INSTALL_FAILED (:8188 never answered)" > "$MARKER"
exit 1
