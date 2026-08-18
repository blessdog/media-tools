#!/bin/zsh
# Animate the inkwash stills into clips. One tool call per shot, camera held
# (the paintings already have their composition; a roaming camera fights it).
# usage: ./animate.sh [shot-number ...]   (no args = all)
set -e
cd "$(dirname "$0")"
T=~/projects/media-tools/tools
mkdir -p clips

shots=("$@")
if [ ${#shots[@]} -eq 0 ]; then shots=(00 01 02 03 04 05 06 07 08); fi

for n in $shots; do
  still="renders/shot-$n.png"
  motion="motion/shot-$n.txt"
  [ -f "$still" ] || { echo "no $still — skipping"; continue; }
  [ -f "$motion" ] || { echo "no $motion — skipping"; continue; }
  node $T/image-to-video.mjs \
    --image "$still" \
    --prompt "$(cat $motion)" \
    --duration 5 \
    --out "clips/shot-$n.mp4" 2>&1 | tail -1
done
