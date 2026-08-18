#!/bin/zsh
# GATE — can a diffusion model fill a disocclusion hole in Wang Meng's paper
# better than the classical patch synthesis we already ship?
#
# ONE FRAME, not a clip. If a model cannot fill one hole in one still, no
# amount of camera conditioning was ever going to save the video version.
#
# THE NULL IS BUILT IN. Three panels come out of this:
#   HOLES      layers-pinned --no-base, the raw defect
#   CLASSICAL  layers-final, our SHIFTMAP patch-synthesis fill — the CONTROL
#   FLUX       same frame, same mask, filled by a diffusion model
# Beating "holes" proves nothing; the bar is beating CLASSICAL. Without that
# panel a plausible-looking fill reads as a win when it is a regression.
#
# THE MASK IS EXACT, NOT THRESHOLDED. --fill black and --fill paper differ at
# precisely the pixels no plane claimed, so differencing the two renders gives
# the hole mask with no luminance guesswork — which matters because this
# painting contains near-black ink that any threshold would eat.
#
# CWD: layers.json names its master image REPO-ROOT-relative, so every render
# must run from the repo root. The --no-base passes happen to survive being run
# elsewhere (they never load the master) — which makes this a trap that hides
# until the one command that needs the file.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
cd "$ROOT"
PY=$ROOT/.venv/bin/python
[ -x "$PY" ] || PY=python3

J=jobs/wang-meng/motion/pan
COMMON=(--path $J/path-push-deep.json --geometry $J/geometry-shot.json
        --plane-fit --z-step 0.15 --stills --width 720 --height 1280)

echo "== rendering the holed frame two ways (mask = their difference)"
$PY tools/render-parallax.py --layers $J/layers-pinned \
  --out $J/fill/holes-black --no-base --fill black "${COMMON[@]}" >/dev/null
$PY tools/render-parallax.py --layers $J/layers-pinned \
  --out $J/fill/holes-paper --no-base --fill paper "${COMMON[@]}" >/dev/null

echo "== rendering the classical fill (the control)"
$PY tools/render-parallax.py --layers $J/layers-final \
  --out $J/fill/classical "${COMMON[@]}" >/dev/null

cd "$HERE"

echo "== building the mask"
$PY - <<'PY'
from pathlib import Path
import numpy as np
from PIL import Image
# --stills writes first/middle/last; the LAST frame is where the dolly has
# opened the widest holes, so that is the one worth testing.
def last(d):
    fs = sorted(Path(d).glob("*.png"))
    if not fs: raise SystemExit(f"no frames in {d}")
    return fs[-1]
b = np.asarray(Image.open(last("fill/holes-black")).convert("RGB")).astype(int)
p = np.asarray(Image.open(last("fill/holes-paper")).convert("RGB")).astype(int)
m = (np.abs(b - p).sum(2) > 12)
Image.fromarray((m * 255).astype("uint8")).save("fill/mask.png")
Image.open(last("fill/holes-paper")).convert("RGB").save("fill/holed.png")
Image.open(last("fill/classical")).convert("RGB").save("fill/classical.png")
print(f"hole coverage: {m.mean()*100:.2f}% of the frame  ({int(m.sum())} px)")
PY
echo "wrote fill/holed.png  fill/mask.png  fill/classical.png"
