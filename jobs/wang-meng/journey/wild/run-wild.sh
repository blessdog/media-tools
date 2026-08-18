#!/bin/bash
# Wild-journey runner (on-box). Three stages per segment:
#   run-wild.sh <SEG> conditions [STYLE]   MoGe + custom trajectory -> condition renders
#   run-wild.sh <SEG> infer      [STYLE]   50-step fp16 infer, prompt = motion + scene + style block
#   run-wild.sh <SEG> chain-from <PREV>    prev segment's last RGB frame -> this segment's input.png
# STYLE is a key in segments.json .style (A_artwork | B_realistic). Flags are
# the proven gate-run flags; --neg-prompt NOT --negative-prompt.
set -euo pipefail
SEG="${1:?segment id}"
STAGE="${2:?conditions|infer|chain-from}"
ARG3="${3:-A_artwork}"
WILD=/workspace/wild
SJ=$WILD/segments.json
mkdir -p "$WILD/$SEG"

jget() { python3 -c "
import json
d=json.load(open('$SJ'))
s=[x for x in d['segments'] if x['id']=='$SEG'][0]
v=s['$1']
print(','.join(str(f) for f in v) if isinstance(v,list) else v)"; }
sget() { python3 -c "import json; print(json.load(open('$SJ'))['style']['$1'])"; }

if [ "$STAGE" = "chain-from" ]; then
  PREV="$ARG3"
  python3 - "$WILD/$PREV" "$WILD/$SEG/input.png" <<'PY'
import sys, glob, cv2
prev_dir, out = sys.argv[1], sys.argv[2]
mp4 = sorted(glob.glob(prev_dir + "/results/*.mp4"))[-1]
cap = cv2.VideoCapture(mp4)
last = None
while True:
    ok, f = cap.read()
    if not ok: break
    last = f
assert last is not None, "no frames in " + mp4
rgb = last[: last.shape[0] // 2]          # top half of RGB-D stack
rgb = cv2.resize(rgb, (1280, 720), interpolation=cv2.INTER_LANCZOS4)
cv2.imwrite(out, rgb)
print("CHAIN-OK:", out, "from", mp4)
PY
fi

if [ "$STAGE" = "conditions" ]; then
  cd /workspace/HunyuanWorld-Voyager/data_engine
  python3 create_input_wild.py \
    --image_path "$WILD/$SEG/input.png" \
    --render_output_dir "$WILD/$SEG" \
    --type forward \
    --end-pos="$(jget end_pos)" \
    --target-end="$(jget target_end)"
  echo "CONDITIONS-DONE $SEG: $(ls $WILD/$SEG/video_input/ | head -3)"
fi

if [ "$STAGE" = "infer" ]; then
  PROMPT="$(jget motion) $(jget scene). $(sget "$ARG3")."
  cd /workspace/HunyuanWorld-Voyager
  python3 sample_image2video.py \
    --model HYVideo-T/2 \
    --input-path "$WILD/$SEG" \
    --prompt "$PROMPT" \
    --neg-prompt "$(sget neg)" \
    --i2v-stability \
    --infer-steps 50 \
    --flow-reverse \
    --flow-shift 7.0 \
    --seed 0 \
    --embedded-cfg-scale 6.0 \
    --use-cpu-offload \
    --save-path "$WILD/$SEG/results"
  echo "INFER-DONE $SEG [$ARG3]: $(ls $WILD/$SEG/results/ 2>/dev/null | head -3)"
fi
