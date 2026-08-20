# How the scroll moves — tools & techniques behind the living Wang Meng

*2026-08-19. The interview-ready explanation of what is actually going on
in BRIDGE-PARALLAX and everything that will follow it. Every number here
was measured in this repo; nothing is estimated.*

## The one-sentence pitch

We take a museum scan of a 650-year-old painting and give it dimension and
life — camera moves with real parallax, water that flows, wind that
gusts — **without ever generating a pixel**. Every frame is Wang Meng's
own ink, resampled. Zero fabrication is the product.

## The stack, layer by layer

### 1. The asset: a 105-megapixel scan, treated as a world

The scroll (葛稚川移居圖, 6586×15923 px) is never shown whole and never
worked whole. It's cut into overlapping **zone worlds** — each a working
"set" around one stretch of the journey — at k=2.34 master px per working
px. Everything below happens per zone.

### 2. Segmentation: human eyes, machine scissors

A human labels **dots** on the painting (this thing is a pine, this is
the bridge, this is water) and **SAM** (Segment Anything, ViT-H) cuts a
mask around each dot. The division of labor matters: the human supplies
*meaning and depth order*, the model supplies *edges*. 13 planes in the
bridge zone, 0% of the frame unclaimed.

One measured exception: **water can't be segmented by any object model**,
because Wang Meng painted water as *absence* — bare silk between drawn
things (留白). SAM, pointed at the river, returns the rocks. So water
masks are cut by a **material rule** instead: bright, low-variance silk =
water ground. The painting's own logic, not a model's.

### 3. Depth: authored, never estimated

The load-bearing decision of the whole project. Monocular depth
estimators were tried and **measurably fail on this painting**: their
"depth" is 49–88% explained by image *row alone* — they read
height-on-the-page, because a Yuan hanging scroll uses 散点透視
(scattered/moving perspective), not Western optics. So depth is
**authored data**: a human assigns each plane its z-order, exactly like a
multiplane camera operator racking glass. The depth map is an asset, not
an inference.

`compose-depth` then folds authored planes + per-figure relief into one
continuous depth field — the painting *with dimensions attached*.

### 4. Layer completion: fill once, behind, forever

Each plane is **completed behind its occluders once** (classical patch
synthesis; a diffusion model only for seam lines — it fills *only* the
seams). This is what makes camera motion possible: when the pine slides
off the cliff, real painted texture is revealed, not a hole and not a
per-frame hallucination. Fill happens once per world, so **flicker is
structurally impossible** (fill flicker-ratio 0.996 vs static).

### 5. The camera: a real pinhole over a card stack

`render-parallax` is the engine. The industry lineage: Disney's
**multiplane camera** (The Old Mill, 1937) → **2.5D camera projection**
(the documentary standard since *The Kid Stays in the Picture*, 2002).
Ours adds two things worth naming:

- **A true pinhole, not sliding cards.** Screen scale per plane is
  `f/(z − camZ)` — one expression gives correct parallax on lateral moves
  AND correct differential zoom on a dolly. Hand-tuned card speeds look
  right for one move and wrong for the next; a projection model is right
  for all of them.
- **Rest-normalized projection** (`--plane-fit`). The classic 2.5D bug:
  separating planes in z changes their painted size, so a push looks like
  a zoom. We scale every plane by `zr/(zr − camZ)` using its *own rest
  depth*, which is exactly 1.0 when the camera is home — so **frame zero
  is the painting, pixel for pixel**, no matter how far apart the planes
  sit. Measured: without it, a dolly was 96% common zoom / 6.8%
  differential; with it, the differential motion (the part that IS
  parallax) is free to be real.
- **Planes have orientation, not just depth.** Per-plane tiltX/tiltY
  makes a ground plane recede and a cliff face turn away — the difference
  between billboards and a set.

The approved dose, from tonight's A/B: dolly z 0→0.24 over 16 seconds.

### 6. Living ink: cel animation, not video generation

The water and foliage move by **displacing Wang Meng's own strokes** —
the oldest solved problem in animation, running on twos (12 drawings/sec)
because the step *is* the drawn idiom. A rented A100 diffusion model was
beaten by 4.3 seconds of CPU arithmetic: the model redrew the strokes
(26 → 37, +9% invented ink); displacement conserves them exactly.

Three physics, because water and trees are different problems:

- **Wave** (water): a crest travels *through* a flat surface; each point
  orbits a small ellipse. Strokes are lifted, the silk behind them
  inpainted, and they move over it — so rocks in the river never move.
  The stroke/rock discriminator is distance-to-edge: a drawn line is thin
  everywhere, a painted mass isn't.
- **Sway** (foliage): a branch is a **cantilever** — it pivots, amplitude
  tapers to the tip, the gust reaches the base first (tip lag).
- **Gust** (new tonight): wind as an **event, not a state** — The Old
  Mill's rule. An attack/hold/decay envelope sweeps downwind across the
  region; between gusts, calm air with a faint idle. The envelope is zero
  at its window edges, so loops still close exactly.

Every cycle self-tests: matte round-trip (the extracted strokes composited
at zero displacement must reproduce the source) or leakage (displacement
must be zero outside the region). And every cycle passes a **what-moves
audit** — a max-deviation heatmap over the loop — before it ships. That
audit is what caught a collector's seal rippling and a porter's basket
weave reading as water lines. Figures and seals are sacred; the audit is
the enforcement.

### 7. The verification culture (the part interviewers remember)

- **Frame-zero control**: at camera home with zero displacement, the
  render must equal the painting. Not approximately — pixel-for-pixel.
- **The null before the number**: every motion claim is measured against
  a static control (silk grain alone costs 11% on drift metrics — quote
  against that, never against 100%).
- **A/B, don't assume**: tonight's subtle-vs-2× dolly was decided by
  rendering both and watching, not by argument.

## Scale laws (all three earned today, the hard way)

1. **Motion params are shot-scale quantities.** The proven water numbers
   are pixels *in the working resolution they were proven at*. Reuse at
   another scale multiplies by k or the current shrinks to a whisper.
2. **Stroke-thickness filters scale too** — at native resolution the same
   filter silently classified water lines as unmovable rock masses.
3. **View scale is part of the recipe.** Cel water carries a frame at
   k≈2.0–2.4 (the multiplane view); at native 1:1 the same water is a
   sliver of a 2-megapixel window. fov ~1.0 is for detail holds only.

## Where this goes next (Ryan's question, answered)

**Camera tilt — yes, and it's cheap.** Today the camera *translates*
(pan x/y, dolly z) with fixed orientation. Adding rotation is a view
homography — a solved transform. The physics worth knowing: **rotation
creates no new parallax** (same center of projection — it's turning your
head, not moving it); **translation is what reveals depth**. The craft
move is combining them: a slight counter-rotation during a lateral drift
is exactly the "floating" feel of high-end 2.5D documentary work.

**"Vectorize the canvas into 3D shapes" — not ahead of yourself; the
asset already exists.** The composed depth field (planes + per-figure
relief) is a continuous heightfield: displace a mesh with it and you have
**proxy geometry with the painting camera-projected onto it** — the VFX
matte-painting workflow (camera mapping). What the mesh buys over cards:
continuous parallax *within* a surface (the cliff face bulges as you
pass). The known cost: rubber-sheet stretching at occlusion edges — the
exact artifact the card stack avoids by completing each layer behind.
The likely destination is the hybrid the literature calls **layered depth
images**: our cards, each carrying its own relief displacement. Cards
where edges matter, relief where surfaces do.

## The vocabulary card

multiplane camera · 2.5D camera projection / camera mapping · layered
depth images (LDI) · pinhole model · rest-normalized projection ·
differential vs common motion (parallax vs zoom) · scattered perspective
(散点透視) · 留白 (deliberate absence) · cel animation on twos · effects
animation · cantilever sway, gust envelope · matte round-trip · null
control · zero-fabrication rendering
