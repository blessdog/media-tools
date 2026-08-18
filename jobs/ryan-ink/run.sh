#!/bin/zsh
# Candidates for THIS project. Nothing inherited.
#
# --raw means style.json is never read: no bongpot swatch, no bongpot prompt
# strings, no "winner" from another project. Every look below is written fresh
# here and is a CANDIDATE ONLY. Nothing is approved until Ryan says so.
#
# usage: ./run.sh
set -u
cd "${0:A:h}"
T=/Users/SSDrive/projects/media-tools/tools/restyle-image.mjs

typeset -A LOOKS
LOOKS[01-mono-minimal]="Repaint this photograph as a monochrome ink painting on white paper. Black ink only, no colour. Large areas of the paper left completely unpainted. A few confident brush strokes describe the figure; everything else is bare white. Keep the same composition, pose and framing."
LOOKS[02-line-and-wash]="Repaint this photograph as an ink drawing with colour wash. Dark ink brush lines describe the edges and features, with loose transparent washes of muted colour laid inside them. Visible paper. Keep the same composition, pose and framing."
LOOKS[03-heavy-black]="Repaint this photograph in heavy black brush ink. Bold dark masses against pale paper, strong contrast, flicks of ink spatter, the figure read mostly as silhouette and shadow. Keep the same composition, pose and framing."
LOOKS[04-soft-grey]="Repaint this photograph in soft grey ink wash with no outlines. Form built entirely from graded washes of diluted black ink, edges dissolving into the paper, quiet and atmospheric. Keep the same composition, pose and framing."
LOOKS[05-loose-colour]="Repaint this photograph as a loose watercolour. Wet transparent colour running and pooling on textured paper, pigment settling into the grain, edges left unresolved where the brush lifted. Keep the same composition, pose and framing."
LOOKS[06-dense-dark]="Repaint this photograph as a dark ink painting. Deep saturated blacks filling most of the frame, the figure lit only where the paper shows through, heavy and dense. Keep the same composition, pose and framing."

models=(bytedance/seedream-5-pro qwen/qwen-image-edit-plus)

pids=()
for key in ${(k)LOOKS}; do
  for m in $models; do
    name="${key}--${m##*/}"
    node "$T" --image source.png --raw --prompt "${LOOKS[$key]}" \
      --model "$m" --out "$name.png" > "logs-$name.txt" 2>&1 &
    pids+=($!)
  done
done
for p in $pids; do wait $p || true; done

ok=0; fail=0
for f in *.png; do [[ -f "$f" ]] && ok=$((ok+1)); done
for l in logs-*.txt; do grep -q '"out"' "$l" || { echo "FAIL  ${l#logs-}: $(tail -2 "$l" | tr '\n' ' ' | cut -c1-120)"; fail=$((fail+1)); }; done
echo "rendered $ok · failed $fail"
