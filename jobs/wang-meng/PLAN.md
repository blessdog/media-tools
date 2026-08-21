# 葛稚川移居圖 — the plan

Written 2026-08-21, after a week of fragments and no film. Ryan: *"First, tell
me what we're doing, where we're going. In simple terms."* This file is the
answer, and it is the SSOT for what "done" means. `STATE.md` is generated and
says what exists right now; this says what we are aiming at.

## The end state

A film in which Wang Meng's scroll is **alive** — water runs, foliage stirs in
gusts, the figures move — and a camera travels up through it from the river at
the bottom to the summits at the top, at a pace a narrator can talk over.
1920×1080. Roughly three minutes for the silent pass; longer once narration
sets the pace.

Two derivatives fall out of the same assets and are not separate projects:

- **Indefinite mode.** The motion is already endless — cycles are indexed
  `(frame // hold) % count` (`tools/render-living.py:119`) — so a screensaver
  needs a closed-loop camera path and cycle lengths that do not re-sync, not
  new animation.
- **Museum edition.** A curator narrates and the film responds: highlight the
  passage they are pointing at, bolden its lines, dim the surround, hold.
  Every region already has a mask, which is exactly what an emphasis layer
  needs.

## Two jobs, and they are not the same job

1. **Make the picture move.** No camera involved. This is the deliverable.
2. **Move the camera through the moving picture.** This is cheap and looks
   like progress, which is why it keeps getting done first. See the MOTION
   BEFORE CAMERA law in `../../CLAUDE.md`.

## Where each phase stands

Every benchmark below is a thing that can be looked at or counted, not a
feeling. "Pass" means Ryan has seen it and said so, or a number is on the
board.

### Phase 0 — THE RISE v1 · **in flight, 2026-08-21**

The first assembly. Everything currently animated, one continuous pass,
bottom to top, with the camera moving toward motion and nothing hidden.

| | |
|---|---|
| Build | `film/build-rise.sh` → `film/THE-RISE.mp4` |
| Length | 176s — z1 53s, z3w 70s, z4w 20s, z5w 9s, z6w 24s |
| Benchmark | one file, 1920×1080, plays end to end without a black frame or a cream bar |
| Benchmark | at least one approach per zone that has animation; **zero** invented moves in zones that have none |
| Pass | Ryan watches it through and can name what is dead in it |

The last 33 seconds are a straight rise with nothing moving. That is not an
oversight, it is the report.

### Phase 1 — Close the water gaps · **hours**

Six water regions **already have finished 36-frame cycles on disk** and are
invisible to the film. They live in `living/regions.json` as boxes; the
builder reads `living/living-polys.json`, which takes polygons. That is the
entire bug.

| Region | State |
|---|---|
| `w-river-entry` | cycle rendered, not registered |
| `w-river-foreground` | cycle rendered, not registered |
| `w-bridge-rapids` | cycle rendered, not registered |
| `w-upper-stream` | cycle rendered, not registered |
| `f-left-tall-fall` | cycle rendered, not registered |
| `f-station8-fall` | cycle rendered, not registered |

| | |
|---|---|
| Benchmark | z1 `built.json` goes 18 → ~30 patches |
| Benchmark | all six ids appear in `journey/*/living-masks/index.json` |
| Benchmark | the opening shot of THE RISE has moving water in it — right now the river the film opens on is a still |
| Risk | the two boxes refuted by eye (`f-left-tall-fall` is bare cliff; `w-upper-stream` is the same fall's lower half) must be re-cut from the corrected polygons, not from the old boxes |

The deeper fix — merging the two region catalogues into one file — is an
`open` claim marked `proven: false` and needs a verdict before anyone touches
it. Phase 1 is the additive version and is reversible.

### Phase 2 — The figures · **the real gap**

Not one figure moves. Ten figures are catalogued and `living/cycles/` holds
exactly one thing: `bridge-proto`, a 73-frame cycle of the Ge Hong scene made
earlier and never wired in.

| Target | Motion | Notes |
|---|---|---|
| Ge Hong at the bridge | fan and robe stir | puppet masks survive (`motion/mask/gehong/`: fan, sleeve, hem, head); the frame sequence does not |
| The deer | walk, or a considered hold | hold is a legitimate answer if the walk fights the stillness |
| The servant boy (band 05, y≈6500) | walk + wave | both hands hold gourds — the wave requires **inventing ink**, which Ryan permitted on 2026-08-21: *"as long as it looks hand-drawn"* |
| A bird | flight across the gorge | pure invention, in Wang's hand |

| | |
|---|---|
| Route | `cut-stroke.py` (one card per limb, pivot at the joint) → `walk-figure.py --limbs` → register |
| Benchmark | ≥4 cycles in `living/cycles/`, each figure ≥40px of ink (below that a hinge reads as jitter) |
| Benchmark | Ryan spots the movement in THE RISE **without being told where to look** |
| Law that governs it | existing marks move rigidly and are never deformed; new marks may be drawn in Wang's hand |

### Phase 3 — The summits · **needs a verdict, not work**

z5w has 13 patches, z6w has 3. Thirteen `gust-far` summit polys were built and
then removed the same day — Ryan: *"peaks shouldnt wobble."* Mist was refuted
outright: there is no mist ink in this painting, the mist is bare silk.

So the question is not "how do we animate the summits," it is **"should the
summits move at all?"** Two honest answers:

- **They are correctly still**, and the camera passes through them faster and
  ends on a held frame. Costs nothing, and may be the better film.
- **The distant foliage stirs at half amplitude**, which is what `gust-far`
  was, rebuilt without the polys that wobbled rock.

| | |
|---|---|
| Benchmark | a verdict in the store answering `should-the-summits-move`, with the A/B that decided it |
| Pass | either answer, recorded — an unanswered question here blocks the film's last 33 seconds |

### Phase 4 — Finish the catalogue · **background work**

185 detections merged to 136 objects: 108 tree, 38 rock, 10 figure, 10 water,
7 trunk, 3 building, 3 structure, 2 void, 1 seal, 3 unknown. It covers only
master y 4712–12594 — the middle. Bands 01–02 at the bottom and 07–08 at the
top are uncatalogued, which is why the summits have no authored regions.

| | |
|---|---|
| Benchmark | catalogue spans y 0–15923 with no gap |
| Benchmark | every `tree` carrying `leavesVisible: true` has a foliage decision — animated, or `still` with a reason |

### Phase 5 — Narration · **after the picture is finished**

The camera pace is currently set by a constant (110 master px/s). Once there
is a script, the pace is set by the sentence being spoken, and the approaches
land on the beat where the narrator names the thing. Not before.

### Phase 6 — Indefinite mode and the museum edition

Bookmarked, not scheduled. Both are camera-and-composite work over assets that
already exist; neither needs new animation.

| | |
|---|---|
| Indefinite | closed-loop camera path + co-prime cycle lengths (water 36, foliage 96 currently re-sync every 8s) |
| Museum | per-region emphasis layer — highlight, bolden, dim the surround — driven by narration cues |

## The order, and why

Phase 1 before Phase 2 because six finished cycles sitting unwired is the
cheapest motion in the project and it fixes the film's opening shot. Phase 2
before Phase 3 because a moving figure is what makes a viewer lean in, and
because Phase 3 may turn out to be a decision rather than a build. Phase 4
runs alongside anything. Phases 5 and 6 are downstream of a finished picture
and must not be started early — that is the corner that keeps getting cut.

## The rule that governs all of it

Assemble and show the whole thing at every phase boundary. A per-region test
strip is a diagnostic, never a deliverable. The week that produced no film
produced dozens of them.
