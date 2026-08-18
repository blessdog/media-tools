#!/bin/zsh
# Bake-off: one photograph, every ref-capable model, the LOCKED swatch as the
# style channel on all of them. Same source, same swatch, same instruction —
# so the ONLY variable is the model, and Ryan's eyes pick the winner.
#
# usage: ./run.sh
set -u
cd "${0:A:h}"
T=/Users/SSDrive/projects/media-tools/tools/restyle-image.mjs

models=(
  black-forest-labs/flux-2-pro
  black-forest-labs/flux-2-dev
  qwen/qwen-image-edit-plus
  flux-kontext-apps/multi-image-kontext-max
  bytedance/seedream-4.5
  google/nano-banana-2
)

pids=()
for m in $models; do
  name="${m##*/}"
  node "$T" --image source.png --style inkwash --model "$m" --out "$name.png" \
    > "logs-$name.txt" 2>&1 &
  pids+=($!)
  echo "launched $name (pid $!)"
done

fail=0
for p in $pids; do wait $p || fail=1; done

echo
for m in $models; do
  name="${m##*/}"
  if [[ -f "$name.png" ]]; then
    echo "OK    $name.png"
  else
    echo "FAIL  $name — $(tail -2 logs-$name.txt | tr '\n' ' ')"
  fi
done
exit $fail
