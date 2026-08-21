#!/bin/zsh
# Every catalogued tile -> SAM canopy masks -> one master-px foliage mask.
# The chain from knowledge/perception-is-a-model-not-a-threshold.md:
#   the VLM says WHAT (tNNN.json boxes) -> SAM says exactly WHERE -> ink cut inside
set -e
ROOT=${0:a:h}/../../..
ROOT=${ROOT:A}
C=$ROOT/jobs/wang-meng/catalogue
mkdir -p $C/sam
for j in $C/t0*.json; do
  n=$(basename $j .json)
  [[ -f $C/sam/$n-trees.png ]] && { echo "skip $n (done)"; continue; }
  echo "== $n"
  ~/.venvs/media-tools/bin/python $ROOT/tools/refine-mask-sam.py \
    --image $C/tiles-z3w/$n.jpg --boxes $j --kinds tree \
    --out $C/sam/$n-trees.png --multimask 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('  boxes',d['boxes'],'coverage',d['coverage'],'maxFill',max((b['fillOfBox'] for b in d['perBox']),default=0))"
done
python3 $ROOT/tools/composite-tile-masks.py --tiles $C/tiles-z3w/tiles.json \
  --masks $C/sam --suffix -trees.png --out $C/foliage-master-z3w.png
