# Wang Meng journey — full-scroll flythrough via 散点透視 zone worlds

**Date:** 2026-08-17 · **Status:** approved (design), pre-implementation
**Job:** `jobs/wang-meng/journey/` · **Painting:** 葛稚川移居圖, Wang Meng,
Yuan, ink and colour on paper, 6586×15923 master at
`corpus/grabs/wang-meng-王蒙_ge-zhichuan-moving-to-the-mountains-葛稚川移居圖.png`

## Goal

One continuous vertical (9:16) video. The camera enters at the river mouth,
travels the route Ge Hong's procession takes through the painting — eleven
stations, bottom to top — and releases into the peaks. The painting is
experienced as terrain from inside: z-axis travel, parallax, each region seen
from the eye the painter gave it. Every rendered pixel is Wang Meng's; depth
is authored, never estimated (monocular estimation is measured to fail on this
material: 48.9% R² vs image row on the painting, 88.4% on generated imitation).

Duration is NOT prescribed; it falls out of path length at a drone-slow speed.
Reference for feel only (not format): Zhangjiajie drone footage — terrain-
relative, floating, continuous.

## Non-goals

- No generated territory. Models fill only occlusion bands behind planes
  (`inpaint-planes --method flux`) and, in principle, true scroll edges the
  route never approaches.
- No invented calligraphy anywhere. The real inscription/seals may appear.
- No music/narration decisions in this spec.
- Not the Krea invented-worlds lane; this is the real-painting lane.

## Why zone worlds (approach B, approved)

散点透視: the scroll has no single projection. The river is seen level
(平遠), the gorge is looked *through* (深遠), the peaks are looked *up at*
(高遠). One globally consistent 3D world would contradict the painting; six
zone worlds, each planed and tilted for its own viewpoint, match it. Wang Meng
separates the zones with mist bands and water voids — the handoff corridors
are already painted. Rejected: A (one global stack — single projection fights
the painting, nothing watchable until 60–100 objects authored), C (coarse
mega-planes — the 720×1280 pilot crop needed 11 planes; fewer reads flat at
drone proximity).

## World model — the coordinate SSOT

Everything speaks **master pixels**. `jobs/wang-meng/journey/world.json`
records:

```json
{ "master": "<repo-relative master path>",
  "masterSize": [6586, 15923],
  "k": 2.34,
  "note": "k = master px per rendered px, proven on the pilot shot" }
```

- Each zone stack's `layers.json` records its master-rect (`masterRect`).
- The journey path is authored ONCE in master coordinates as a spline through
  the stations. A small tool maps the world path into any zone's local
  normalized coordinates for `render-parallax` (`map-path.py`: world path +
  zone layers.json → zone-local path JSON; one job, no rendering).
- All paths inside JSON files are relative to the JSON file's own directory
  (locate-crop was fixed to this convention 2026-08-17 after the cwd-relative
  master path bug).

Output frame: 720×1280 (proven working scale; a 1080×1920 re-render from the
same worlds stays below master resolution and remains available later).

## Zone map (DRAFT rects, master px — refined at authoring)

Overlaps are the handoff corridors, parked on painted seams.

| zone | region | master rect (x0,y0,x1,y1) | 散点 eye | corridor with next |
|---|---|---|---|---|
| Z1 | river + bridge | 425, 11466, 6586, 15923 | 平遠 level glide | resting ledge (~y 11500–12100) |
| Z2 | left-bank climb | 0, 9449, 4248, 12104 | climbing, level-to-tilted | rapids (~y 9450–10100) |
| Z3 | gorge + fenced cliff path | 0, 5945, 4566, 10086 | 深遠 through stacked screens | autumn shelf (~y 5950–8050 east side) |
| Z4 | waterfall traverse | 1593, 4565, 6586, 8069 | 深遠→rising | compound tree line (~y 4570–5950) |
| Z5 | compound arrival | 637, 3503, 4990, 5945 | slightly-above, settling | mist band above compound (~y 3500–4250) |
| Z6 | peaks + mist release | 637, 0, 6586, 4247 | 高遠 looking up | — (ends the piece) |

## Stations (journey spline knots, master px, DRAFT)

1. river entry (3186, 15342) → 2. ox party on the bank (3186, 13059) →
3. bridge, Ge + deer (1593, 12528) → 4. porters climb (849, 11679) →
5. rapids, left bank (956, 10511) → 6. fenced cliff path (531, 6795) →
7. gorge traverse (2655, 7326) → 8. under the waterfall (4141, 5733) →
9. THE COMPOUND (1805, 4724) → 10. mist release (3186, 2761) →
11. summit + far blue (3504, 1380)

Visuals: `jobs/wang-meng/motion/pan/route-draft.png`, `zones-draft.png`.

## Per-zone pipeline (existing tools; the human pass is the depth authoring)

1. Cut the zone region from the master at k (records `masterRect`).
2. `segment-points --review` — Pissjug clicks objects and assigns depth order
   (~10–15 planes/zone, like the pilot's 11).
3. `inpaint-planes --method flux` — occlusion bands painted behind planes;
   hard-composite bounded; frame-zero control must show 0 px changed.
4. `geometry.json` per zone — the 散点 tilts (tiltX pitches ground away with
   height, tiltY yaws cliff faces): Z1 level, Z3 receding screens, Z6 pitched
   up. Per-zone, because per-zone eyes are the point.
5. `map-path.py` slices the world spline; `render-parallax --plane-fit`
   renders the zone's span.
6. Watch it. A zone is done only when its own flythrough is watchable.

Z1 seed: the pilot 11-plane stack (`layers-flux`) — its depth ordering and
object choices carry over; the footprint is re-cut to the full zone rect and
re-segmented at that size.

## Camera choreography

Per zone the camera inhabits that zone's eye. Z1: level glide over water,
across the bridge, a pause on Ge. Z2: rising traverse past the porters. Z3:
push THROUGH the stacked screens along the fenced path — the deepest z travel.
Z4: lateral traverse under the waterfall. Z5: slow settle at the compound
gate (a figure waits on the veranda). Z6: rise, look up, release into mist
and the far blue peaks. z-pushes concentrate at stations; travel between
stations is smooth spline. fov stays near 1.0 (native pixels); parallax comes
from z and the tilts, not zoom.

## The handoff gate — first risk retired first

Before any authoring past Z2: render the shared resting-ledge corridor from
BOTH Z1 and Z2 stacks along the same world-path span. Look at the pair, and
difference them. Outcomes:

- Renders agree to invisibility → crossfade inside the corridor.
- They disagree visibly → handoffs move fully into mist/water whiteouts: a
  straight cut under whiteout, which cannot fail.

Nothing downstream depends on which mechanism wins; the gate only picks it.

## Verification and controls (law from the pilot)

- Frame-zero control per zone: inpaint/extend steps change 0 px at rest.
- Every visual claim gets a rendered image opened on screen, never prose.
- Null before believing any motion metric (static/synthetic-zoom controls).
- Depth is never estimated; any tool that would estimate depth on this
  material is out of scope by measurement.
- Fills report sampled vs generated px in their JSON manifests.

## Phase map — all phases ship, in order, each with completion criteria

1. **World + Z1.** `world.json`; Z1 re-planed at full footprint; journey
   spline drafted through stations 1–4. DONE WHEN: Z1 flythrough (entry →
   porters) is watchable and passes its controls.
2. **Z2 + handoff gate.** Z2 authored; corridor rendered from both stacks;
   mechanism chosen. DONE WHEN: one continuous Z1→Z2 cut plays through the
   seam without a visible world-switch.
3. **Z3.** The 深遠 push. DONE WHEN: continuous cut reaches the fenced path.
4. **Z4.** DONE WHEN: continuous cut reaches the waterfall.
5. **Z5.** DONE WHEN: arrival at the compound plays, pause at the gate.
6. **Z6.** DONE WHEN: full journey entry→release plays end to end.
7. **Assembly + life pass.** Grade; `animate-strokes` on river, rapids,
   falls; mist drift — on top of the LOCKED camera. DONE WHEN: final cut
   rendered, watched, approved.

## Worked example — phase 1, concretely

Z1 rect ≈ (425, 11466)–(6586, 15923): 6161×4457 master px → 2633×1905 at
k=2.34. Pissjug's pass: one `segment-points --review` session (~15 objects:
water, near rocks, far rocks, bank, bridge, Ge+deer, ox party, two great
trees, servant groups, cliff walls). Then flux occlusion fill (~$1–2), tilts
(water dead level, bank slight tiltX, trees upright), path stations 1→4,
render at 720×1280, watch. Existing pilot work that carries: depth order for
the 11 pilot planes, the measured wander envelopes (0.3–0.5 wander needs
53–150px reach), the flux fill prompt, all controls.

## Open items

- Exact zone rects and station coords are DRAFT — refined when each zone is
  cut, against the master, with Pissjug's eyes on the overlay.
- Whether the piece ends before or at the inscription/seal (real calligraphy,
  allowed) — decided at Z6 authoring.
