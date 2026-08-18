#!/bin/zsh
# A finished painting -> its FIRST WASH ("block-in"): the big tonal masses a
# painter lays down before any detail, with wet edges bleeding into the paper.
#
# Made FROM the finished frame on purpose. If the wash's silhouette matches the
# painting's, LTX interpolating between them reads as the picture being PAINTED.
# A blot invented separately would have to travel into place first, and that
# travel is exactly what looks like AI morphing.
#
# v1 was a gaussian blur and it looked like an OUT-OF-FOCUS PHOTO, which is the
# opposite of a wash: blur produces soft gradients everywhere, while a real wash
# is FLAT inside and stops at a HARD edge, often with a darker rim where the
# pigment pooled as it dried. So: posterize to flat masses first, wobble the
# boundaries with -spread rather than smoothing them, and paint the wet rim back
# in explicitly.
#
#   usage: ./blockin.sh <finished.png> <out.png> [strength]
#          1 = faint first wash, 3 = nearly the finished mass
set -e
src="${1:?usage: blockin.sh <finished.png> <out.png> [strength]}"
out="${2:?usage: blockin.sh <finished.png> <out.png> [strength]}"
s="${3:-2}"

case "$s" in
  1) shrink=7%  ; levels=3 ; spread=30 ; white=90% ; rim=0.55 ;;
  2) shrink=11% ; levels=5 ; spread=22 ; white=93% ; rim=0.45 ;;
  3) shrink=17% ; levels=7 ; spread=15 ; white=96% ; rim=0.35 ;;
  *) print -u2 "strength must be 1, 2 or 3"; exit 2 ;;
esac

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

# 1. Flat masses: collapse the image, quantise to a few tones, blow it back up.
#    Posterising BEFORE the upscale is what keeps the interiors flat.
magick "$src" -resize "$shrink" -posterize "$levels" -resize 1000% \
  -spread "$spread" -blur 0x2 \
  -modulate 100,62,100 \
  -level "6%,${white}" \
  "$tmp/mass.png"

# 2. The wet rim: pigment pools and dries darker where a wash stops. Take the
#    boundaries of the flat masses and multiply them back in.
magick "$tmp/mass.png" -colorspace Gray -edge 1 -blur 0x6 -auto-level \
  -evaluate multiply "$rim" -negate "$tmp/rim.png"

# 3. Granulation: pigment settling into the paper's tooth.
magick "$tmp/mass.png" "$tmp/rim.png" -compose multiply -composite \
  -attenuate 0.4 +noise Gaussian -blur 0x0.6 \
  "$out"

print "block-in: $out  (strength $s — $levels tones)"
