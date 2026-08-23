#!/bin/zsh
# Rebuild zones whose derived pixels were reaped (2026-08-21 disk clear).
# Plates must already be re-cut from plate.json (crop-region --rect --k).
# Each zone runs the full chain, which now ends in build-relief.
#
# usage: rebuild-zones.sh z2 z3 z3w z4w z5w
# Log lands in the repo, not a scratchpad, so an interrupted run is diagnosable.
set -u
cd "$(dirname "$0")/../../.."
LOG=jobs/wang-meng/journey/rebuild.log
: > $LOG
for z in "$@"; do
  print -u2 "########## $z start $(date +%H:%M:%S)"
  echo "########## $z start $(date +%H:%M:%S)" >> $LOG
  if zsh jobs/wang-meng/journey/build-zone.sh $z >> $LOG 2>&1; then
    echo "########## $z OK $(date +%H:%M:%S)" >> $LOG
    print -u2 "########## $z OK"
  else
    echo "########## $z FAILED exit=$? $(date +%H:%M:%S)" >> $LOG
    print -u2 "########## $z FAILED — continuing to the next zone"
  fi
done
echo "########## ALL DONE $(date +%H:%M:%S)" >> $LOG
