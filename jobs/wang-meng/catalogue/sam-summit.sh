#!/usr/bin/env zsh
# The SUMMITS, master y 0-4712, through the same chain the rest of the scroll
# already uses:
#   the VLM catalogue says WHAT (summit-tNNN.json boxes)
#   -> SAM says exactly WHERE   -> composite to one master-px foliage mask
#
# WHY THIS BAND IS THE HARDEST. Everything up here is far away, so a tree is not
# a canopy -- it is one glyph: a short dark vertical trunk stroke under a flat
# dotted crown, repeated along a ridge. The decoy is 点苔 moss dotting, which is
# the SAME MARK without the trunk under it, chained along a rock fold. On the
# shaded cliffs it forms near-continuous vertical curtains that are
# indistinguishable from hanging foliage at thumbnail size.
#
# AND COLOUR FAILS IN BOTH DIRECTIONS HERE, which is why the catalogue decides:
# the far peaks carry a blue wash and are stone, the thatched roofs carry the
# same ochre as the trunks, and the pure-ink pine stands carry no wash at all.
# A threshold grabs the first two and misses the third.
set -e
ROOT=${0:a:h}/../../..
ROOT=${ROOT:A}
C=$ROOT/jobs/wang-meng/catalogue
mkdir -p $C/sam-summit

for j in $C/summit-t0*.json; do
  n=$(basename $j .json)          # summit-tNNN
  t=${n#summit-}                  # tNNN
  out=$C/sam-summit/$t-trees.png
  [[ -f $out ]] && { echo "skip $t (done)"; continue; }
  echo "== $t"
  # A TILE WITH NO FOLIAGE IS AN ANSWER, NOT A FAILURE -- refine-mask-sam has
  # nothing to prompt with, prints nothing, and `set -e` would take the whole
  # run down with it. Write an empty mask so the composite still has a tile.
  ntree=$(python3 -c "import json; d=json.load(open('$j')); print(sum(1 for o in d['objects'] if o.get('kind')=='tree' and o.get('leavesVisible')))")
  if [[ $ntree -eq 0 ]]; then
    python3 -c "
from PIL import Image
im = Image.open('$C/tiles-summit/$t.jpg')
Image.new('L', im.size, 0).save('$out')
print('   no foliage catalogued -- empty mask written')"
    continue
  fi
  ~/.venvs/media-tools/bin/python $ROOT/tools/refine-mask-sam.py \
    --image $C/tiles-summit/$t.jpg --boxes $j --kinds tree \
    --out $out --multimask --fence 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('   boxes',d['boxes'],'coverage',d['coverage'],'maxFill',round(max((b['fillOfBox'] for b in d['perBox']),default=0),3))"
done

python3 $ROOT/tools/composite-tile-masks.py \
  --tiles $C/tiles-summit/tiles.json \
  --masks $C/sam-summit --suffix=-trees.png \
  --out $C/foliage-master-summit.png
