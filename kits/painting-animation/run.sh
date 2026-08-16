#!/bin/zsh
# painting-animation — render one shot from a painting.json.
#
# The kit's procedure lives in SKILL.md; this is the executable half. Everything
# specific to a painting comes from the JSON, so this file never learns the name
# of a scroll, a deer, or a crop box.
#
#   ./run.sh --painting jobs/wang-meng/painting.json --shot ledge-climb
#
# Deliberately NOT a pipeline that runs end to end unattended. Steps that need a
# human verdict on pixels (plane review, mask completeness, does the gait read)
# are the whole job, and a script that hides them behind one command is a script
# that ships slop.
set -eu
KIT="$(cd "$(dirname "$0")" && pwd)"
T="$KIT/../../tools"
PAINTING=""; SHOT=""; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --painting) PAINTING="$2"; shift 2;;
    --shot)     SHOT="$2"; shift 2;;
    --dry-run)  DRY=1; shift;;
    -h|--help)  sed -n '2,16p' "$0"; exit 0;;
    *) echo "unknown flag: $1" >&2; exit 2;;
  esac
done
[ -n "$PAINTING" ] || { echo "need --painting <painting.json>" >&2; exit 2; }
[ -n "$SHOT" ]     || { echo "need --shot <name>" >&2; exit 2; }

J="$(cd "$(dirname "$PAINTING")" && pwd)"
q() { python3 -c "import json,sys;d=json.load(open('$PAINTING'));print(eval(sys.argv[1],{'d':d}) if sys.argv[1] else '')" "$1"; }

NAME=$(q "d['name']")
MASTER=$(q "d['master']")
SHOTIMG=$(q "d['shot']['image']")
CROP=$(q "d['shot'].get('crop','')")
S=$(q "[s for s in d['shots'] if s['name']=='$SHOT'][0]")

R_LEFT=$(q  "[s for s in d['shots'] if s['name']=='$SHOT'][0].get('region',{}).get('left',0)")
R_RIGHT=$(q "[s for s in d['shots'] if s['name']=='$SHOT'][0].get('region',{}).get('right',0)")
R_UP=$(q    "[s for s in d['shots'] if s['name']=='$SHOT'][0].get('region',{}).get('up',0)")
R_DOWN=$(q  "[s for s in d['shots'] if s['name']=='$SHOT'][0].get('region',{}).get('down',0)")
WINDOW=$(q  "','.join(map(str,[s for s in d['shots'] if s['name']=='$SHOT'][0]['window']))")
START=$(q   "','.join(map(str,[s for s in d['shots'] if s['name']=='$SHOT'][0].get('start',[0,0])))")
PAN=$(q     "','.join(map(str,[s for s in d['shots'] if s['name']=='$SHOT'][0]['pan']))")
TRAVEL=$(q  "','.join(map(str,[s for s in d['shots'] if s['name']=='$SHOT'][0]['travel']))")
FRAMES=$(q  "[s for s in d['shots'] if s['name']=='$SHOT'][0].get('frames',72)")
OVER=$(q    "[s for s in d['shots'] if s['name']=='$SHOT'][0].get('over','')")

FIG=$(q "d['figures'][0]['name']")
FIGMASK=$(q "d['figures'][0]['masks']")
LIMBS=$(q "d['figures'][0].get('limbs','')")
G_STRIDES=$(q "d['figures'][0].get('gait',{}).get('strides',2)")
G_BOB=$(q     "d['figures'][0].get('gait',{}).get('bob',3)")
G_LEAN=$(q    "d['figures'][0].get('gait',{}).get('lean',0.9)")
G_SWING=$(q   "d['figures'][0].get('gait',{}).get('swing',5)")

OUT="$J/out/$SHOT"; mkdir -p "$OUT"
# --mask-offset: crop-region adds painting on the left/up, so masks cut against
# the original shot must shift by exactly that. Both tools refuse without it
# rather than shifting silently, because the silent version looks plausible.
OFFSET="$R_LEFT,$R_UP"

# zsh does NOT word-split ${VAR:+--flag "$VAR"} — it arrives as ONE argument and
# argparse rejects it. Optional flags go in arrays.
LIMB_ARGS=(); [ -n "$LIMBS" ] && LIMB_ARGS=(--limbs "$LIMBS")
LIMB_MASK=(); [ -n "$LIMBS" ] && LIMB_MASK=(--masks "$LIMBS")
OVER_ARGS=(); [ -n "$OVER" ]  && OVER_ARGS=(--over "$OVER")

say() { print -r -- "  $*"; }
run() { say "\$ $*"; [ "$DRY" = 1 ] || "$@"; }

say "painting : $NAME"
say "shot     : $SHOT   window $WINDOW  pan $PAN  travel $TRAVEL  frames $FRAMES"
say "figure   : $FIG${LIMBS:+  (+limbs)}"
say ""

run python3 "$T/crop-region.py" --master "$MASTER" --crop "$CROP" --out "$OUT/plate.png" \
    --left "$R_LEFT" --right "$R_RIGHT" --up "$R_UP" --down "$R_DOWN"

run python3 "$T/clean-plate.py" --image "$OUT/plate.png" --masks "$FIGMASK" \
    "${LIMB_MASK[@]}" --mask-offset "$OFFSET" --out "$OUT/plate-clean.png"

run python3 "$T/walk-figure.py" \
    --plate "$OUT/plate-clean.png" --figure "$OUT/plate.png" \
    --masks "$FIGMASK" "${LIMB_ARGS[@]}" --mask-offset "$OFFSET" \
    "${OVER_ARGS[@]}" \
    --window "$WINDOW" --start "$START" --pan "$PAN" --travel "$TRAVEL" \
    --strides "$G_STRIDES" --bob "$G_BOB" --lean "$G_LEAN" --swing "$G_SWING" \
    --frames "$FRAMES" --on 2 --out "$OUT/$SHOT.mp4"

# The null. Same everything, one held drawing. Whatever life the eye reads in the
# shot must not be present here, and this is cheap enough that there is no excuse.
run python3 "$T/walk-figure.py" \
    --plate "$OUT/plate-clean.png" --figure "$OUT/plate.png" \
    --masks "$FIGMASK" "${LIMB_ARGS[@]}" --mask-offset "$OFFSET" \
    "${OVER_ARGS[@]}" \
    --window "$WINDOW" --start "$START" --pan "$PAN" --travel "$TRAVEL" \
    --strides 0 --bob 0 --lean 0 --swing 0 --limb-swing 0.001 \
    --frames "$FRAMES" --on "$FRAMES" --out "$OUT/$SHOT-null.mp4"

say ""
say "wrote $OUT/$SHOT.mp4 and its null. OPEN BOTH — the null is what makes the"
say "first one a claim rather than a hope."
[ "$DRY" = 1 ] || open "$OUT/$SHOT.mp4"
