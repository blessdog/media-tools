#!/usr/bin/env zsh
# WHAT IS A LEAF: ask a vision model, not a threshold.
# Writes journey/<zone>/living-work/<region>/semantic/ for every foliage region,
# which hinge-foliage reads with --semantic. Run once per zone; the masks do not
# change unless the plate does.
set -e
cd "$(dirname "$0")/../../.."
J=jobs/wang-meng; z=$1
[[ -n $z ]] || { echo "usage: build-semantic-masks.sh <zone>" >&2; exit 2; }
PROMPTS="green and orange tree leaves,bare grey rock and cliff,empty background paper"
for wd in $J/journey/$z/living-work/s-*(/); do
  [[ -f $wd/plate.png ]] || continue
  echo "==== ${wd:t}" >&2
  ~/.venvs/media-tools/bin/python tools/segment-semantic.py \
    --image $wd/plate.png --prompts "$PROMPTS" --out $wd/semantic > /dev/null
done
echo "==== SEMANTIC DONE $z" >&2
