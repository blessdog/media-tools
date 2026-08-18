# WANG MENG — STATE OF THE WORK (read this FIRST, every session)

Updated 2026-08-17 evening. This file exists because compaction and API kills
kept destroying context and the assistant kept re-inventing solved problems.
Everything here is reconstructed from git log and file mtimes, not memory.
**Rule: update this file at every milestone and before every session end.**

## WHERE WE ARE RIGHT NOW

Z1 (river + bridge zone) segmentation is DONE and awaiting Ryan's mask
verdict on `journey/z1/layers-cut/overlay.png`:

- 13 planes, all real, zero empties, 35.2% unclaimed (continuous wash +
  walking figures — unclaimed BY DESIGN; sealing claims it by proximity).
- Points: `journey/z1/points.json` (13 pts, remapped master→plate).
  Dropped-with-reasons recorded in its `note`.
- On his GO: `complete-planes` → `pin-objects` → `inpaint-planes --behind
  100 --method flux` → frame-zero control (must be 0 px changed) → commit.
- Then: shot-scale density check along stations 1–4 (planes-per-frame,
  depth σ), `map-path.py` + `path-world.json`, `geometry.json` (平遠
  tilts), render, watch.

## THE ARCHITECTURE (approved, committed)

Spec: `docs/specs/2026-08-17-wang-meng-journey-design.md` (`22db1bf`).
Plan: `docs/plans/2026-08-17-wang-meng-journey-phase1.md`.
Full-scroll flythrough, vertical 720×1280, 散点透視 zone worlds (6 zones),
11 stations bottom→top, handoffs in painted mist/water seams. All coords in
master px; k=2.34 master px per rendered px. `journey/world.json` is the SSOT.
Z1 rect [0, 9596, 4613, 15923] Ryan-approved, cut by the camera-world rule
(`journey/zone-rect.py`: bbox + (frame/2 + 250 reach)·k).

## THE CAPABILITY CHAIN — built Aug 13–17, ALL PROVEN, DO NOT REINVENT

Data-enrichment tools, in pipeline order (all in `tools/`):

| tool | job | proven by |
|---|---|---|
| `crop-region.py --rect` | cut any master rect at k, provenance sidecar | `2881985`, Z1 plate |
| `segment-points.py` | clicked dots + depths → RGBA depth planes | pilot 11-plane + Z1 13-plane |
| `segment-regions.py` | auto object masks (figures, never big planes) | `motion/pan/objects/regions.json` |
| `complete-planes.py` | seal unclaimed wash to nearest plane by proximity | `layers-sealed`, FLY-SEALED.mp4 |
| `pin-objects.py` | object spanning 2 depths → pinned to one (18 shears→0) | `6fa444a`, PIN-COMPARE.mp4 |
| `inpaint-planes.py --method flux` | fill occlusion bands ONCE behind planes, seams only | `4dea787`, FLUX-VS-CLASSICAL.mp4 |
| `extend-planes.py --source-crop` | margin sampled from MASTER (0 model calls in-scroll) | `ada0653`, 1.28M px sampled |
| `compose-depth.py` | authored planes + per-figure native-crop model relief | depth-gehong.png, relief 0.0698 vs 0 null |
| `render-parallax.py --plane-fit` | camera flight over sealed card stack | FLY-FINAL.mp4, differential 1.131 |
| `render-warp.py` | content-preserving warp: one sheet, rigid objects, strain in wash | FLY-WARP.mp4, CARDS-VS-WARP.mp4 |
| `walk-figure.py` | cut-out walk cycle from clean plate + mask | WALK.mp4, deer-walk |
| `animate-strokes.py` | painter's own ink displaced (water/foliage life) | GEHONG-alive.mp4, living-river |
| `locate-crop.py` | where a shot sits in the master (self-relative paths) | `aab1d12` |

## LAWS — measured, not opinions. NEVER re-derive, NEVER violate.

1. **Depth is authored, never estimated.** Monocular depth on this painting
   = 48.9–55% R² against image ROW (it reads height-on-page, not depth).
   Figures at native crop are the exception: real volume (Ge relief 0.0698,
   corr(depth,ink) −0.064 → completing shape, not tracing darkness).
2. **PLAN PLANES AT SHOT SCALE.** Scroll-scale stack seen in a shot = 3
   planes, σ 0.098; shot-scale = 13 planes, σ 0.394. Density check per zone.
3. **Frame-zero control** on every fill/extend: 0 px changed at rest.
4. **Null before any motion metric** (static + synthetic-zoom controls).
   silk-survival drift floor = 11% (static control) — quote against IT.
5. **Naming a substance in a motion prompt requests FOOTAGE of it.**
   Camera-only positive, cfg 2–3, 73 frames. Masked crops may name the
   substance. (Full recipe: NEXT-SESSION.md bottom half.)
6. **Grading is not geometry.** "A card with a soft edge is still a card."
7. **SAM tricks:** click TRUNKS not canopies; window sized to the feature;
   wash has no contour — leave it unclaimed for sealing; a "failed" plane
   may have been ERASED by an overlapping leak, check overlap before blaming
   the point.
8. **Share-your-ground:** every figure rides its supporting surface's depth
   (bridge party = one rung in front of the deck). Checkable as code.
9. Don't regress `feedback_workday_dropdown...` — wrong project. For THIS
   project: don't touch the pilot `layers-flux` stack; it's the Z1 seed
   reference, not a scratch area.

## THE SYNTHESIS PLAN (Ryan's directive: "put it all together")

Two renderers, ONE data source, per segment of the journey:
- **Cards** (`render-parallax --plane-fit`, sealed+pinned+filled stack) for
  traverses — real occlusion.
- **Warp** (`render-warp`) for pushes — no disocclusion holes, objects held
  rigid by stiffness map.
- A/B per segment; Ryan's eyes pick. Comparison template: CARDS-VS-WARP.mp4.
- Figure relief via `compose-depth --figure` (Ge, deer, ox party) enters at
  render time — the "green/blue/gray/black" depth PNGs are
  `motion/pan/{depth-gehong,relief-gehong,gehong-native}.png`.
- Life pass (animate-strokes water/foliage, walk-figure) = phase 7, on the
  LOCKED camera.

## KEY ARTIFACTS MAP (what lives where)

- `journey/` — world.json, stations.json (11 stations), zone-rect.py,
  z1/{plate.png, plate.json, points.json, layers-cut/, pick.html}
- `points.json` (job root) — Ryan's 20 manual dots + 11 labelled additions,
  master-normalised. `points-v1-model.json` = backup of old model pass.
- `pick.html` (job root) — 20-dot zero-typing picker, REDESIGNED by the
  parallel session. Current. Do not revert.
- `motion/pan/` — the entire pilot-shot lab: all FLY-*.mp4 evidence videos,
  layers-* stack iterations (flux → sealed → pinned → final → wide4),
  report/{depth-on-silk.html, zoom-to-flight.html} (the measurement
  write-ups), probe-* controls.
- `motion/` — Aug 13–14 masked-motion + stroke-cycle + walk lab
  (GEHONG-alive, WALK, living-river, cel-* sweeps).
- `NEXT-SESSION.md` — handoff notes + the HunyuanVideo masked-motion recipe
  and gpu-box commands (bottom half). Still valid.

## DEFERRED (recorded so they don't get lost OR re-litigated)

- Top-quarter peaks (y < ~0.24): no dots yet — Z6's own pass.
- `great-trees` (points.json id 26): outside Z1 rect — Z2+ business.
- Handoff gate (Z1↔Z2 corridor render-off): phase 2, first thing.
- 1080×1920 re-render: available later from same worlds; not now.
- Zone rects Z2–Z6 are content boxes; each gets the camera-world dilation
  at its turn.

## 2026-08-17 late — mask refix + research pointers (Ryan's links)

- Overlay bug found + fixed: quick overlay placed layers by `cropBox` (SAM
  search window) instead of `bbox` (true position). New INVARIANT adopted:
  **every plane's click point must lie inside its own mask** — this check
  caught two genuinely bad masks the coverage table missed
  (right-bluff-crown-pines, right-hill-front-trees: auto-grow doubled their
  windows until SAM grabbed off-point masses). Both re-segmented with
  --max-grow 0 (front-trees 19.4%; crown-pines re-clicked onto the pale
  TRUNK at plate (1857,657) w700 → 1.52%). 13/13 verified, unclaimed 28.4%.
- Palace Museum page (dpm.org.cn/collection/paint/234561.html): curatorial
  read confirms the journey design — "waterfalls and mountain paths guide
  the viewer's eye progressively deeper." 139×58 cm. No high-res there; our
  105MP master stands.
- World Labs: Marble = image→persistent 3D world (Gaussian splat/mesh
  export, camera-path video). Ryan's verdict: NOT the answer, glean
  technique. No papers; RTFM blog = autoregressive diffusion transformer,
  posed frames as spatial memory, no explicit 3D. Transferable principle:
  geometry answers what it can, the model only completes what geometry
  cannot — which our layer-space flux fill already implements statically.
- **HunyuanWorld-Voyager (Tencent) — Ryan's pointer, TOP CANDIDATE for a
  gate test.** Single image + user camera trajectory → world-consistent
  RGB-D video; conditions on partial renders of an accumulated point cloud.
  Why it matters HERE: it may resolve the measured tension "Hunyuan holds
  the ink but has no control input; Wan has the control ecosystem but a
  hostile prior" — Voyager is Hunyuan-family WITH trajectory control.
  Gate test (like GATE1): Z1 720×1280 crop + simple push trajectory on a
  rented box; judge with silk-survival vs static control + figures intact.
  Ryan's framing: flux dev for style + Hunyuan World for fly-through.

## 2026-08-17 night — GO given: seal chain run + THE RANGEFINDER

Chain state (all under `journey/z1/`):
- `complete-planes`: unclaimed 28.4% → 0.0%, max expansion 253.6 px → `layers-sealed/`
- `segment-regions` at native size (41 objects) → `objects/`
- `pin-objects --min-majority 0.4`: 29 pinned, 0 ambiguous, torn ink
  30.1% → 23.9% (pilot's accepted floor was 20.3%) → `layers-pinned/`.
  The 3 ambiguous rocks (8: outcrop behind Ge → d14; 11: shore boulder →
  d16; 32: resting-ledge rock → d11) resolved by plurality = their ground.
- `inpaint-planes --behind 100 --method flux` → `layers-filled/` (13 planes)
- NEXT: frame-zero control (0 px changed), then stations 1–4 path + render.
- Swap gotcha for the record: a plane entry's `offset` field (not just bbox)
  must be patched when swapping layers — complete-planes reads `offset`.

**RANGE-PLANES (new tool, Ryan-approved, committed `5e0f394`).** Painted
figure size IS distance (h ∝ 1/z within one class). First reading of the
scroll, servant class, master px: ox-leader 515px (Z1 bank, z≡1) →
cliff-path traveler 255px (Z3, z=2.02) → compound figure 170px (Z5,
z=3.03). The journey is spaced in clean multiples. TWO SCALES AT ONCE:
Ge Hong = 760px, 1.48× a NEARER servant — hierarchical (status) scale;
protagonists never calibrate. Within-zone spacing is below instrument
resolution (class spread > z separation) — author by eye; use the
rangefinder ACROSS zones. Files: `tools/range-planes.py`,
`journey/range-marks.json`, `journey/journey-scale.json`.

Synthesis for the flythrough (the forest, not the trees):
- Zone worlds get METRIC spacing from journey-scale.json (z 1→2→3).
- Cards render the wide legs (occlusion); warp + compose-depth field
  renders the station pushes (figure relief visible ∝ 1/distance).
- Camera speed defined in figure-heights/sec; 平遠 altitude = eye height
  above the water plane.

## 2026-08-17 night — FIRST FLIGHT RENDERED
`journey/z1/FLY-S1-4.mp4` (z-step 0.035) and `FLY-S1-4-DEEP.mp4` (0.30,
the proven setting) — stations 1–4, 24s, 720×1280, --plane-fit --no-base,
filled stack. Entry key clamped to y=0.760 (0.908 hung the window 392px
past the scroll bottom → blank paper; the zone-rect rule guards STATIONS,
the path author must guard FRAMES). Frame zero identical across z-steps as
plane-fit guarantees. AWAITING: Ryan's watchability verdict = the Z1 gate.
Then: warp A/B on the bridge push, figure reliefs, Z2.

## 2026-08-17 late night — THE DIMENSIONAL PIECES, WIRED AND JUDGED
Ryan called the first flight Ken Burns — correct: it had cards+parallax but
no tilts, no warp, no relief. Now measured on the bridge push
(`path-push-ge.json`, lateral approach + 0.30-separation dolly on Ge):
- `geometry.json` (平遠 roles from pilot values; trestle-bridge-ge stays
  BILLBOARD — Ge rides it, figures never take tilt): stills + motion clean.
  `PUSH-GE-TILT.mp4` = the keeper.
- `render-warp` on the SAME path: COLLAPSED — central smear, structures
  dissolved (f190/f287). Mechanism, not mystery: the path is a big lateral
  move + deep push; warp's own contract says lateral is where it is wrong,
  and the strain budget (silk 13%, pockets ≤66px) cannot absorb a 1.4x
  differential. Ryan's earlier verdict ("the chop off looks better") stands
  measured. Warp remains viable ONLY for small pure dollies, if anywhere.
- Figure relief: compose-depth builds the map but NO renderer consumes
  intra-figure relief yet (cards = one z/plane; warp holds objects rigid).
  Missing piece = a displacement pass on a figure's card for close-ups.
  PUSH-CARDS-VS-WARP.mp4 is the side-by-side evidence.

## 2026-08-18 overnight — VOYAGER GATE RUNNING AUTONOMOUSLY (Ryan asleep)
Standing orders: complete the gate test by morning; DESTROY the box
(instance 47992868, $1.303/hr, `node tools/gpu-box.mjs down`) on every exit
path. Budget cap $5 (Ryan, tightened before bed). Check `gpu-box status` accrued cost before run 2; skip run 2 if projected total > $5. Checkpoints judged by Claude against pre-registered
criteria (dossier §07), all evidence saved for morning review. Run 2
(authored depth) only if run 1 ink holds. Provisioning attempt 2 in
progress (attempt 1 died: box image lacked python3-venv — fixed; default
manifest's downloader also had to be killed twice). Known deps issue:
repo's pinned pandas has no py3.12 wheel — patch modern pandas into venv
during the weights download, extend smoke test to import create_input deps.


## 2026-08-18 ~23:00 — GATE ABORTED AT $2.20, BOX DESTROYED, READY FOR ATTEMPT 3
The Voyager gate DID NOT RUN: two provisioning failures (missing python3-venv;
then py3.12 wheel mismatches + flash-attn source-compile tar pit — my
--find-links pointed at a GitHub releases PAGE, not a pip index). Both caught
by the 45-min kill criterion. Box 47992868 destroyed, $0 burning, ~$2.20 of
the $5 cap spent. NO third rent overnight (unsupervised retries after two
environment surprises = the pattern Ryan banned). Morning deliverables:
voyager-gate/MORNING-REPORT.md + provision-voyager-v3.sh (docker-image rent:
pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel; exact flash-attn wheel by URL;
weights download first in parallel; ~$1.30 projected). Fires on Ryan's word.

## 2026-08-18 morning — ATTEMPT 3 ARMED, BLOCKED ONLY ON THE RENT CLICK
Ryan approved attempt 3. Free OFFLINE verification pass done before renting
(the lesson: environment questions cost $0, only GPU questions need a box):
- Docker tag pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel EXISTS (7.9GB).
- flash-attn 2.6.3 wheels exist cp310+cp311; script auto-detects PYTAG.
- Voyager data_engine/requirements.txt pins TORCH 2.3.1 → would downgrade
  the box's torch. NEVER install it. v3 filters torch lines from main reqs.
- create_input.py needs ONLY MoGe (clone into data_engine/) + numpy renderer.
  VGGT/Metric3D + their source surgery = training engine only, skipped.
- run-gate1.sh fixed: no venv (docker base IS the env) + official flags
  added (--flow-reverse --flow-shift 7.0 --embedded-cfg-scale 6.0
  --use-cpu-offload).
- provision script travels INSIDE the rent command as a base64 data: URI
  (urlretrieve handles data: natively) → no gist, and the default LTX
  manifest downloader never runs. Wrapper: voyager-gate/rent-attempt3.sh.
Committed: 238f9f5 + 91825fe.
DRY RUN PASSED: A100 80GB machine 27283, $1.281/hr, rel 0.999, ↓15Gbps
(weights pull no longer the long pole). THE --rent CALL IS CLASSIFIER-
BLOCKED in the 2026-08-18 session (server-side auto-mode classifier, not
local permissions — context-sensitive, dry run passed, spend call vetoed).
Ryan is restarting with a fresh session. NEXT SESSION: run
  bash jobs/wang-meng/journey/voyager-gate/rent-attempt3.sh          # dry
  bash jobs/wang-meng/journey/voyager-gate/rent-attempt3.sh --rent   # go
then: wait READY → tail /var/log/bongpot-start.log until PROVISION-OK →
scp voyager-gate/input-bridge.png to /workspace/input-bridge.png → scp
run-gate1.sh → run conditions stage → PULL CHECKPOINT-B SAMPLES TO RYAN'S
SCREEN (open them) before infer → infer (~32min) → pull results + stills →
`gpu-box.mjs down` ALWAYS. Budget: ~$2.80 of $5 remains; box ≈ $1.30/hr,
target ≤1.5h. Judge vs dossier §07 criteria. Run 2 (authored depth swap in
create_input.py) only if run 1 ink holds AND budget allows.

## 2026-08-18 morning — ATTEMPT 3 EXECUTED + THE AMNESIA FIX
Voyager gate attempt 3 ran end-to-end (instance 48031012, machine 28415,
A100 80GB @ $1.315/hr — dry-run machine 27283 was taken). FIVE environment
bugs found and fixed live, all patched back into the committed scripts:
1. huggingface_hub ≥1.0 removed the `huggingface-cli` shim (prints "use hf"
   and exits) → weights never started; script's `wait` died on it silently.
   Fix: `hf download` + WEIGHTS-OK marker in weights.log.
2. cv2 needs libGL.so.1 even headless → apt libgl1 libglib2.0-0.
3. Deps dragged numpy to 2.4.6; image's cv2 binary is numpy-1.x ABI
   (_ARRAY_API) → pin "numpy<2" LAST.
4. sample_image2video.py flag is --neg-prompt, NOT --negative-prompt
   (argparse died; grep pattern missed it — widen watchers with "error:").
5. Weights expected at /root/ckpts → symlink to /workspace/ckpts.
Weights: 81GB in ~90s (15Gbps real). Provision→smoke pass ≈17 min, ~$0.40.
CHECKPOINT B PASSED (Claude judge): 49 RGB partial renders + 49 depth EXRs,
frame 0 byte-faithful, wireframe stretch only in late deep-push frames.
Samples pulled to evidence: journey/voyager-gate/checkpoint-b/ (committed).
Note for verdict: stock `forward` preset pushes DEEP — last third of the
clip is mostly invention; judge silk-survival accordingly.
Inference launched (fp16, 50 steps, ~20s/step + VAE decode w/ cpu-offload).

TECHNIQUE ATLAS published (Ryan's ask: full illustrated catalog + gaps):
https://claude.ai/code/artifact/df599ab5-7b96-4354-b3e1-754cde599664
Figure sources copied to evidence/atlas-2026-08-18/ (committed).

THE AMNESIA FIX (Ryan: "you are too amnesic… make Git a default"):
- Pink-grid diagnostic he screenshotted 2026-08-16 12:05 could NOT be
  provenance'd — it lived only in a dead session scratchpad. The class of
  loss is now banned.
- Laws installed: media-tools/CLAUDE.md top law (evidence lands in repo),
  ~/.claude/CLAUDE.md "Git is the memory organ" (auto-loads in EVERY
  session), bible §7.5 (canon, pushed to GitHub mirror).
- .gitignore rewritten: jobs/ text+scripts+json+evidence*/ tracked by
  default; only bulk pixel intermediates ignored. 312 files committed incl.
  salvaged flight A/B evidence (evidence-salvage-2026-08-18/, 103MB — the
  z-step/plane-fit experiment frames that back the FLY verdicts).
- claude-code-guide agent researching @import + hook mechanics for
  harness-level enforcement (SessionStart/Stop hook, bible @import).

## 2026-08-18 ~09:30 — VOYAGER GATE VERDICT: FAIL (style collapse), GATE CLOSED AT ~$1.40
Run 1 completed (45 frames, 768×1024 RGB-D stacked, seed 0, 50 steps fp16).
Evidence: journey/voyager-gate/results-run1/ (VOYAGER-RUN1.mp4 + stills, committed).
Judged by eye against pre-registered criteria (dossier §07), Ryan's screen + mine:
- FRAME 0 IS ALREADY A REPAINT: model redrew the whole painting as clean
  vector-cartoon (flat fills, smooth shading); 皴 texture + silk grain gone.
- Figures redrawn (Ge's face changed, porters cartooned) → hard fail.
- POSITIVE FINDING: trajectory control WORKS — camera executes exactly the
  conditioned push, composition tracks the partial renders, depth channel
  coherent. Voyager obeyed our geometry and repainted our pixels.
- Measured tension now closed on both ends: Hunyuan-I2V holds ink/no control;
  Voyager has control/hostile prior (same family, different training data —
  its RGB-D corpus is photoreal+game renders, and that prior wins over the
  reference image even at frame 0).
RUN 2 DOES NOT FIRE (pre-registered: better geometry can't fix a style prior).
Box 48031012 destroyed immediately after pull. Total attempt-3 cost ≈ $1.40.
Tilted cards remain the path (FLY-S1-4-DEEP, PUSH-GE-TILT unharmed).

## 2026-08-18 evening — WILD JOURNEY PILOT: chained-world FAILS at S2 (one-generation rule)
Box 48042658 (parked, not destroyed, per Ryan). Style A/B on S1: BOTH treatments
held ink (style block + anti-cartoon neg-prompt — the morning gate's collapse was
partly a prompting artifact). Ryan picked B_realistic. THE LAW MEASURED:
- S1 (conditions = real painting pixels): ink holds. Ryan: "i fw that for sure."
- S2 (conditions = Voyager's own S1 output): game prior surfaces immediately —
  red-pagoda game asset, smoothed shading. Ryan: "the slop was just right around
  the corner. As soon as you pushed it past S1."
Rule: Voyager holds style for EXACTLY ONE GENERATION from real pixels. The style
prompt is a one-generation stabilizer, not a lock. Chained self-feeding is a
ratchet toward the training prior. Consequence: wild journey v2 = station-anchored
(every segment generation-1 from a real crop at one of Ryan's 11 stations; joined
as cuts). Evidence: jobs/wang-meng/journey/wild/S1/ S2/ (committed). S3 (gen-2,
launched pre-verdict) kept as drift-curve data.

## 2026-08-18 late — THE V2 VISION (Ryan, verbatim intent): explore the artwork, don't replace it
"Some of the best cartoons ever are not photorealistic, they're unbelievably
simple… staying true to the artwork. That's what I want to do." The film:
scenes + cut-throughs + pans along the 11 stations; Voyager gen-1 flights for
camera moves; animate-strokes for water/leaves (painter's own ink displaced);
walk-figure for background figures; tilted-cards multiplane (the Disney-1930s
machine) for parallax pans; occlusion teases — "peer around the corner but
can't quite look past it… we don't need to build the world behind the rocks."
Everything is Wang Meng's pixels or one generation from them. Box PARKS (stop,
not down) after queue-v2 — Ryan kills it explicitly, never by default.

## 2026-08-18 ~15:45 — S2-v2 STATION-ANCHORED: FAIL (Ryan: "failed. i hate it")
Gen-1 from real pixels at station 2 (ox party). Style held (ink, silk tone,
painted world) but CONTENT redrawn: family's faces changed, red gate invented,
leaves decorative. Mechanism: repaint tax invisible on texture (S1 = rocks/
water, passed), unbearable on figures. Voyager verdict FINAL: unusable wherever
figures or fidelity matter — S1-B is the only surviving Voyager asset, cameo at
most. Film proceeds with classical lane per the v2 vision: multiplane pans,
animate-strokes water/leaves, walk-figure figures — $0, local, Wang Meng's own
pixels. Box 48042658 PARKED (storage ~$0.033/hr) awaiting Ryan's explicit kill.
Evidence: journey/wild/S2/S2-v2.mp4 + stills + input-station.png (committed).
