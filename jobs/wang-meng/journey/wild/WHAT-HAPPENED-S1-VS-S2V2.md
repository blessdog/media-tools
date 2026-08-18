# What happened: S1 held, S2-v2 failed — the autopsy

*2026-08-18 · wang-meng · written at Ryan's request after the "i hate it" verdict*

## The question

S1 and S2-v2 were supposed to be the same experiment on different patches of
the painting: real scroll pixels in, one Voyager flight out. S1 gave us
something real. S2-v2 desecrated the family. Same recipe — so what actually
differed?

## What was identical (the controls)

Model, checkpoint, seed (0), steps (50), fp16, negative prompt, B_realistic
style block, generation-1 anchoring (real painting pixels through MoGe →
point cloud → conditions). None of these can explain the split.

## What differed — three factors, ranked

### 1. S2's crop contains people. S1's contains none.

S1's rectangle: rocks, water, grasses. S2's rectangle: Ge's family — six
figures, the mother and child on the ox, faces 30–50 pixels tall.

Voyager does not copy pixels; it re-synthesizes every frame through its
latent space (the crop is also downscaled ~2× internally, so a 40px face is
~20px in the generation raster). That re-synthesis preserves *statistics*,
not *identity*. Rock texture is statistically exchangeable — redraw every
stroke of 皴 and it still reads as the same rock. A face is the opposite: a
few dozen wrong pixels make a different person. **The repaint tax is uniform
per pixel; the damage is not.** S1 spent the tax on texture, where it is
invisible. S2 spent it on faces, where it is everything.

### 2. My configuration error: the prompt ordered up a bridge that isn't there.

The v2 queue reused the journey prompts written for the *chained* design,
where each prompt described the segment's DESTINATION. So S2-v2 rendered
under: *"the camera moves forward and to the left, turning to face **a stone
bridge crossing the stream**."*

There is no bridge in that crop. The prompt was a mandate to invent a
landmark — and Law 6 (naming a thing summons the training data's version of
it) did the rest: asked for architecture, Voyager reached into its prior and
produced its favorite — red-lacquered Chinese gate, the same red-architecture
emission as the chained run's pagoda. The red gate is not the model
freelancing; it is the model doing what my prompt told it to do, with its own
vocabulary. S1's prompt also named an absent thing ("travelers with an ox
ahead"), but S1's other conditions (below) kept the invention small and
peripheral.

### 3. S2's camera move opens a bigger invention zone, exactly where the gate landed.

S1: slow forward push (magnitude 0.5), slight gaze drift — small dis-occluded
slivers at the frame edge. Its inventions (tiny pavilions) landed there, small
and ignorable. S2: forward-left translation with a real gaze swing — the
rotation reveals a large unpainted region on the LEFT of frame. That is
precisely where the red gate materialized. Bigger hole × landmark mandate ×
architecture prior = a prominent fabrication instead of an edge decoration.

## The evidence

| | S1 (held) | S2-v2 (failed) |
|---|---|---|
| anchor | ![s1 anchor](S1/checkpoint/render_0000.png) | ![s2 anchor](S2/input-station.png) |
| end of flight | ![s1 end](S1/B-still-44.png) | ![s2 end](S2/v2-still-44.png) |
| crop contents | rocks, water, grass | six figures, ox, faces |
| prompt named | absent travelers (small edge invention) | absent bridge (prominent gate invention) |
| move | slow push, small reveal | turn, large left reveal |

## The transferable laws

1. **Texture is exchangeable; identity is not.** Re-synthesis models are safe
   on material and fatal on faces, regardless of anchoring. Never point one
   at a figure you care about.
2. **A prompt is a work order for the invention zones.** In anchored shots,
   the prompt must describe what is IN the crop, never a destination or
   landmark beyond it — otherwise you have ordered a fabrication.
3. **Camera rotation is an invention multiplier.** Translation reveals
   slivers; rotation reveals wedges. The bigger the reveal, the more the
   prior speaks.

## Could a fixed S2-v2 pass? Honestly: the tax stays.

Crop-true prompts, no rotation, figure-free framing would shrink factors 2
and 3 to S1 levels — that experiment would probably hold like S1 did. But
factor 1 is not fixable: any shot containing the family redraws the family,
and the family is the heart of this painting. So the fix defines Voyager's
ceiling for this artwork: **empty landscape cameos only** — which the
classical lane already does without a GPU, without a prior, and without
touching a single face. Verdict stands.
