---
id: subtle-beats-continuous-for-this-painting
kind: verdict
conflict-key: how-broadband-should-foliage-motion-be
status: live
verified-on: 2026-08-24
scope: >
  foliage motion on 葛稚川移居圖 via hinge-foliage.py. About the SPECTRUM of the
  angle signal, not its amplitude -- amplitude is leaf-travel-is-measured-on-screen.
evidence:
  - tools/hinge-foliage.py
asked-as:
  - should foliage motion have turbulence
  - is a broadband wind spectrum better than one sine
  - why is the leaf swing a single sine wave
  - can I add noise to the gust to make it look more natural
---

**One sine per card, plus one third-harmonic flutter term. Not a spectrum.**

A broadband turbulence spectrum was built and REJECTED on 2026-08-24, the same
day it was added. Ryan, on the A/B: *"it looked better before the turbulent
spectrum. I don't want that. I like the subtleness of it."*

Measured at IDENTICAL peak swing, the spectrum multiplied frame-to-frame motion
by 87x and removed every still frame from the loop. That is the mechanism: real
wind is broadband, but a broadband signal has no rest, and this painting reads
as alive precisely because the leaves are mostly still and a gust passes
through. Ryan's standing brief since 2026-08-19 is that foliage is NOT
constantly moving -- little gusts blow through. A spectrum deletes the calm,
and the calm is the effect.

Commits: `5f1dd36` added it, `1490855` reverted it. The rejection is also
recorded in `tools/hinge-foliage.py` at the point of temptation, so the next
person to reach for a noise term reads it before writing one.

What stands instead:

    ang = swing * act * sin(ph) + flutter * act * sin(3*ph + 1.7)

`flutter` is 0.15 deg -- a third harmonic, phase-offset 1.7 rad, enough that a
stand of trees does not move as one object. Variety across the scene comes from
the per-card `seed` and from the gust DELAY (each card's pivot projected onto
the wind direction over `--gust-travel`), not from making any single card's
signal noisy.

Sibling: [[leaf-travel-is-measured-on-screen]] governs HOW FAR a leaf moves.
This claim governs WHAT SHAPE the motion has. They are independent and were
confused once already -- the turbulence build kept peak swing constant and was
still rejected, which is what proves they are separate questions.
