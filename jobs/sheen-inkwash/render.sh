#!/bin/zsh
# Render described shots through the real inkwash renderer (USO on the box).
# usage: ./render.sh [shot-number ...]   (no args = all)
set -e
cd "$(dirname "$0")"
T=~/projects/media-tools/tools
mkdir -p renders

# dephoto.sh drops the header AND the camera language — describe-video writes for
# a camera, this renderer paints. Feeding its prose in raw is what produced the
# airbrushed faces Ryan caught on 2026-08-12.
strip_header() { ./dephoto.sh "$1"; }

shots=("$@")
if [ ${#shots[@]} -eq 0 ]; then shots=(00 01 02 03 04 05 06 07 08); fi

for n in $shots; do
  f="regen/shot-$n.txt"
  [ -f "$f" ] || { echo "no $f — skipping"; continue; }
  p="$(strip_header "$f")"
  [ -n "$p" ] || { echo "$f is empty — skipping"; continue; }
  node $T/generate-image.mjs --style inkwash --provider comfy \
    --prompt "$p" --out "renders/shot-$n.png" 2>&1 | tail -1
  open "$PWD/renders/shot-$n.png"
done
