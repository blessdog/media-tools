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
path. Budget cap $10. Checkpoints judged by Claude against pre-registered
criteria (dossier §07), all evidence saved for morning review. Run 2
(authored depth) only if run 1 ink holds. Provisioning attempt 2 in
progress (attempt 1 died: box image lacked python3-venv — fixed; default
manifest's downloader also had to be killed twice). Known deps issue:
repo's pinned pandas has no py3.12 wheel — patch modern pandas into venv
during the weights download, extend smoke test to import create_input deps.
