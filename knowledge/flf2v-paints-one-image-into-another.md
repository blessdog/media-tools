---
id: flf2v-paints-one-image-into-another
kind: procedure
conflict-key: how-to-transition-between-two-stills-in-the-ink-medium
status: live
supersedes: []
sibling: style-is-solved-control-is-the-problem
verified-on: 2026-08-12
applies-when: >
  you need a shot that TRAVELS between two stills you already have -- an ink
  splatter becoming a finished painting, a painting dissolving back to bare
  paper, one scene cutting to another through the medium itself. Both endpoints
  must exist as images.
route-also: >
  the mechanism is ONE API FIELD, not a pipeline. LTX image-to-video's
  `last_frame_uri`: "the video will interpolate between the first frame and
  this last frame." tools/image-to-video.mjs exposes it as --last-frame, with
  --frame-guide for how hard the endpoint is pinned. Give it ink and a picture
  and it paints one into the other.
route: >
  tools/image-to-video.mjs --provider <ltx-2.5 route> --image <first>.png
  --last-frame <last>.png --frame-guide 0.8 --duration 5
  --prompt "<what the PAINT does; end with: The paper stays still. Only the
  paint moves.>" --out clips/<name>.mp4
  Worked example with four shot shapes: jobs/inkwash-flf2v/run.sh
not-when: >
  the shot needs a SPECIFIC subject to appear that is not already in one of the
  two endpoint frames. Content control is exactly what this route does not give
  you -- four of six clips drifted to the wrong man, invented reeds, or an
  unrelated scene, while the medium held perfectly in all of them. If the
  subject matters, put it in an endpoint frame; do not ask the prompt for it.
  Also not for LTX 2.3, which is materially worse at this across 4 shots and 2
  guide settings.
evidence:
  - jobs/inkwash-flf2v/clips/A-ink-becomes-painting.mp4
  - jobs/inkwash-flf2v/run.sh
  - docs/research/2026-08-12-inkwash-motion-handoff.md
asked-as:
  - how do I get from an ink splatter to a painting on screen
  - how to transition between two still images
  - what is last_frame_uri for
  - between the paper and the painting
  - how do I dissolve out of a scene
---

## Give it ink and a picture, and it paints one into the other

**PROVEN 2026-08-12, first attempt, default settings, Ryan watched it.**
`jobs/inkwash-flf2v/clips/A-ink-becomes-painting.mp4` — LTX 2.5 Pro, 6s, 720p.
First frame a real ink splatter, last frame an approved inkwash still. The splat
blooms, the man resolves out of the ink mass — glasses and cigarette emerging
from the black — and settles into the painting. No drift to photoreal, paper
grain present throughout, the blue washes arrive as washes.

That is Ryan's *"between the paper and the painting"* idea, working.

**Prompt discipline for this route:** describe only what the PAINT does, and
state explicitly that the substrate is still. The clip A prompt ends *"The paper
stays still. Only the paint moves."* — and note it never names a physical
substance as the subject, which would request footage of that substance
([[naming-a-substance-requests-footage]]).

**The guide setting is a real dial with a measured trap.** At `--frame-guide
0.8` LTX 2.3 treated the ink splat as a **stencil**: the painting was revealed
through the splat's hole, the splat stayed as a blue frame, and the render never
landed on the target last frame — a visible white cutout edge is the tell.
Pinning to `1.0` was the obvious fix and **made it worse**, going flat and
graphic. A looser guide is the right default for shots whose whole point is
dissolution; a tighter one does not buy you the endpoint on 2.3.

**Four shot shapes were built on it** (`jobs/inkwash-flf2v/run.sh`): ink→picture,
picture→ink (how you cut OUT of a scene), a push INTO the paper with no last
frame at all, and scene→scene.
