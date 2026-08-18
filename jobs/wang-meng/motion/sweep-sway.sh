#!/bin/zsh
set -e
cd "$(dirname "$0")"
run() { python3 stroke-cycle.py --image shot-real.png --masks mask/canopy \
        --out "sway-$1.mp4" --field sway --pivot 720,780 --frames 72 --on "$2" \
        --wobble "$3" --drift "$4" --stiffness "$5" --wavelength 620 \
        | python3 -c "import json,sys;d=json.load(sys.stdin);print(f\"  sway-$1.mp4  on=$2 wobble=$3 peak={d['peakDisplacementPx']}px leak={d['roundTripP99Err']}\")" }
run breath 2 8  2  1.6
run breeze 2 16 4  1.6
run gust   2 26 7  1.9
run breeze-threes 3 16 4 1.6
