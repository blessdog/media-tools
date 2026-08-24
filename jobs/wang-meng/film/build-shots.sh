#!/usr/bin/env zsh
# Build the SUBTLE SHOT reel: a few focus shots on a COARSE plane stack, joined
# by crossfades. Ryan, 2026-08-24: "maybe we're trying to parallax in too much of
# a granular way... just three or four parallaxed planes, pick a point of focus
# in each shot, string different shots together with a smooth transition fade.
# This should just be a subtle parallaxing shift that you barely perceive, but
# it still is enough to be delightful."
#
#   build-shots.sh [render|concat|all]
set -e
cd "$(dirname "$0")/../../.."
J=jobs/wang-meng
F=$J/film
stage=${1:-all}
STACK=$J/journey/z1/layers-filled-coarse4
LIVING=$J/living/living-z1-coarse4.json
SHOTS=(focus-water focus-ge focus-trees)
X=0.8                                   # crossfade seconds

if [[ $stage == render || $stage == all ]]; then
  for s in $SHOTS; do
    d=$F/frames/shot-$s
    rm -rf $d; mkdir -p $d
    print -u2 "== $s"
    # NO --relief and NO --geometry: both are keyed by PLANE NAME and the merged
    # planes have new names. A merged plane also mixes roles (water + rock), so a
    # single tilt for it would be wrong even if the name matched. Re-deriving
    # per-merged-plane geometry is open work, not a silent default.
    python3 tools/render-parallax.py \
      --layers $STACK --path $F/paths/shot-$s.json \
      --out $d --width 1920 --height 1080 --fps 24 \
      --z-step 0.30 --plane-fit --no-base \
      --living $LIVING > /dev/null
    ffmpeg -y -loglevel error -framerate 24 -i $d/%05d.png \
      -c:v libx264 -crf 16 -pix_fmt yuv420p $F/SHOT-$s.mp4
    [[ -s $F/SHOT-$s.mp4 ]] && rm -rf $d
    print -u2 -- "   -> $F/SHOT-$s.mp4"
  done
fi

if [[ $stage == concat || $stage == all ]]; then
  tmp=$F/frames/_x; rm -rf $tmp; mkdir -p $tmp
  # BRACE THE SUBSCRIPT AND KEEP THE EXTENSION: `$F/SHOT-$SHOTS[1]` expands to a
  # path with no .mp4 and ffmpeg fails on the first join.
  prev=$F/SHOT-${SHOTS[1]}.mp4; i=0
  for s in ${SHOTS[2,-1]}; do
    dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $prev)
    off=$(python3 -c "print(max(0.0, $dur - $X))")
    out=$tmp/chain-$i.mp4
    ffmpeg -y -loglevel error -i $prev -i $F/SHOT-$s.mp4 \
      -filter_complex "[0:v][1:v]xfade=transition=fade:duration=$X:offset=$off,format=yuv420p" \
      -c:v libx264 -crf 16 $out
    prev=$out; i=$((i+1))
  done
  ffmpeg -y -loglevel error -i $prev -c copy $F/SUBTLE-REEL.mp4
  rm -rf $tmp                            # the chain is scaffolding, not output
  print -u2 -- "-> $F/SUBTLE-REEL.mp4 ($(ffprobe -v error -show_entries format=duration -of csv=p=0 $F/SUBTLE-REEL.mp4)s)"
fi
