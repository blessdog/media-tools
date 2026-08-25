# RISE 5 — the locked plan

*2026-08-25. Supersedes `archive/superseded-plans/2026-08-25-rise5-design-ONE-UNBROKEN-RISE.md`.*
*READ THIS FIRST after any compaction or new session.*

---

## The end state

A film of 葛稚川移居圖 in which **the mountain is alive and a camera explores it.**
Under four minutes. Rendered through **Blender**, not the hand-rolled renderer.

Ryan's framing, 2026-08-25:

> "Think about the whole painting as the mountains alive. And we are capturing it
> through these beautiful shots as we kind of go from a wide angle and crop in,
> pan around as we zoom out. Should go in and out, left, up, down, right."

Three things must be simultaneously true, and none of them is true today:

1. **The foliage cut is bushels, not confetti.** Today only the tree beside Ge is
   cut correctly (19 cards). `s-great-trees-upper` gets 147 cards, 113 of which
   hinge on nothing.
2. **The motion is scattered, gentle and sparse.** A couple of swings, a second
   or two of quiet, then a smaller shuffle in a *different direction*. Most trees
   never move. Never exactly one moving thing in a frame.
3. **The camera does real shot work**, in and out and around, with actual
   parallax — measured, not asserted.

---

## What is already settled — do not re-litigate

| settled | detail |
|---|---|
| **Renderer** | Blender 5.2.1 LTS. `tools/blender-multiplane.py` builds the scene headless; measured 0.75 s/frame, parallax differential **1.091×** at a 43.3% dolly vs THE-RISE's **1.009×** at 5.5%. |
| **Authoring surface** | Frame By Plane 7.1.18, in the GUI. Its importers do **not** register headless (63 of 353 operators register in `-b`, zero importers) — `knowledge/frame-by-plane-importers-are-gui-only.md`. |
| **Ridge pines are HELD** | A tree whose ink is continuous with the rock has no card boundary. `knowledge/store/a-tree-welded-to-rock-cannot-be-carded.md`. This retires the summit-coverage goal — 52.3% was measuring the defect. |
| **Swing math untouched** | Ryan approved the tree beside Ge at `carrier 1`, `swing 6`, `flutter 0.15`, `gust 0.10,0.08,0.22`, `gust-rest 0.15`, `under: hold`. That approval is for **that tree**, not the technique everywhere. |
| **`under: hold`** | A swinging card reveals more leaves, never bare ground. |
| **Water is fine** | The **waterfall** is the gap, not the water. |
| **No regeneration** | Cinemagraph models (DreamLoop, LTX, Loopa) repaint brushwork. Wrong technique here, permanently. |
| **RISE 4 shots** | Retired at tag `hard-pivot-rise5-prep`. Nothing gets assembled from existing renders. |

---

## Phase map

Each phase ends in something Ryan looks at. Phases 0–2 are strictly ordered;
3 and 4 can run in either order once 2 lands.

```
  0  THE CUT          bushels on every tree, not just Ge's
  1  THE MOTION       scattered gentle events, varied direction
  2  WHAT MOVES       sparse; ridge pines held; never one lone mover
  2b THE FIGURES      not one figure moves — carried from the 08-21 plan
  3  THE WATERFALL    the one thing that visibly does not move
  4  THE SHOTS        Blender camera work; the Blender depth ceiling is UNMEASURED
  4b THE CATALOGUE    y 0–4712 and 12594–15923 uncatalogued; runs alongside
  5  ASSEMBLE         cut, review, ship to the Desktop symlink
```

Phases 0–2 are the deliverable: MAKE THE PICTURE MOVE. Phase 4 is the camera and
it comes last on purpose — see *Two jobs* below, and the MOTION BEFORE CAMERA law.

---

## PHASE 0 — the cut

**The defect, measured.** Identical class settings on all three trees, no
per-region overrides anywhere:

| tree | cards | hinged at a branch | hinged at an arbitrary foot |
|---|---|---|---|
| `s-pine-over-bridge` (broadleaf, APPROVED) | 19 | 12 | 7 |
| `s-gorge-big-canopy` | 59 | 55 | 4 |
| `s-great-trees-upper` | **147** | 34 | **113** |

**Mechanism.** `branchRadius auto` = 0.55 × that tree's own p99 stroke
half-width. It reproduces Ryan's 5 on Ge's tree and yields 2–3 on trees drawn
with thinner strokes. A 2px morphological opening cannot isolate a branch, so
the cutter slices at every thin neck and shreds one spray into worms.

**Work.** Find a basis for the branch radius that holds across all 170 regions.
Candidates to test, cheapest first — but **LAW #0 applies: search for how cutout
riggers solve limb detection before writing any of these.**
- scale from crown size / card area rather than stroke width
- skeletonise the ink and cut at junctions rather than at thin necks
- SAM/Roboflow: let a click define the bushel and skip the automatic cut entirely

**Done when:**
- `s-pine-over-bridge` still produces **19 cards**, unchanged. If Ge's tree moves,
  the fix is wrong.
- No region has more than **35% of its cards hinged at a foot**. (`cardsFoot /
  cards` in each `drawings/cycle.json`. Today: pine 37%, gorge 7%, great-trees
  77%.) *This number is CHOSEN, not measured — revisit once three trees pass.*
- A `--card-sheet` contact strip of six trees, opened for Ryan, reads as bushels.

**Evidence lands:** `jobs/wang-meng/evidence/cards/`

---

## PHASE 1 — the motion

**What Ryan asked for, in his words:**

> "I want the trees to blow naturally, not faster. Just a couple of swings. And
> then a second or two later, have it gently breeze again, a tiny little shuffle.
> Move in a different direction. Just tiny little movements here and there. Not
> just a single one, and then dead."

**What is built.** One gust envelope, one sine, one wind direction (`--angle 8`),
all cards on one clock offset by position. Attack+hold+decay = 0.40 of an 8s
loop, so 60% of every loop sits at 15% amplitude. That is literally "two or
three movements, then dead still."

**What the model needs to become.** Several small events per loop, at
**irregular** spacing, each with **its own direction**, none of them larger than
today's peak. Explicitly:
- **not faster** — Ryan said so directly
- **not bigger** — amplitude is ruled out twice
- **not the broadband turbulence** — refuted 2026-08-24, `knowledge/subtle-beats-continuous-for-this-painting.md`

**Open question for Ryan, needed before building:** roughly **three or four
events per 8 seconds**, or slower — a few events per **twenty** seconds? He was
asked and the conversation moved on. *Assumption if unanswered: 3 events per 8s
loop, the largest at today's peak and the others at 40–60% of it.*

**Done when:**
- An A/B of one tree, current vs new, opened for Ryan, and he says the rhythm is
  right.
- The loop still closes seamlessly (measured: frame 0 vs frame N-1 seam).
- Peak degrees unchanged from today's approved value.

**Evidence lands:** `jobs/wang-meng/evidence/`

---

## PHASE 2 — what moves at all

> "Most of the trees on the canvas — I don't even want most of them animated,
> just little specks here and there in a shot. Not every tree needs to be moving
> like a full windstorm is blowing through."

And the failure mode he named:

> "It's weird when you're on a shot for about five ten seconds and one single
> bush in the middle of the shot moves, has two or three movements, and then is
> dead still."

**Work.**
1. Ryan marks the sheets. Four contact sheets exist at
   `jobs/wang-meng/evidence/weld/sheet-{0..3}.png`, cells numbered **000 at the
   river to 169 at the summit**. He marks the few that should be alive;
   everything unmarked is held. This also resolves the ridge pines for free.
2. Add `held: true` per region in `regions.json`; the builder skips them.
3. **The lone-mover rule:** no shot may contain exactly one live region. Enforced
   as a check against the shot's frustum, not as a guideline.

**Done when:**
- Every one of the 170 regions has an explicit alive/held flag.
- `check` reports zero shots with exactly one live region.
- The summit renders with no foliage motion and does not read as dead.

---

## PHASE 3 — the waterfall

> "The water looks fine as well. Where I'm telling you that it's not animated is
> like the waterfall."

`w-gorge-fall`, `w-compound-fall`, `w-lower-pool`, `w-midstream` are all **built**
and the previous film simply never framed them. Two possibilities and they need
separating with pixels, not reasoning: the shots missed them, or the fall motion
is invisible at shipping framing.

**Done when:** each of the four renders at the fov the film actually uses, opened
for Ryan, and each visibly moves — or is diagnosed with a mechanism.

---

## PHASE 4 — the shots

**Vocabulary is already written**: `jobs/wang-meng/film/MOVES.md` — push in, pull
out, pan, tilt, diagonal drift, anchored zoom, drifting anchor, opposition move,
hold-move-hold, speed ramp, breathing. Ryan's complaint is that it is
underutilised, not that it is missing.

**Rules that bind every shot:**
- **fov ceiling 2.2**, and the frame must always contain a *region* — a gorge
  mouth, a bank, a compound — never one tree centred and isolated.
- **Real z travel.** `check-camera-plan.py` gates the plan before a frame
  renders. Target differential ≥ **1.05×** near-vs-far growth. THE-RISE was
  1.009×. *Chosen, not measured — revisit after the first three shots.*
- **No recycling.** Every shot renders fresh through Blender.
- Under four minutes total.

**Work.** `blender-multiplane.py` must gain: image-sequence textures per plane
(so the living layer plays), and camera paths read from a shot JSON.

**Done when:** every shot passes the camera gate, and a contact sheet of first
frames is opened for Ryan before any full render.

---

## PHASE 5 — assemble

Cut, review, `~/Desktop/WANG-MENG-LATEST.mp4` refreshed, journal entry appended,
README era updated.

---

## CARRIED FORWARD from the 2026-08-21 plan — still live, was missing above

The 2026-08-21 `PLAN.md` was written after "a week of fragments and no film" and
called itself the SSOT. This document replaces it (archived at
`archive/superseded-plans/2026-08-21-PLAN.md`), and these parts of it are
UNCHANGED and still binding.

## Two jobs, and they are not the same job

1. **Make the picture move.** No camera involved. This is the deliverable.
2. **Move the camera through the moving picture.** This is cheap and looks
   like progress, which is why it keeps getting done first. See the MOTION
   BEFORE CAMERA law in `../../CLAUDE.md`.

### PHASE 2b — THE FIGURES · *the omission in the plan above*

**Not one figure moves.** This was called "the real gap" on 2026-08-21 and the
RISE 5 plan above did not mention it at all. The `what-moves` LAW names robes
first: *"just the delicate things move. Their robes, the water ripples, leaves."*

Ten figures are catalogued and `living/cycles/` holds
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

### PHASE 4b — THE CATALOGUE GAP · *background, runs alongside anything*

185 detections merged to 136 objects: 108 tree, 38 rock, 10 figure, 10 water,
7 trunk, 3 building, 3 structure, 2 void, 1 seal, 3 unknown. It covers only
master y 4712–12594 — the middle. Bands 01–02 at the bottom and 07–08 at the
top are uncatalogued, which is why the summits have no authored regions.

| | |
|---|---|
| Benchmark | catalogue spans y 0–15923 with no gap |
| Benchmark | every `tree` carrying `leavesVisible: true` has a foliage decision — animated, or `still` with a reason |

### DEPTH — what is approved, and one open number

Approved technique is **breath**: camZ as a cosine laid across the leg, never a
permanent travel. `depth-may-resize-never-deform`. Multiplane truck, sheet warp
and disparity spacing are all REFUTED.

- **render-parallax units:** peak camZ **0.18** at `--z-step 0.30` is a measured
  ceiling. 0.45 tore the canvas. AND the opposite failure is real — 13–31% of
  every leg sat at camZ < 0.02, which is a pan by construction.
- **Blender units are NOT the same parameter.** Measured 2026-08-25: a dolly of
  0.52 world units (43.3% of stack depth) on z3w returns `check-holes: intact,
  0 holes, 0 cream bars` across 12 sampled frames. **The Blender ceiling has not
  been found and must be measured before Phase 4 authors anything.** Do not
  carry 0.18 across; it is a number from a different renderer's projection.

## The rule that governs all of it

Assemble and show the whole thing at every phase boundary. A per-region test
strip is a diagnostic, never a deliverable. The week that produced no film
produced dozens of them.

---

## What I still need from Ryan

Neither blocks Phase 0. Both are asked again at the phase that needs them.

1. **Phase 1:** event frequency — ~3–4 per 8s, or a few per 20s?
2. **Phase 2:** the marked sheets. Cells 000 (river) → 169 (summit).
3. *(Not on the critical path)* whether an iPad exists, which decides whether the
   Procreate → Frame By Plane authoring path is real or theoretical.

---

## Standing constraints

- **LAW #0** — search before building anything in any phase; search again after
  each failure, with the words the failure taught.
- **LAW #0.5** — Ryan's architecture calls are decisions. Open ones live in
  `~/.claude/knowledge/directives.json`.
- **LAW #0.6** — archive, never delete. Superseded implementations move to
  `archive/` with a header, still runnable.
- **LAW #1** — name a visual, `open` it in the same turn.
- **Evidence lands in the repo at creation time.** Commit at the moment of
  learning.
