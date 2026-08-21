---
id: leaf-travel-is-measured-on-screen
kind: verdict
conflict-key: how-much-should-a-leaf-move
status: live
supersedes: []
scope: >
  Choosing the swing angle for cut-out foliage on 葛稚川移居圖. The GEOMETRY below
  is exact for this plate. SETTLED 2026-08-21 at swing 6 -- and note that 12 was
  chosen first off a single-tree ladder and then REVERSED once seen in the film.
  A ladder built at one framing does not settle an amplitude for a film that
  changes framing.
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

**The verdict, 2026-08-21 — and its reversal the same afternoon.** Ryan watched
the 6 / 12 / 20 ladder and said *"12"*. Rebuilt into the reel, he watched it and
said: *"Unfortunately, the leaves looked better before."* Swing is 6.

**Why the ladder lied, which is the transferable part.** The ladder was ONE
tight hold on ONE tree. The reel spans **fov 1.0 to 1.6 across seven trees**, and
tip travel in screen px scales with fov — the same 12 deg that read as lively in
a tight hold is nearly double the screen travel in a wide one, on trees whose
card radii differ by 3x. **An amplitude chosen at one framing does not transfer
to a film that changes framing.**

So the ladder is still the right instrument for the QUESTION "what does this
angle look like", and the wrong instrument for "what angle should the film use".
The second question can only be answered in the cut. Build the ladder to
understand the range; set the value in the reel.

But he did not stop there, and the second half matters more: *"Okay, but I see
the entire leaf structure is one green blob. I would like to make the individual
leaves kind of twinkle and shake. move around leaf not entire tree."* **An
amplitude question can be the wrong question.** Three angles of one rigid blob
were three sizes of the same defect, and no value on that ladder was ever going
to be right, because what was missing was a whole scale of motion rather than
more of the one we had. That second scale was then built and REJECTED the same
afternoon, for a reason the amplitude question could not reach either -- see
[[rigid-cards-preserve-the-brushwork]].

**The method that generalises:** `living/swing-ladder.sh <hold> <region> <deg...>`
rebuilds one region at several angles, renders the same hold for each, and
stacks them left to right. An amplitude is a thing to SEE at the real framing,
never a number to nudge.
