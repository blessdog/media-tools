#!/bin/zsh
set -e
cd "$(dirname "$0")"
run() { python3 stroke-cycle.py --image shot-real.png --masks mask/water --only upper-river \
        --out "cel-$1.mp4" --frames 72 --on "$2" --wobble "$3" --drift "$4" --wavelength "$5" >/dev/null
        echo "  cel-$1.mp4   on=$2 wobble=$3 drift=$4 wavelength=$5" }
run gentle 2 3  8  260
run medium 2 6  16 240
run strong 2 10 26 220
run smooth 1 6  16 240
run threes 3 6  16 240
run boily  2 6  16 240
