#!/bin/bash
# v2 station-anchored queue (on-box): S2..S10 back to back, every shot
# generation-1 from a REAL scroll crop (input-station.png -> input.png,
# no chain stage ever). Conditions then infer per shot, locked B_realistic.
# Markers: QUEUE-SHOT-START/QUEUE-SHOT-DONE per segment, QUEUE-ALL-DONE at end.
set -euo pipefail
cd /workspace
for SEG in S2 S3 S4 S5 S6 S7 S8 S9 S10; do
  echo "QUEUE-SHOT-START $SEG $(date -u +%H:%M:%S)"
  cp "/workspace/wild/$SEG/input-station.png" "/workspace/wild/$SEG/input.png"
  rm -rf "/workspace/wild/$SEG/video_input" "/workspace/wild/$SEG/results"
  bash wild/run-wild.sh "$SEG" conditions
  bash wild/run-wild.sh "$SEG" infer B_realistic
  mv "/workspace/wild/$SEG/results/"*.mp4 "/workspace/wild/$SEG/$SEG-v2.mp4"
  echo "QUEUE-SHOT-DONE $SEG $(date -u +%H:%M:%S)"
done
echo "QUEUE-ALL-DONE $(date -u +%H:%M:%S)"
