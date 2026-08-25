> **SUPERSEDED 2026-08-25, same day it was written. ARCHIVED, NOT DELETED —
> LAW #0.6: a dead end is data.**
>
> **What it got right and is still live:** ridge pines held; fov ceiling 2.2 with
> a region in frame rather than a single tree; the swing math untouched; the
> water regions already built; parallax measured at 5.5% of stack depth.
>
> **What killed it:** the "one unbroken rise, no cuts, 5:00" shape. Ryan, hours
> later: *"What I don't want is a slow pan, the same path we've been doing over
> and over… I want to start over. It doesn't need to be a four-minute movie
> either."* He wants the painting treated as alive and covered by REAL SHOTS —
> wide, crop in, pan around, zoom out, in and out, left, up, down, right.
>
> **Why it is kept:** the zone-overlap arithmetic (z1→z3w = 2,998 master px = 66s
> of dissolve room) and the z1-is-only-70%-wide constraint are measured facts
> that any future cut-free passage would need again. Superseded by
> `docs/plans/2026-08-25-rise5-plan.md`.

# RISE 5 — one unbroken rise

*Design, 2026-08-25. Supersedes the RISE 4 shot list, retired at tag
`hard-pivot-rise5-prep`.*

## What it is

A five-minute film of 葛稚川移居圖 as one continuous camera move from the bottom
frame of the scroll to the summit. No cuts. Silent; narration is written later
over finished picture.

## Why RISE 4 was rejected

Ryan, 2026-08-25, on THE-RISE: *"It doesn't make sense to pan up close to the
canvas and then zoom into a tree that's not moving and then move a wave once…
Feels like you're recycling everything… forget everything and start over with a
rise five."*

Five defects, each with the mechanism that produced it:

| defect | mechanism | fix |
|---|---|---|
| read as a zoom, not parallax | z travel was **5.5% of a 3.30-deep stack** (measured 2026-08-22) | z travels **62%** of the stack; `check-camera-plan.py` runs as a gate before any frame renders |
| "waves once mechanically" | one 8s gust cycle, held on one isolated tree, is one visible wave | never one tree in frame; a region holds ~12 trees at staggered gust delays. **The swing math is untouched** — Ryan approved the existing version on the ladder |
| "stupid cropped-in shots" | fov followed the subject with no ceiling | fov ceiling **2.2**, and the frame must contain a scene, not a specimen |
| the waterfall is not animated | `w-gorge-fall`, `w-compound-fall`, `w-lower-pool`, `w-midstream` are all **built**; the path never framed them | two of the four region passages are water, verified with pixels before the full render |
| the mountain tops move | ridge pines are welded to the rock — see [[a-tree-welded-to-rock-cannot-be-carded]] | ridge pines are **held**; summit life comes from parallax, water and mist |
| recycled footage | shots were assembled from existing renders | one path, one render pass; there is nothing to recycle from |

## Decisions taken

All four settled with Ryan on 2026-08-25:

1. **Shape** — one unbroken rise. Not composed shots cut together.
2. **Tightest framing** — fov 2.2 ceiling, the same closeness as the tree he
   approved, but the frame always holds a region rather than a single tree.
3. **Length** — a fixed 5:00, picture first, narration later.
4. **Ridge pines** — held. They do not move at all.

## Architecture

One `path.json` in master coordinates spanning y 15923 → 0. Five plane stacks
render the same path over their own y range:

```
z1   y  9596 - 15923   x 0-4613   (70% of width only)
z3w  y  4712 - 12594   x 0-6586
z4w  y  3650 -  9409   x 0-6586
z5w  y  2641 -  7816   x 0-6586
z6w  y     0 -  6807   x 0-6586
```

Where two stacks overlap, both render the band and **cross-dissolve inside it**.
There is never a cut, because at every dissolve both stacks show the same
painting from the same camera. Narrowest overlap is z1→z3w at 2,998 master px =
**66 seconds** at 45 px/s. This is the mechanism that makes "no cuts" real.

**A constraint that shapes the opening.** z1 covers only x 0–4613 of 6586, and
the bottom 3,329 master px exist in no other stack. The film therefore cannot
open wider than **fov 1.44** without running off the right edge into nothing. The
opening is a mid-tight river entry that widens as it rises into z3w's full
width. This is a limit of the cut, not a choice.

## Motion budget

Nothing in the living layer changes. The parameters Ryan approved stand:
`swing 6`, `flutter 0.15`, `gust 0.10,0.08,0.22`, `gust-rest 0.15`, `under:
hold`, `carrier 1`. `s-pine-over-bridge` carries no overrides and every other
foliage region already inherits the identical numbers, which is what Ryan asked
for when he said the approved tree "should be the default for the other branches
and tree leaves."

The single change is **which** regions are allowed to move: welded ridge trees
get `held: true` and are never carded.

## Phases

Each ends in something Ryan looks at.

### 1. Weld pass
Decide per summit region whether its ink is continuous with the rock. Region
names cannot decide this — `s-pine-over-bridge` is a broadleaf. Output is a
`held: true` flag per region in `regions.json`, plus a contact sheet with the
call marked on each crop for Ryan to overrule by pointing.
**Done when:** every summit region has an explicit held/moves flag and Ryan has
seen the sheet.

### 2. Path authored and gated
Author the single `path.json`. `tools/check-camera-plan.py` must pass on: z
travel ≥ 55% of stack depth, fov never above 2.2, every fov peak containing a
region box rather than a single tree box.
**Done when:** the gate exits 0 and the spec plot is regenerated from the real
keys rather than a sketch.

### 3. Handoff proof
Render only the four dissolve bands, ~15s each, and stack them. This is the one
thing that can sink the approach and it gets proven before 7,200 frames are
spent.
**Done when:** Ryan cannot see the handoffs.

### 4. Water verification
Render each of the four water regions at the fov the path actually uses.
**Done when:** each fall visibly moves at its shipping framing, or is diagnosed.

### 5. Full render
~7,200 frames at the measured 0.85 s/frame ≈ 1h42m.
**Done when:** `~/Desktop/WANG-MENG-LATEST.mp4` points at it.

## What this design does not do

- No narration, no audio, no grade. Picture only.
- No new animation technique. Everything renders with tools that exist.
- No summit foliage motion. That is the point, not an omission.
