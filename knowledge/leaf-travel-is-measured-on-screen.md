---
id: leaf-travel-is-measured-on-screen
kind: verdict
conflict-key: how-much-should-a-leaf-move
status: live
supersedes: []
scope: >
  Choosing the swing angle for cut-out foliage on 葛稚川移居圖. The GEOMETRY below
  is exact for this plate and framing; the VERDICT on how many screen px read as
  wind is Ryan's and is pending (LADDER-pinebridge.mp4, 2026-08-21).
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/living/LADDER-pinebridge.mp4
  - jobs/wang-meng/living/swing-ladder.sh
asked-as:
  - the leaves barely move
  - how much should a leaf move
  - what swing angle for foliage
  - the foliage is not impressive
---

## A swing angle is not a visible amount until you convert it

Ryan, 2026-08-21, on the first station reel: *"I don't know if you were trying
to animate much of the leaves, but that was not very impressive."* The rig was
running at swing 6 deg and nobody had ever converted that into pixels.

**The conversion, exact for this project.** `render-parallax --width 1920` sets
the view half-width to `960 * K / fov` master px with `K = 2.34` master px per
plate px, so **at fov 1.0 one plate px is one screen px**, and the scale is
linear in fov. A card's tip travels `radius * 2*sin(swing/2)` where radius is
the distance from its pivot to its farthest pixel.

Measured on z3w's seven near trees at swing 6 deg (p90 card radius):

    tree                   p90 radius   tip travel   on screen @fov 1.35 / 1.75
    s-pine-over-bridge         86 px       9.0 px          12.1      15.7
    s-left-clifftop-pine       80          8.4             11.3      14.6
    s-great-trees-upper        64          6.7              9.0      11.7
    s-gorge-big-canopy         59          6.2              8.3      10.8
    s-gorge-foreground         51          5.3              7.2       9.3
    s-left-pines-z2            51          5.4              7.3       9.4
    s-right-rust-tree          31          3.3              4.4       5.7

Roughly half a percent of frame width at the framing the reel used. Doubling
the angle doubles the travel (small-angle), so 12 deg is ~2x and 20 deg ~3.3x.

**The cost side.** Swing was 15 deg until 2026-08-20 and was cut to 6 when the
compositor leak was fixed, because the 15 had been compensating for a rig that
deleted 54% of the canopy. Ink loss at 6 deg is 1.8%. So the ladder must report
loss per angle, not just look nicer.

**The method that generalises:** `living/swing-ladder.sh <hold> <region> <deg...>`
rebuilds one region at several angles, renders the same hold for each, and
stacks them left to right. An amplitude is a thing to SEE at the real framing,
never a number to nudge.
