---
id: a-card-that-exists-moves-fine
kind: verdict
conflict-key: why-does-the-foliage-not-read-as-moving
status: live
supersedes: [why-only-half-the-leaf-in-a-region-moves]
verified-on: 2026-08-24
scope: >
  葛稚川移居圖 foliage cut by hinge-foliage.py, measured on the z1 plate
  2026-08-24 against catalogue/foliage-master.png.
evidence:
  - jobs/wang-meng/journey/evidence-coverage-split.json
  - jobs/wang-meng/journey/measure-foliage-coverage.py
asked-as:
  - why don't the leaves look like they are moving
  - should I increase the foliage swing
  - is the foliage a cutting problem or an amplitude problem
  - how much of the painted leaf actually animates
---

On z1, of 269,561 px of painted leaf ink:

- **116,204 (43.1%) has a card over it at all**
- 70,537 (26.2%) visibly changes across the cycle
- so **60.7% of the CARDED leaf moves**

**The ceiling is 63%.** Measured by the control: translate the entire z1 plate
rigidly by 1 px and ask the same >6-level rule what fraction of leaf ink
"moved". It answers 63.1% (2px → 80%, 3px → 84%). Ink sliding inside a dense
mass looks identical to itself, so no real motion can score much above that.

**Therefore the cards that exist are working essentially perfectly, and swing
amplitude is not the deficit.** The entire loss is that 57% of the painted leaf
has no card on it — the region masks are drawn tighter than the leaf they name.

This retires the amplitude argument. `swing` was moved four times between
2026-08-19 and 2026-08-21 (15 → 6 → 12 → 6, two of those moves Ryan's own) and
landed back where it started, because it was being tuned against a symptom of an
upstream masking loss. Ryan, 2026-08-24: *"I don't think you've still been able
to animate the foliage."* He was right, and the reason was never the dial.

Two things were ruled out on the way, both by measurement, both cheap:

- **The gust envelope is not the cause.** Re-running
  `cat-broadleaf-great-right` with `--gust-rest 1.0` (constant full amplitude,
  no envelope at all) lifts its move fraction 14.6% → 20.2%. Worth ~6 points,
  not 40.
- **The metric is not blind.** That was the first hypothesis — that a dense
  canopy could move rigidly and still score low. The 1px control kills it: a
  rigid shift of one pixel scores 63%, so a region at 13% really is standing
  still.

The fix is to widen the region masks until `cardCoveragePct` approaches 100,
then `foliageCoveragePct` follows it up to the 63% ceiling. That is a batch job
with a finish line, not a taste call. See [[the-catalogue-decides-what-is-foliage]]
— the catalogue answers WHAT and it is not the failing link; SAM answers WHERE
and it is.

Supersedes the open claim [[why-only-half-the-leaf-in-a-region-moves]], which
asked the right question and had four refuted hypotheses; the answer is that
half the leaf is not *in* the region.
