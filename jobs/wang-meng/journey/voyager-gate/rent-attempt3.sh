#!/bin/bash
# Voyager gate attempt 3 — rent wrapper. Embeds provision-voyager-v3.sh into
# the box's onstart as a base64 data: URI (urlretrieve handles data: natively),
# so no gist/hosting is needed and the LTX default manifest never runs.
# Dry run by default (gpu-box contract); pass --rent to actually rent.
set -euo pipefail
T="$HOME/projects/media-tools/tools"
G="$HOME/projects/media-tools/jobs/wang-meng/journey/voyager-gate"
B64=$(base64 -i "$G/provision-voyager-v3.sh" | tr -d '\n')
exec node "$T/gpu-box.mjs" up \
  --gpu A100_SXM4 --min-vram 78 --max-price 1.40 --disk 120 \
  --image pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel \
  --provision-url "data:text/plain;base64,$B64" \
  "$@"
