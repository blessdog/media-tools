#!/usr/bin/env zsh
# Delete PNG frame sequences that have already been encoded. One job.
#   reap-frames.sh            DRY RUN — lists what would go, deletes nothing
#   reap-frames.sh --go       actually delete
#   reap-frames.sh --go NAME  just that one frames dir
#
# A 1920x1080 PNG is ~3MB and a leg is 1200-1700 frames, so every render leaves
# 4-8GB behind. Measured 2026-08-21: media-tools had reached 123GB, 67GB of it
# frame sequences, and Ryan had to clear space on the Mac by hand.
#
# SAFETY: a frames dir is only reaped when its encoded .mp4 EXISTS and is
# non-empty. Frames without an mp4 are listed as KEEP and left alone -- encode
# them first if you want the space. Nothing here is unrecoverable in principle
# (build-rise.sh regenerates any leg from its path + the living layer) but a
# re-render costs ~12 minutes per leg, so the mp4 check is not optional.
set -e
cd "$(dirname "$0")/../../.."          # media-tools
F=jobs/wang-meng/film
go=""; only=""
for arg in "$@"; do
  case $arg in
    --go) go=1 ;;
    *) only=$arg ;;
  esac
done

total=0; kept=0
for d in $F/frames/*(/N); do
  n=${d:t}
  [[ -n $only && $n != $only ]] && continue
  sz=$(du -sm "$d" 2>/dev/null | cut -f1)
  # the encoder names the mp4 for the dir: rise-z1 -> RISE-z1.mp4,
  # st-foo -> ST-foo.mp4, _ab-* are throwaway probes with no mp4 at all.
  mp4=""
  for cand in $F/${(U)${n%%-*}}-${n#*-}.mp4 $F/${(U)n}.mp4 $F/$n.mp4; do
    [[ -f $cand && -s $cand ]] && mp4=$cand && break
  done
  if [[ -n $mp4 ]]; then
    total=$((total + sz))
    if [[ -n $go ]]; then
      rm -rf "$d"
      print -- "  REAPED  ${sz}MB  $n  (kept ${mp4:t})"
    else
      print -- "  would reap  ${sz}MB  $n  -> ${mp4:t}"
    fi
  else
    kept=$((kept + sz))
    print -- "  KEEP        ${sz}MB  $n  (no encoded mp4 — encode it first)"
  fi
done

print -- ""
if [[ -n $go ]]; then
  print -- "  freed ${total}MB; left ${kept}MB of unencoded frames alone"
else
  print -- "  DRY RUN: ${total}MB reapable, ${kept}MB has no mp4 and would be kept"
  print -- "  run with --go to delete"
fi
