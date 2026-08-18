# Voyager wild journey — design spec

2026-08-18 · wang-meng campaign · approved direction: **chained world**

## What this is

A deliberate departure from the museum campaign. The Voyager gate (closed
2026-08-18, $1.40) proved two things: Voyager repaints the painting into its
own world even at frame 0, and its trajectory control is exact. The museum
work rejects the repainting; this experiment **uses** it. Ryan: "I'm curious
what kind of world it can push through… It could take us through a wild
beautiful journey. I'm interested in seeing a full story out of it."

Deliverable: one continuous ~20-second flight from the river at the bottom of
葛稚川移居圖 to the summit at the top, through Voyager's own invented
extension of the painting, stitched with a music bed.

**This does not touch the museum path.** Tilted cards (FLY-S1-4-DEEP,
PUSH-GE-TILT) remain the true-to-the-art lane. Nothing in `layers*/`,
`motion/`, or the locked style surfaces is modified.

## The spine: Ryan's 11 stations

`jobs/wang-meng/journey/stations.json` — the dots Ryan placed across the
scroll — is the narrative route. Chained-world means only segment 1 anchors
to real pixels; after that the stations serve as **headings** (each
station-to-station vector sets the camera trajectory) and **story beats**
(each segment's prompt names the thing the station is).

Scale calibration from `journey/journey-scale.json` (figure-height law,
h ∝ 1/z): the compound sits at 3× the bank's distance and far above it.
The felt journey is on the order of a mile. Two consequences: the flight
must visibly **climb** from segment 5 onward, and a single speed would
either rush the beats or make a mile feel like a hallway.

## Segment table

10 segments, strictly sequential (each needs the previous one's last frame).
Class sets speed: **beat** = slow push (~⅓ scene depth per 2s clip, the
camera arrives and lets you look), **transit** = fast push (most of scene
depth, these carry the miles).

| # | route (stations) | class | heading (from dot geometry) | prompt scene noun |
|---|---|---|---|---|
| S1 | river entry → ox party | beat | forward over water toward the bank | travelers with an ox at a river bank |
| S2 | ox party → bridge | beat | forward-left | a stone bridge over the stream |
| S3 | bridge → porters climb | transit | left, beginning to climb | a steep path into the rocks |
| S4 | porters → rapids | transit | forward, climbing along the stream | rushing rapids between boulders |
| S5 | rapids → fenced cliff path | transit | strong climb, slight left | a fenced path clinging to the cliff |
| S6 | cliff path → gorge traverse | transit | rightward traverse | a deep gorge |
| S7 | gorge → waterfall | beat | forward-right, rising | a tall waterfall down the cliff face |
| S8 | waterfall → compound | beat | left and up | a walled compound among mountain pines |
| S9 | compound → mist release | transit | up, fast | rolling mist swallowing the ridges |
| S10 | mist → summit, far blue | beat (finale) | pitched up, slowing | distant blue peaks above the clouds |

Trajectory implementation: Voyager's condition generator ships preset camera
movements. **Offline verification item (shift-left law, $0):** read
`create_input.py` in the Voyager repo on GitHub before renting — enumerate
the exact preset vocabulary and any speed/step parameter, and map each
segment's heading to the nearest supported preset. If no speed parameter
exists, beat vs transit is expressed by trajectory choice (partial-depth
presets vs full push) — resolve this offline, not on the meter.

## Style: ink and graphite, not game render

Ryan, verbatim intent: Voyager's example footage "looks like 3D rendered
cartoonish video game graphics." Order of preference: **artwork (ink wash /
pencil) > realistic > cartoon.** "Imperfections are what give it character
in the pencil drawing. You can see the graphite where the tooth of the paper
unevenly pulls the line."

Known physics: the gate measured that Voyager's prior beats even byte-faithful
pixel conditions, so prompts will *steer*, not command. Two levers the gate
deliberately never used:

- **Positive prompt style block** appended to every segment's camera+scene
  prompt: `ink wash painting on paper, handmade artwork, visible brush
  texture and granular pigment, uneven graphite line where the paper tooth
  catches, muted mineral palette, soft paper grain`
- **Negative prompt** (`--neg-prompt`, real classifier-free guidance, not
  Law-6 summoning): `cartoon, cel shading, flat colors, video game
  render, 3D render, smooth plastic surfaces, saturated colors`

**Style gate = segment 1 A/B.** Two infers of S1, same seed, same trajectory:

- **A "artwork":** full style block above.
- **B "realistic":** `weathered natural landscape, matte surfaces, atmospheric
  haze, muted palette, film grain` + same neg-prompt.

Ryan judges on screen. Pass = whichever escapes cartoon better; that
treatment locks for all remaining segments. If **both** come back cartoon,
STOP at ~$2.50 spent and decide with Ryan: accept the game-world look as the
experiment's honest voice, or close the experiment. No silent proceeding.

## Chain mechanics

Per segment N ≥ 2 (`chain-leg.sh`, the only new code):

1. Extract segment N−1's final RGB frame (top half of the 768×1024 RGB-D
   stack, frame ~44).
2. Upscale/pad to 1280×720 (Voyager force-resizes anyway; do it explicitly).
3. MoGe depth → point cloud → condition renders (same stage as the gate;
   note MoGe is *more* at home on Voyager's output than it was on ink).
4. Infer with the locked style treatment + segment's trajectory + scene noun.
   Same flags as the proven gate run: 50 steps, fp16, seed 0, cpu-offload,
   `--neg-prompt` (NOT --negative-prompt).

Known seam risk: Voyager repaints frame 0, so each splice may pop. Expected
to shrink down the chain (each input is already in-distribution). Mitigation
at assembly: 4–6 frame crossfade per seam in `stitch.mjs`. Judged at pilot.

## Pilot gate (pre-registered)

Run S1-A/B (style gate) + S2 + S3. Pull and judge ONE question: does the
chain hold — style consistent across seams, world coherent, not compounding
into mush by S3? Box stays up during judging.

- **Hold** → run S4–S10 without stopping.
- **Mush** → down the box; total loss ≈ $3.50; findings to STATE.md/journal.

## Budget and box discipline

A100, ≈$1.30/hr. Provisioning is one command (attempt-3's five fixes are
committed in `provision-voyager-v3.sh` / `run-gate1.sh`). ~25–35 min per
infer, conditions ~2 min. 11 infers total (S1×2 + S2–S10) ≈ 6–7 h ≈ **$9;
cap $12.** All watcher greps include `error:` as well as `Traceback`
(silence-is-not-success). `gpu-box.mjs down` ALWAYS, verified, before the
session ends — regardless of outcome.

## Evidence & memory (git-is-memory-organ law)

- Working dir: `jobs/wang-meng/journey/wild/` — per-segment trajectory/prompt
  JSONs committed BEFORE renting; per-segment last-frames, stills, and final
  stitched cut committed as they land under `journey/wild/evidence/`.
- STATE.md one-liner per gate verdict (style gate, pilot gate, final).
- Journal entry when the experiment closes, either way.

## Out of scope (YAGNI)

- No post-hoc restyle pass (restyle-video/stylize-frames) in v1 — judged a
  separate experiment if the style gate result demands it.
- No custom camera pose authoring beyond preset mapping.
- No audio beyond a single music bed at stitch time.
- No changes to museum-lane assets, styles/, or locked surfaces.
