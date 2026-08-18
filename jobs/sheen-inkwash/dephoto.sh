#!/bin/zsh
# Turn a describe-video shot (written for a CAMERA) into a prompt for a PAINTER.
#
# describe-video is right to write what it writes — its job is describing what
# the camera did, and "cool frontal key light, minimal fill, camera-left" is an
# accurate description of that. But in the USO graph the content channel then
# argues for a photograph while the style channel argues for paint, and the face
# is where the photo prior wins. Ryan spotted it at 100%: painted paper, airbrushed
# skin.
#
# Two operations, both conservative:
#   1. drop whole sentences whose SUBJECT is the apparatus (the camera, the
#      lighting, on-screen text) — never sentences about the man.
#   2. rewrite the handful of optical phrases that appear inside subject
#      sentences into painter's equivalents.
#
# usage: ./dephoto.sh regen/shot-05.txt
set -e
sed -e '1{/^Shot [0-9]/d;}' "$1" \
  | tr '\n' ' ' \
  | sed -e 's/\. /.\n/g' \
  | grep -v -i -E '^[[:space:]]*(the camera|lighting is|the lighting|light is|no on-screen text|there is no text|shot on|the shot is)' \
  | sed -E \
    -e 's/[Ll]ooking just below the lens/looking slightly down and past the viewer/g' \
    -e 's/(soft,? )?out-of-focus/loosely washed/g' \
    -e 's/shallow depth of field/soft washed background/g' \
    -e 's/[Bb]okeh/soft pooled colour/g' \
    -e 's/;[^;.]*(camera|key light|fill|backlight|lens)[^;.]*//g' \
  | sed -e 's/^[[:space:]]*//' -e '/^[[:space:]]*$/d' \
  | tr '\n' ' ' \
  | sed -e 's/[[:space:]]\{2,\}/ /g' -e 's/[[:space:]]*$//'
