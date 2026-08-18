#!/bin/zsh
# "Between the paper and the painting" — LTX 2.3 22b-dev on CivitAI buzz.
#
# A at guide 0.8 treated the ink splat as a STENCIL: the painting was revealed
# through the splat's hole, the splat stayed as a blue frame, and the render
# never landed on the target last frame (visible white cutout edge = the tell).
# So A is re-run pinned harder. B/C/D go out at 0.8 in the same round, since a
# looser guide is the right default for shots whose whole point is dissolution.
set -e
T=/Users/SSDrive/projects/media-tools/tools
F=frames
C=clips
mkdir -p $C
gen() { node $T/image-to-video.mjs --provider civitai --duration 5 "$@" }

# A″ — same pair as before, pinned to the last frame.
gen --image $F/ink-start.png --last-frame $F/painting-end.png --frame-guide 1.0 \
  --prompt "Wet black ink spreads outward across the cream paper from the splatter, the wash creeping and feathering into the grain. As it spreads the ink settles into the shape of a man in glasses smoking, pale blue and grey washes flooding in behind him and drying into a finished painting. The paper stays still. Only the paint moves." \
  --out $C/A3-guide10.mp4 &

# B — the reverse: how you cut OUT of a scene.
gen --image $F/painting-end.png --last-frame $F/ink-start.png --frame-guide 0.8 \
  --prompt "The painted man dissolves. The washes lift off the paper and run back together into a single wet black splatter at the centre, colour draining away to bare cream paper. The paper stays still. Only the paint moves." \
  --out $C/B-painting-becomes-ink.mp4 &

# C — INTO the paper. No last frame: the model is free to travel, and the only
#     instruction is that the picture stops being a picture.
gen --image $F/painting-end.png --frame-guide 0.8 \
  --prompt "Slow steady push into the painted surface. The brushstrokes grow until they stop reading as a face and become wet ink sitting in the grain of the paper, individual bristle marks and pooled edges filling the frame. Nothing in the picture moves; the view travels into the paint." \
  --out $C/C-into-the-paper.mp4 &

# D — scene to scene. The one that decides whether a whole film cuts this way.
gen --image $F/painting-end.png --last-frame ../sheen-inkwash/renders/shot-07.png --frame-guide 1.0 \
  --prompt "The washes flow and rearrange on the paper, wet pigment running from one composition into the next, edges bleeding and re-drying as the new picture settles. Everything stays ink and watercolour on cream paper throughout." \
  --out $C/D-scene-to-scene.mp4 &

wait
print "\ndone -> $C"
