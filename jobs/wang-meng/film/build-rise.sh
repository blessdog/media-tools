#!/usr/bin/env zsh
# Build THE RISE: the continuous bottom-to-top pass over the whole scroll.
#   build-rise.sh [paths|render|concat|all]
#
# One leg per zone, chained so each leg's camera centre starts where the
# previous one ended -- the zone seams are handoffs, not cuts. Every leg is
# rendered against its own plane stack AND its own living layer, and the
# concat crossfades 0.8s at each handoff so the plane-stack change does not
# read as a pop.
#
# This replaces film/paths/leg-slow-*.json, which zigzagged between identical
# keys and always returned to the same framing. Ryan, 2026-08-21: "the way it
# looks now is like the same perspective, just floating right above, never
# backing out, not really zooming in."
set -e
cd "$(dirname "$0")/../../.."          # media-tools
J=jobs/wang-meng
F=$J/film
stage=${1:-all}

# zone  from-y  to-y  pushes  skip(ids already approached in an earlier leg)
LEGS=(
  "z1  14626 11000 2 -"
  "z3w 11000  6600 3 w-midstream,w-lower-pool,s-pine-over-bridge,s-left-pines-z2,w-gorge-fall"
  "z4w  6600  5502 1 s-gorge-foreground,s-gorge-big-canopy,w-gorge-fall,s-left-clifftop-pine,s-left-pines-z2"
  "z5w  5502  4493 1 s-gorge-foreground,s-right-rust-tree"
  "z6w  4493  1852 1 -"
)

if [[ $stage == paths || $stage == all ]]; then
  for leg in $LEGS; do
    parts=(${=leg})
    skip=$parts[5]; [[ $skip == "-" ]] && skip=""
    python3 $F/author-rise.py --zone $parts[1] --from-y $parts[2] --to-y $parts[3] \
      --pushes $parts[4] --skip "$skip"
  done
fi

if [[ $stage == render || $stage == all ]]; then
  for leg in $LEGS; do
    parts=(${=leg})
    z=$parts[1]
    d=$F/frames/rise-$z
    rm -rf $d; mkdir -p $d
    # WITHIN-PLANE SURFACE SHAPE, where it was authored. --relief only engages
    # when camZ != 0, so it does nothing on a flat traverse and everything under
    # the breath. Only z1 has maps today (left-cliff-wall, gorge-wall-right,
    # foreground-rock-mass).
    # An ARRAY, not a string: zsh does not word-split an unquoted parameter
    # expansion, so ${relief:+--relief $relief} arrives as ONE argv entry and
    # argparse rejects it.
    relief=()
    [[ -f $J/journey/$z/relief.json ]] && relief=(--relief $J/journey/$z/relief.json)
    print -u2 "== rendering leg $z${relief:+  (+relief)}"
    python3 tools/render-parallax.py \
      --layers $J/journey/$z/layers-filled --path $F/paths/rise-$z.json \
      --out $d --width 1920 --height 1080 --fps 24 \
      --z-step 0.30 --plane-fit --no-base \
      --geometry $J/journey/$z/geometry.json \
      --living $J/living/living-$z.json \
      $relief > /dev/null
    ffmpeg -y -loglevel error -framerate 24 -i $d/%05d.png \
      -c:v libx264 -crf 16 -pix_fmt yuv420p $F/RISE-$z.mp4
    # REAP THE FRAMES. A 1920x1080 PNG is ~3MB and a leg is 1200-1700 of them,
    # so keeping them costs 4-8GB PER LEG. Measured 2026-08-21: this repo had
    # reached 123GB, 67GB of it frame sequences, and Ryan had to clear space on
    # the Mac by hand. Only after the mp4 exists and is non-empty; NO_REAP=1
    # keeps them when you need to inspect individual frames.
    if [[ -z $NO_REAP && -s $F/RISE-$z.mp4 ]]; then
      rm -rf $d
      print -u2 -- "   -> $F/RISE-$z.mp4  (frames reaped)"
    else
      print -u2 -- "   -> $F/RISE-$z.mp4"
    fi
  done
fi

if [[ $stage == concat || $stage == all ]]; then
  # xfade chain. Each leg ends and the next begins on the same master y, so a
  # short dissolve reads as one continuous move rather than a cut.
  X=0.8
  prev=$F/RISE-z1.mp4
  tmp=$F/frames/_x
  rm -rf $tmp; mkdir -p $tmp
  i=0
  for z in z3w z4w z5w z6w; do
    dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $prev)
    off=$(python3 -c "print(max(0.0, $dur - $X))")
    out=$tmp/chain-$i.mp4
    ffmpeg -y -loglevel error -i $prev -i $F/RISE-$z.mp4 \
      -filter_complex "[0:v][1:v]xfade=transition=fade:duration=$X:offset=$off,format=yuv420p" \
      -c:v libx264 -crf 16 $out
    prev=$out; i=$((i+1))
  done
  ffmpeg -y -loglevel error -i $prev -c copy $F/THE-RISE.mp4
  # THE CHAIN IS SCAFFOLDING. Four intermediate encodes of a 3-minute 1080p film
  # is 583MB, measured 2026-08-21, and every one of them is THE-RISE minus a leg.
  # reap-frames.sh cannot see them (they are mp4s, not frame dirs), so the stage
  # that made them is the stage that must clear them.
  rm -rf $tmp
  ln -sfn "$PWD/$F/THE-RISE.mp4" ~/Desktop/WANG-MENG-LATEST.mp4
  print -u2 -- "-> $F/THE-RISE.mp4  ($(ffprobe -v error -show_entries format=duration -of csv=p=0 $F/THE-RISE.mp4)s), Desktop symlink refreshed"
fi
