#!/usr/bin/env zsh
# The bottom of the scroll, master y 12594-15923, through the same chain the
# catalogued middle already uses:
#   the VLM catalogue says WHAT (z1lower-tNNN.json boxes)
#   -> SAM says exactly WHERE   -> composite to one master-px foliage mask
#
# WHY THIS RUN EXISTS. The catalogue stopped at y 12594 and z1 runs to 15923, so
# the bottom half of the zone -- the foreground rock and the trestle bridge --
# had no labels and the colour gate was left deciding. Run over the whole plate
# it cut 1,243 cards and the rock swayed. Ryan, 2026-08-24: "unfortunately the
# rock moves... this is a solved problem."
#
# SAM IS LOAD-BEARING HERE, NOT DECORATION. Several catalogued boxes are marked
# in their notes as SEARCH REGIONS rather than masks -- the `veil-foliage-*`
# boxes in t002/t003 are leaves drawn as a transparent veil in front of ochre
# boulders, so roughly half the pixels inside each box are rock. Using the boxes
# directly would animate stone. Turning a box into a pixel-exact boundary is
# exactly what this step is for.
set -e
ROOT=${0:a:h}/../../..
ROOT=${ROOT:A}
C=$ROOT/jobs/wang-meng/catalogue
mkdir -p $C/sam-z1lower

for j in $C/z1lower-t0*.json; do
  n=$(basename $j .json)          # z1lower-tNNN
  t=${n#z1lower-}                 # tNNN
  out=$C/sam-z1lower/$t-trees.png
  [[ -f $out ]] && { echo "skip $t (done)"; continue; }
  echo "== $t"
  ~/.venvs/media-tools/bin/python $ROOT/tools/refine-mask-sam.py \
    --image $C/tiles-z1lower/$t.jpg --boxes $j --kinds tree \
    --out $out --multimask 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('   boxes',d['boxes'],'coverage',d['coverage'],'maxFill',round(max((b['fillOfBox'] for b in d['perBox']),default=0),3))"
done

python3 $ROOT/tools/composite-tile-masks.py \
  --tiles $C/tiles-z1lower/tiles.json \
  --masks $C/sam-z1lower --suffix=-trees.png \
  --out $C/foliage-master-z1lower.png
