# 2026-08-25 — the density rule was eating the leaves

*Companion to [2026-08-24 — the polygon was the classifier](2026-08-24-the-polygon-was-the-classifier.md).*

## Tried

Ryan, after a night of watching the reel: *"I don't think you've still been able
to animate the foliage. Ah, we'll just give it, you know, another couple more
months."* Then, when asked what the plan even was: *"Do you even have any end
goal? Or do we just infinitely go back and forth?"*

The fair answer was that on ONE number we had. `swing` moved 15 → 6 → 12 → 6
across three days and four verdicts, two of the moves Ryan's own, and landed
exactly where it started.

| date | swing | who moved it | verdict |
|---|---|---|---|
| 08-19 | 15° | me | — |
| 08-20 | 6° | me, after the compositor fix | — |
| 08-21 | 12° | Ryan, on LADDER-pinebridge | "12" |
| 08-21 | 6° | Ryan, on the v4 reel | "the leaves looked better before" |

That is an infinite loop **by construction**: "the leaves don't read" was being
treated as an amplitude problem, amplitude is a taste call, and a taste call has
no stopping condition. I kept bringing a dial to a man describing a hole.

## Happened

Splitting one number into two answered it in about ten minutes.
`measure-foliage-coverage.py` reported *what fraction of painted leaf visibly
changes* — and one figure cannot say WHY it is low. Adding
`leafInkUnderACardPx` beside it:

| | leaf ink | % |
|---|---:|---:|
| painted leaf in z1 | 269,561 | 100% |
| **had a card on it** | **116,204** | **43.1%** |
| visibly moved | 70,537 | 26.2% |

**Of the leaf that had a card, 60.7% moved.** Against a ceiling of 63%.

The ceiling is measured, not assumed — the control was to translate the whole
plate rigidly by one pixel and ask the same rule what changed. It answers 63.1%
(2px → 80.1%, 3px → 84.4%), because ink sliding inside a dense mass looks
identical to itself. So the cards that existed were working essentially
perfectly. **The deficit was entirely that 57% of the leaf had no card on it.**

Two hypotheses died on the way, both cheap, both by control:

- *the metric is blind* — a dense canopy could move rigidly and score low. The
  1px control kills it: 63% for one pixel of travel.
- *the gust envelope eats it* — running with `--gust-rest 1.0`, constant full
  amplitude and no envelope, lifts one region 14.6% → 20.2%. Worth 6 points
  of 40.

## Mechanism

`build-zone-living.py`'s `canopy_mask` decided card territory by local ink
DENSITY and COMPACTNESS. It is a good heuristic and it was written before the
catalogue existed. Nothing retired it when the catalogue landed, so the chain
had **two** answers to WHERE:

    catalogue says WHAT  →  SAM says WHERE  →  ink cut says WHICH
                              ↑
                    canopy_mask, also saying WHERE, and losing

Measured across all five zones: the authored polygons enclose **91.4%** of the
catalogued leaf ink, and `canopy_mask` handed **36.0%** to the cutter. The
polygons were never the problem.

`classes.foliage.canopyRule = "catalogue"` — card territory is the polygon AND
the catalogue's own pixel-exact leaf mask.

**And the first version of that was wrong, in a way only a full sweep caught.**
Validating on the single worst-offending region showed a clean 2.1× win. Running
it across all 42 z1 foliage regions showed four REGRESSIONS, the worst of them
`s-pine-over-bridge` — the pine whose sway Ryan had approved — losing half its
leaf. Cause: several polygons here are drawn SMALLER than the tree they name,
and `canopy_mask` had been quietly compensating by dilating 120px and keeping
components whose centroid lands inside. Dropping that grow dropped the overhang.

The grow came back, with the catalogue doing the deciding. **The catalogue is
what makes a 120px reach safe**: density extending that far past a polygon can
land on rock; an intersection with a pixel-exact leaf mask cannot.

## Verdict — LAW

**A heuristic that predates a better answer does not retire itself.** The store
already said the catalogue decides WHAT and SAM decides WHERE. Neither claim was
wrong, and the pipeline still had a third decider quietly overruling both,
because retiring a technique means deleting its CODE, not just writing a
successor claim. See `knowledge/a-card-that-exists-moves-fine.md`.

Rebuilt across all five zones — masks, cycle, register:

| zone | card was | card now | moves was | moves now |
|---|---:|---:|---:|---:|
| z6w | 40.0% | 80.8% | 16.7% | 52.3% |
| z5w | 35.7% | 94.6% | 15.5% | 63.3% |
| z4w | 38.4% | 95.0% | 18.5% | 67.6% |
| z3w | 37.9% | 97.1% | 21.5% | 76.0% |
| z1 | 43.1% | 97.8% | 26.2% | 76.3% |
| **scroll** | **38.5%** | **93.5%** | **19.4%** | **67.9%** |

![coverage](../../jobs/wang-meng/journey/evidence-cut-not-swing.png)

1.82M px of Wang Meng's leaf ink now move against 520k before. Off-leaf ink
moving rose 17,004 → 30,798 in absolute terms — the honest cost of 2.4× more
card — while purity IMPROVED 96.8% → 98.3%, because a catalogue mask cannot
include a boulder.

Living layer 260 → 510 registered patches. Render cost 0.60 → 0.81 s/frame on
z1, compositing 81 living patches instead of 46. THE-RISE re-rendered at the
slower camera: 6,712 frames, 276.5s against 192.96s, `check-holes` 277 frames,
0 holes, intact.

## What this cost, stated plainly

Three days of tuning a parameter that was never the problem, on a project where
the measurement that settles it is four lines of numpy and had been available
since the day the coverage script was written. The lesson is not "measure more."
It is that **a single summary number cannot be debugged** — it has to be split
along the axis of the possible causes before it can say anything, and splitting
it is cheaper than one round of tuning.
