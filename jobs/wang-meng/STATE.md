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
Addendum (Ryan): Voyager also fails on RESOLUTION — 768×512 output, "pixel
poor". Scroll is 6586×15923 native; classical lane crops/renders at full res.
Third independent kill: fidelity (faces), fabrication (prompts/prior), and
resolution. NEXT PHASE: assemble the film from the toolbox — classical only.

## 2026-08-19 — ASSEMBLY PHASE OPENED: Z1 tilt flight + Z2 groundwork ($0, local)
Two moves, both blocked only on Ryan's eyes:
1. **FLY-S1-4-TILT.mp4** (journey/z1/) — the stations 1–4 flight re-rendered
   WITH geometry.json. The 08-17 DEEP flight predates the tilts (that is why
   it read as Ken Burns); same recipe otherwise (path-s1-4.json, filled stack,
   z-step 0.30 --plane-fit --no-base). Controls: frame zero 0/921600 px vs
   DEEP (plane-fit guarantee holds under tilt); f200/f336/f480 differ on
   35–44% of px, so the tilts are live. Evidence:
   journey/z1/evidence-tilt-vs-deep-f336.png. HIS VERDICT = the phase-1 gate.
2. **Z2 cut by the camera-world rule** (zone-rect.py --ids 4-5; the rule
   reproduces Z1's approved rect exactly on ids 1-4, so it is trusted):
   rect [0,8428,2383,13762], plate 1018×2279 at k → journey/z2/plate.png.
   journey/z2-rect-overlay.png shows Z2 vs Z1 + the resting-ledge gate
   corridor (S4 sits inside it). 10 global dots fall in-rect, remapped
   master→plate by journey/z2/remap-points.py → z2/points.json (windows =
   global/k, DRAFT) + z2/points-overlay.png. Wash-flagged (Z1's measured SAM
   failures, red rings): bank-ledge-below-bridge, porter-ledge. Upper band
   y<0.30 (rapids-corridor approach: waterfall, big pines, right-bank masses)
   is thin — top-up in z2/pick.html (seeded with the 10 dots) before
   segmenting. Then: segment → seal → pin → fill → frame-zero control →
   geometry (climbing eye) → handoff-gate render-off vs Z1.
Note: gpu-box status = no instances, $0 burning (wild-journey box gone).

## 2026-08-19 midday — PHASE-1 GATE PASSED; SEQ-Z1-v1 SHIPPED (63s)
Ryan on FLY-S1-4-TILT: "the zoomed-in zigzag looks fine" = Z1 watchable,
phase 1 closed. First minute-long cut assembled same session:
journey/z1/SEQ-Z1-v1.mp4 — river entry 22s (new render, lateral parallax
leg) → living bridge hold 9.1s (cel loop ×3, seam delta 0.82) → PUSH-GE-TILT
12s (keeper, as-is) → rise to porters 20s (new render). Controls: shot-1
frame zero 0px vs approved flight; spot strip z1/evidence-seq-v1-shots.png.
Full step log: reports/2026-08-19-seq-z1.md (Ryan wants a report per build —
standing practice from here). Music: none yet — when a track lands, retime
paths to it (durations are JSON fields) and stitch --music. Next: his SEQ
verdict → then Z2 dots top-up (z2/pick.html seeded) → Z2 chain → handoff gate.

## 2026-08-19 evening — FULL-FILM PLAN APPROVED; FILM 0-11s EXISTS; ALL ZONES STAGED
Plan (approved): 7-shot Chowder Julius journey, all proven tech, plan file
~/.claude/plans/effervescent-wobbling-dove.md; shot SSOT film/shots.json.
- P1 DONE pending verdict: film/FILM-0-11s.mp4 — shots 1-2 (river entry;
  sweep onto Ge) with FOUR living planes (water, upper-stream, pine, FAN —
  fanonly mask remapped shot->plate at +385,+431) against the real audio.
- render-parallax --living + animate-strokes --out-frames shipped (a371a4f).
- Deer walk DEFERRED with mechanism: loops snap back, walks aren't loops;
  needs non-looping per-shot plane sequences (shot-5 era).
- Z3-Z6 STAGED by journey/stage-zone.py: rects (camera-world rule, ids
  5-7/7-8/8-9/9-11), plates, remapped dot drafts + overlays (z3:13, z4:10,
  z5:10, z6:8 dots). Z6 top quarter (y<0.24) still needs Ryan's click pass.
- RYAN'S QUEUE: (1) watch FILM-0-11s; (2) Z2 dot top-up in z2/pick.html.

## 2026-08-19 late — SHOT GRAMMAR CONDEMNED; FILM BLOCKED ON RYAN'S SHOT DESCRIPTION
Ryan's verdict on FILM-0-11s and every camera so far: the z-push TEST
grammar wearing a film costume — "same pan over a still shot," scrapped.
Root cause named: I authored cinematography instead of asking the
director. BLOCKED ON: Ryan describing the first ~10s as HE'D shoot it
(what's in frame on "Orange Julius," what happens on the cut, when if
ever the camera moves, what's alive). Machinery is NOT condemned and sits
ready: locked living frames direct from animate-strokes drawings,
native-px close-ups (board: film/evidence-native-closeup-board.png —
water / family-on-ox / Ge+fan / deer), walk cycles, ffmpeg cuts on
beats.json, parallax reserved for true travel moments. Zones Z2-Z6 all
staged. Do NOT render another authored camera path before his answer.

## 2026-08-19 night — THE REAL FILM, from Ryan directly (supersedes Chowder Julius)
An ART HISTORY YOUTUBE CHANNEL piece. His words: explore the ENTIRE
artwork — pan between details, zoom in/back out, float around; water
moving in EVERY shot the entire shot; foliage moves only when "little
gusts of wind blow through"; subtle; "1930s Disney with all of their
clever techniques" (The Old Mill 1937 = the multiplane template; our
tilted cards ARE a multiplane camera). He is writing the narration script
(Ge Hong history, e.g. the fashion anecdote); visuals will follow its
beats — zoom/focus on what the script discusses, occasional 3D
peek-arounds at held shots. ENHANCE with our data richness + FFmpeg +
local tools; NEVER regenerate pixels with AI (museum pitch). DEAD: the
fixated Ge bridge crop, z-push paths as film grammar, LPC audio here.
WHILE HE SCRIPTS, my prep queue: (1) research actual 1930s Disney
techniques -> mapping doc technique->our tools; (2) whole-scroll living
layer: native water/fall cycles for every water region (regions.json
inventory stands), gust-envelope sway (intermittent, needs an envelope
feature in animate-strokes — currently continuous); (3) exploration
camera language across ALL zones, far from the bridge.

## 2026-08-19 late — gust envelope SHIPPED (prep queue item 1 done)

animate-strokes gained `--gust A,H,D` (+ --gust-travel/-rest/-push/
-flutter): wind as an EVENT that sweeps downwind and leaves calm air,
loop still closes exactly. Proven on pine-over-bridge (Z1): calm floor
0.07 for 60% of an 8s loop, front peaks at the old sway's full energy,
seam 0.079 = no pop, leakage 0.00. Evidence:
living/AB-GUST-VS-SWAY.mp4 (left constant / right gust),
living/evidence-gust-vs-constant-sway.png, plane-cycles/gust-activity.json.
peakDisplacementPx metric fixed to running max (was last-drawing-only).
NEXT (queue item 2): native-res water/fall cycles for ALL water regions.

## 2026-08-19 late II — NATIVE WATER LAYER LIVE (prep queue item 2 done)

All 7 water regions (5 wave + 2 fall) have native-res 36-drawing cycles
registered in living/regions.json; render-living plays them held on twos.
The what-moves audit (living/heat-native-cycles.py) caught and fixed two
trespasses: rippling collector seals (mask-bare-ground --seal-red) and a
rippling porter's basket weave (per-region exclude rects). vmin 0.66 for
wave boxes with toned banks. First grammar probe SHIPPED:
film/FLOAT-MIDSTREAM.mp4 (14s native float, living-vs-static control
1.4-1.7% pixels differ = water only). Evidence:
living/evidence-native-water-motion.png, native/*/motion-heat.png.
NEXT (queue item 3): more float/pan idiom paths through unvisited
territory; gust verdict pending Ryan's eyes on AB-GUST-VS-SWAY.mp4.

## 2026-08-19 night — REGRESSION FIXED: three scale laws, ensemble shipped

Ryan condemned FLOAT-MIDSTREAM (correct). Mechanisms found and fixed:
(1) motion px params are SHOT-SCALE — class values are 720-space, ×2.34
at native (peak 28.3px = proven 1.67% current); (2) max-thick 3 dropped
native water lines as masses (midstream ink 6→16.7%); (3) VIEW SCALE is
part of the recipe — cel water carries at k≈2.0-2.4 (the proven clip's
scale), fov≈1 native is for detail holds only. Pine inventory box was
bare cliff — corrected from the Z1 plane; native gust cycle registered.
SHIPPED: film/BRIDGE-ENSEMBLE.mp4 (fov 2.3→1.7 push, whole bridge cast,
water streaming, pine gusting twice). Awaiting verdict.

## 2026-08-19 night II — BACK TO THE DEPTH WORLD (Ryan's correction)

Ensemble verdict: line-water alone is not the carrier; "let's start
utilizing some of this depth of field… very subtle 3D parallaxing."
DEMOTION: render-living 2D lane = scaffolding for stack-less zones only.
The film's engine is render-parallax over zone worlds + living planes.
SHIPPED: z1/BRIDGE-PARALLAX.mp4 — bridge theater, dolly z 0→0.14 (half
the ceiling-shot envelope), pine GUSTING (plane gust cycle via
living-gust.json), water + fan alive. Static A/B: 3.4→4.7% of frame
alive, living-planes-confined. Awaiting verdict.

## 2026-08-19 night III — VERDICT: BRIDGE-PARALLAX PASSES

Ryan: "I think its working. subtle. very very subtle. barly notice it.
but it doesnt suck." First positive gate of the day. THE RECIPE LOCKS:
zone depth world (plane-fit + tilts) + subtle dolly + living plane
cycles + gust pine = the film's default shot engine. His one note:
borderline too subtle -- an A/B at the full approved envelope (z 0->0.24)
rendered for his pick of strength.

## 2026-08-19 night IV — 2X WINS: default dolly locked at z 0->0.24

Ryan on the A/B: "oh yeah stronger is better." The film's default depth
move = the full proven envelope (z 0->0.24 over 16s, plane-fit, tilts).
path-bridge-parallax-2x.json is the reference path shape. Next direction
from him: camera TILT (rotation) on top of translation, and eventually
mesh-level 3D from the composed depth field — see
docs/2026-08-19-how-the-scroll-moves.md.

## 2026-08-19 night V — CAMERA ROTATION: BRIDGE-FLOAT rendered

render-parallax now takes rx/ry/rz (degrees) in path keys — homography
H = K·Rᵀ·K⁻¹, fpx = fov·width. Rotation adds no parallax (same center of
projection); the value is the keystone drift. Commit `72af9c9`. Verified:
zero-rotation re-renders byte-identical; signs probed (+ry pans camera
left, +rx tilts down). BRIDGE-FLOAT.mp4 (journey/z1/) = the 2X dolly +
ry→−1.0/rx→−0.6/rz→0.25 easing from zero; frame 0 byte-matches the 2X,
no edge reveal. Opened for Ryan's verdict next to BRIDGE-PARALLAX-2X.
Path: journey/z1/path-bridge-float.json. Evidence: report
2026-08-19-seq-z1.md. Agreed next after his verdict: per-plane relief
displacement (LDI hybrid) from compose-depth's field.

## 2026-08-19 night V verdict — FLOAT PASSES. Next: relief displacement
Ryan on BRIDGE-FLOAT: "yep. hit it" (go-ahead on the LDI hybrid).
Rotation is now part of the shot vocabulary. Building: per-plane relief
displacement from compose-depth's field — cards keep their completed
edges, surfaces gain continuous parallax within each card.

## 2026-08-19 night VI — RELIEF DISPLACEMENT: RIVER-ENTRY A/B on screen
render-parallax --relief shipped (222ccd1): per-plane DAv2 relief,
high-passed so authored depth stays law; radial remap about the camera
axis, null structural at camZ=0. Figure check excluded 4 of 7 candidate
planes (travelers hiding in trees/rocks/ledges — evidence in report);
roster = both gorge walls + foreground-rock-mass. First probe showed
zero effect because the BRIDGE SHOT never frames those planes — lesson:
a feature proves nothing until the shot stages it. Probe moved to
path-river-entry.json (shot-1 territory, 42s map). On screen:
RIVER-ENTRY-RELIEF.mp4 + AB-RELIEF-VS-FLAT.mp4 (left flat, right
relief; drawtext unavailable in this ffmpeg). Evidence:
evidence-relief-maps.png, evidence-relief-what-moved.png. Awaiting
Ryan's verdict.

## 2026-08-19 night VI verdict — RELIEF WINS ("right wins")
Relief displacement joins the locked shot vocabulary. Default recipe is
now: zone world + plane-fit z-step 0.30 + dolly to 0.24 + rotation into
the travel + living cycles + relief on figure-free masses. Next: the
gorge-facing shot that stages the walls' relief (band 0.6, already
mapped), all elements stacked.

## 2026-08-19 night VII — GORGE-PUSH: all elements in one take
First full-stack shot: path-gorge-push.json = dolly 0->0.24 + rotation
into the cleft (rx -0.6, ry 0.5, rz -0.2) + living upper-stream/gust +
wall relief (band 0.6) on the gorge mouth framing (plate upper band,
first time rendered — stills showed no holes, sealed layers cover it).
Frame 0 byte-matches the stills control. On screen: GORGE-PUSH.mp4.

## 2026-08-19 night VIII — SEQ-Z1-v2: the full 42s cut, one delivery
Ryan called out the probe loop ("10 second video all night?") — answer
was the whole film. film/SEQ-Z1-v2.mp4: all 7 Chowder Julius shots from
the Z1 world on the locked recipe (dolly + rotation + living + relief),
cut on beats.json line starts, call at full volume (stitch's --music
ducks to bed level — remuxed 1:a direct; fix stitch or add --music-full
later). Shot framings verified by stills before render: Ge hold (shot 5)
is dead-on — fan raised, deer beside. shots.json + paths/ + render
script in film/. v3 upgrades: deer walk composite, Z2-Z6 zone worlds
for shots 3/6/7, 4K master.

## 2026-08-19 night IX — ONESHOT-42: the continuous take
Ryan rejected the 7-cut structure ("violent, abrupt shifts... should be
one smooth, long, continuous shot"). film/ONESHOT-42.mp4: one 42s
camera, six keys at beat times, bottom-to-top through Z1 — river open,
rise past the ox party, land tight on Ge for the 5s silence (identical
keys = true full stop, living ink only), lift into the gorge on the
explosion, settle by the falls. Full stack throughout. Path:
film/paths/oneshot-42.json. The camera LANDS on beats instead of
cutting on them. Cuts-on-beats structure retired for this film.

## 2026-08-19 night X — FULL-SCROLL-FLIGHT: the whole painting, one shot
Ryan's demand ("we have this whole huge painting") answered: all five
flight worlds built TONIGHT from the existing global dots (z3w-z6w cut
full-width for the landscape camera; z2's portrait-era rect bypassed),
every zone frame-zero 0px / 100% claimed. film/FULL-SCROLL-FLIGHT.mp4 =
42s, one apparent shot, river to peaks: z1 (living water + relief) ->
z3w gorge push -> silence hold + mid-hold handoff -> z4w/z5w compound
on the explosion -> z6w mist release. Handoff law enforced in
compile-flight.py (identical rest cameras through every crossfade;
measured z1->z3w agreement mean|diff| 2.26). Dot surgery tonight:
porter-ledge, resting-ledge, rear-pines, main-hall moved off figures/
walls; compound-court DROPPED (contourless wash, Law 7). Desktop link
refreshed. v2 upgrades: living water z3w-z6w, relief for upper zones,
deer walk, 4K.
