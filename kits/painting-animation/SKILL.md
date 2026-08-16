---
name: painting-animation
description: Use when animating a still painting — camera moves through it, water and foliage in motion, figures that walk. Covers ink-on-silk scrolls and any picture whose space is drawn by convention rather than photographed. Encodes what has been MEASURED to work and to fail, so those experiments are not repeated.
---

# Painting animation — the golden path

The toolbox in `tools/` is general. This kit is the opinionated route through it
for one class of job: **make a still painting move without a model redrawing the
painting**.

Read this before reaching for a tool. Most of its value is the dead ends: each
one below cost a session and a control to establish, and every one of them looks
plausible right up to the moment you measure it.

## The three layers, and why to keep them apart

| layer | true of | lives in |
|---|---|---|
| universal | any image | `tools/` |
| domain | any painting you want to animate | this kit |
| instance | one painting | `jobs/<name>/painting.json` |

Instance facts leaking into `tools/` is the failure mode to watch. A tool named
for a deer, or a crop transform hardcoded in a depth composer, are the same bug.

## Decision points — measure, do not assume

This kit is a road, not a rail. Painting #2 will differ from painting #1, so
these are the forks and the measurement that resolves each.

**1. Does this painting have photographic space?**
Run `estimate-depth` and check what fraction of the depth variance is explained
by image ROW alone. On a Yuan scroll it was 55%: a vertical ramp with the cliff,
gorge, ledge, river and an entire bridge simply absent. That means the model has
no prior for the layout and its landscape depth is worthless.
- Ramp → landscape depth must be AUTHORED (step 4 below).
- Real structure → you have a station point; camera projection mapping and
  photographic depth pipelines become available, and they are better than planes.

**2. Is the thing you want to move a stroke, a mass, or a figure?**
Three different maskers, and picking wrong wastes a session.
- long and thin, drawn in a pass or two, bare ground either side → `cut-stroke`
- an object with a contour → `segment-points` (a click, not automatic sampling)
- unpainted ground, 留白 → `mask-bare-ground`, which cuts by MATERIAL. An absence
  has no contour, so SAM pointed at a river returns the rocks in the river.

**3. Is the camera moving along the picture, or into it?**
- ALONG (pan, track) → solved. `crop-region` + `walk-figure --window/--pan`.
- INTO (dolly, Z-push) → unsolved for conventional space; see the dead end below.

## The path

Assumes a big scan and a shot cropped out of it.

1. **Register the shot.** `locate-crop --master BIG --shot SHOT --out crop.json`.
   This is the single source of truth for the master↔shot transform; every other
   tool reads it. Check the score (0.95+) and confirm by re-cutting and diffing —
   ~5/255 is resampling, not error.

2. **Cut what moves.** Masks are cut in SHOT coordinates and stay there. Choose
   the masker by decision point 2.

3. **Animate deterministically.** Water and foliage: `animate-strokes` — the
   painter's own ink displaced, never redrawn, and it loops. Figures:
   `clean-plate` then `walk-figure`. A robed figure needs no legs invented
   because the robe hides them; a quadruped needs `cut-stroke` + `--limbs`.

4. **Only if the camera goes INTO the picture:** author landscape depth with
   `plan-planes` → `segment-points` → `compose-depth`, then verify with
   `probe-parallax --null` before believing anything.

5. **Move the camera.** `crop-region` cuts a plate wider than the frame, then
   `walk-figure --window/--start/--pan`. Travel equal to pan is walking in place,
   so the shot is as long as the painting rather than as long as the frame.

## Measured dead ends — do not re-derive

**Diffusion video redraws the painting.** Naming any physical substance in a
motion prompt — water, mist, leaves — is a request for FOOTAGE of it. At cfg 6
the words overpowered the conditioning image and the painting became a
photographic waterfall in ~2 seconds. Describe ONLY the camera, put the
photographic failure modes in the negative, cfg 2–3. And the model spends a fixed
motion budget on whatever it reads as most animate, which is always the face and
the animal: it redraws the protagonist into a different man with no prompt asking.
Never put the medium's own qualities in the negative — "dark outlines" cost 54%
of the ink.

**The living world is deterministic, not generative.** Cel animation beat a
rented A100 on this job: 4.3s vs 10min, CPU vs GPU, selectivity 34.9 vs 9.7,
strokes conserved 26→26 (−0.2% length) vs 40→37 (+9%), and it loops, which the
model cannot. Name the classical technique before proposing a model.

**Monocular depth reads figures, not painted space.** Depth Anything V2 sculpts a
robed figure correctly — relief 0.0698 against a flat-card null of 0, and
corr(depth, ink luminance) −0.064, so it is completing a shape rather than
tracing brushwork. The same model returns a ramp for the landscape. The rule:
**depth where the object has a strong shape prior, convention where there is
none.** It has seen a million standing humans and no Yuan gorges.

**Depth does not cut limbs, and it inverts thin ones.** On a pack animal it found
the barrel and the antlers but never four legs — the far legs are barely painted
— and it placed the near foreleg (0.325) BEHIND the far flank (0.497), because
thin dark strokes on light ground get pushed back. Displacing with that map sends
the legs through the belly. Cut limbs with `cut-stroke`.

**Plan planes at SHOT scale, never at scroll scale.** A stack authored for a whole
scroll has scroll-sized planes and one frame sits inside one or two of them:
3 planes in shot, 69.6% of pixels on a single plane, depth σ 0.098. Re-planned on
the shot: 13 planes, σ 0.394. Always run `plan-planes --review` afterwards — the
first pass left 26.5% unclaimed, concentrated in the mid-ground where the action
was, and the pack animal got no plane at all.

**A Z-push needs `render-parallax --plane-fit`, or it is a zoom. REWRITTEN
2026-08-16 — the previous entry here blamed the wrong thing.** It said a plane
stack "cannot give you a Z-push" and pointed at plane interiors being
piecewise-constant. That was a true observation attached to a false cause. The
actual cause was a single global focal length taken at mid-depth: separating
planes in z changed their PAINTED size, so the composition came apart at frame
zero, so `--z-step` had been throttled to 0.035 to hide it. On wang-meng's
11-plane shot stack that left z spanning 1.000..1.315 and a 0.22 dolly producing
1.201x of common magnification against **6.8% of differential — 96% of the
motion identical for every pixel, which is the definition of a zoom.** No tilt
value fixes that, because tilt adds gradient WITHIN a plane on top of a BETWEEN-
plane budget of nothing.

`--plane-fit` scales every world point by `zr/(zr-camZ)` using its own rest
depth, which is exactly 1.0 at camZ=0 for any depth. So frame zero is the
painting pixel-for-pixel however far apart the planes are — measured: z-step
0.035 → 0.30 (8.6x the depth) changed **zero** pixels at frame zero, where
without the flag it changed 56.4% of them. Depth separation becomes free and
z-step 0.15–0.30 is the useful range. Measured differential near/far scale at
60% of a 0.45 dolly: control 1.000, old settings 1.067, `--plane-fit` 1.183.

Two corrections that follow. **Tilt was never fairly tested** — the rejection
ran at x4 ("deliberately exaggerated… dial back once proven", never dialled
back) on the scroll-scale stack. At 1x with `--plane-fit` tilt is rest-
normalised, so a tilted plane lands on its painted rectangle at rest and only
keystones as the camera moves. And **figures never take a tilt entry**: the
skewing-cutout artefact is a tilted GROUND plane painted after a figure and
riding over it, measured as 6.9% of the figure's window at x4 versus 1.9% at 1x.

Still true: DepthFlow consumes a depth map and does not produce one, and relief
INSIDE a region still has to come from somewhere that is not a plane.

**HY-World stages 2–5 are unusable on a vertical painting.** Its world
representation is a sphere and `split_panorama_image` maps spherical UV over
whatever it is handed with no aspect check, so a vertical image yields silent
smeared garbage rather than an error.

## Two habits that are not optional

**Build the null.** Three separate parallax claims each looked like proof and
each died to a control. A metric with a plausible story attached is not evidence.
And the null must match the thing it controls for on everything except the
effect: a constant-depth null that zoomed at a lower rate than the real map
reported 11.4% instead of 24.8% and made the disocclusion look fourteen points
bigger than it was.

**Render the picture and open it.** Never describe what an image would show. A
mask offset by 100px produced a hole in empty ground, left the real figure
painted in, and composited a ghost over it — and looked completely fine in a
contact sheet. Round-trip against the source when a part is supposed to be
displaced rather than redrawn: frozen-limb vs painting, 2.04/255.

## Output canvas aspect is the 高遠 lever

For generated stills rather than the real painting: the OUTPUT canvas ratio, not
the reference image's shape, decides high-distance vs level-distance composition.
The same square input gives a flat river valley at 1952×960 and towering cliffs
at 960×1952. Also crop generated verticals — they fabricate inscription blocks
and collector seals in gibberish characters, and invented calligraphy must never
appear in a film about a real painting.
