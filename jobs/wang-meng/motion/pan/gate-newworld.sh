#!/bin/zsh
# GATE — can we walk OUT of the painting into new territory that still reads as
# Wang Meng, and can that new territory be turned back into a card stack?
#
# Pissjug, 2026-08-17: "stretch it as far as we can and then take that reframed
# angle and feed it back into the model to generate a new pathway through."
# That is perpetual view generation, and the published cure for its compounding
# drift is exactly his re-grounding instinct.
#
# HOW THE VOID IS MADE HONESTLY. The planes are painted 100px behind their
# occluders. The full meander needs 298px (probe-path-envelope). So rendering
# the meander from the FILLED stack runs the camera off the end of the paint on
# purpose — the holes that open are not seams, they are territory that has never
# existed in the painting. That is the thing the model has to invent.
#
# WHAT THIS DOES AND DOES NOT TEST. It runs flux-fill-pro, which has a prompt
# and no style-reference channel. So it answers "can new territory be generated
# convincingly at all". It does NOT test the USO image-based style anchor
# (buildUsoGraph swatchImage), which is the real anti-drift lever and needs a
# rented box. Renting that box is only justified if this passes.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
cd "$ROOT"
J=jobs/wang-meng/motion/pan
C=(--path $J/path-meander.json --geometry $J/geometry-shot.json --plane-fit
   --z-step 0.15 --width 720 --height 1280 --fps 24 --stills --no-base)

echo "== rendering the meander off the end of the paint"
python3 tools/render-parallax.py --layers $J/layers-flux --out $J/new/void-b --fill black "${C[@]}" >/dev/null
python3 tools/render-parallax.py --layers $J/layers-flux --out $J/new/void-p --fill paper "${C[@]}" >/dev/null

python3 - <<'PY'
from pathlib import Path
import numpy as np
from PIL import Image
J = Path("jobs/wang-meng/motion/pan/new")
last = lambda d: sorted((J/d).glob("*.png"))[-1]
b = np.asarray(Image.open(last("void-b")).convert("RGB")).astype(int)
p = np.asarray(Image.open(last("void-p")).convert("RGB")).astype(int)
m = np.abs(b - p).sum(2) > 12
Image.fromarray((m*255).astype("uint8")).save(J/"void-mask.png")
Image.open(last("void-p")).convert("RGB").save(J/"void.png")
print(f"void to invent: {m.mean()*100:.2f}% of the frame ({int(m.sum())} px)")
PY
echo "wrote $J/new/void.png and void-mask.png"
