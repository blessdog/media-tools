---
id: rest-is-a-noop
kind: law
conflict-key: what-must-a-transform-guarantee-at-rest
status: live
supersedes:
  - hinge-rest-is-a-noop
verified-on: 2026-08-20
asked-as:
  - the animation looks broken
  - paint is missing from my render
  - the tree lost half its ink
  - how do I test a rig
  - how do I know a fill worked
  - frame zero control
---

**Every transform has a parameter value at which it must do NOTHING, and that
value is the cheapest test you will ever run: one subtraction, no eyes, no
opinion. Build the identity case before the interesting case.**

An inpaint at rest must change 0 px. A hinge at 0 degrees must be bit-exact
with its source. An extend with no margin must return the input.

## This law was already written down, and I re-derived it anyway

`jobs/wang-meng/STATE.md` has carried it since 2026-08-17 as LAW 3:

> **Frame-zero control** on every fill/extend: 0 px changed at rest.

On 2026-08-20 a cut-out rig was tuned through four amplitudes — 3, 6, 10 and
15 degrees — against a compositor that was deleting 54% of the canopy before
anything moved. Rendering it at `--swing 0` took one command and showed 26,293
px changed, max 102 levels. Ryan's word for the output had been "broken", and
the law that would have found it in a minute was nine lines above the section
being edited, in a numbered prose list nothing could query.

**That is the whole argument for the store.** The knowledge did not need to be
DISCOVERED; it needed to be RETRIEVABLE, and prose is not retrievable. See
[[hinge-at-the-attachment]] for the sibling failure in the same rig, and
[[null-before-the-metric]] for the same discipline applied to measurements
rather than transforms.

## Measured

    inpaint / extend at rest      0 px changed          (law since 2026-08-17)
    hinge at swing 0, before      26,293 px, max 102
    hinge at swing 0, after       0 px, max 0, mean 0.0000
