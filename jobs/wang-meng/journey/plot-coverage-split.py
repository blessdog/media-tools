#!/usr/bin/env python3
"""Is the foliage deficit a CUTTING problem or an AMPLITUDE problem?

One job: draw the two-step loss from painted leaf -> leaf under a card ->
leaf that visibly moves, against the measured ceiling, so the answer is
readable instead of arguable.

WHY. Ryan, 2026-08-24: "I don't think you've still been able to animate the
foliage." The swing parameter had been moved four times in three days without
the number improving, because coverage was reported as ONE figure and one figure
cannot say whether the leaf failed to move or was never cut.

THE CEILING IS MEASURED, NOT ASSUMED. Translating the whole z1 plate rigidly by
1px registers 63.1% of its leaf ink as changed under the same >6-level rule --
ink sliding inside a dense mass looks identical to itself. So 63% is the most
any real animation can score, and a bar near it is DONE, not weak.

usage:  plot-coverage-split.py --split evidence-coverage-split.json --out x.png
"""
import argparse, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE, INK, MUTED = "#16191d", "#e8e6e1", "#8b9199"
LEAF, CARDED, MOVES, CEIL = "#2a3b38", "#3f8f84", "#c9a227", "#e0574a"

ap = argparse.ArgumentParser()
ap.add_argument("--split", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()

d = json.load(open(a.split))
rows = d["zones"]
ceil = d["ceilingPct"]
names = [r["zone"] for r in rows][::-1]
carded = [r["cardCoveragePct"] for r in rows][::-1]
moves = [r["foliageCoveragePct"] for r in rows][::-1]

fig, ax = plt.subplots(figsize=(10.5, 5.4))
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.barh(names, [100] * len(names), color=LEAF, height=0.66, label="painted leaf in the zone")
ax.barh(names, carded, color=CARDED, height=0.66, label="has a card over it")
ax.barh(names, moves, color=MOVES, height=0.42, label="visibly moves")
prev = {"z6w": 16.7, "z5w": 15.5, "z4w": 18.5, "z3w": 21.5, "z1": 26.2}
for i, nm in enumerate(names):
    if nm in prev:
        ax.plot([prev[nm]], [i], marker="|", ms=22, mew=2.5, color="#e8e6e1", zorder=5)
# THE CONTROL IS A LADDER, NOT ONE LINE. A rigid translation of the whole plate
# scores 63.1% at 1px, 80.1% at 2px, 84.4% at 3px under the same >6-level rule,
# because ink sliding inside a dense mass looks identical to itself. So a bar
# between the rungs is not "past the ceiling" -- it reads off how far the leaves
# actually travel.
for px, pct in ((1, 63.1), (2, 80.1), (3, 84.4)):
    ax.axvline(pct, color=CEIL, lw=1.4, ls=(0, (5, 3)), alpha=0.85 if px == 1 else 0.45)
    ax.text(pct, len(names) - 0.38, f" {px}px", color=CEIL, fontsize=8.5, va="top")
ax.text(63.1, -0.95, "rigid-shift control: a whole-plate translation of this many px\nscores this much under the same rule",
        color=CEIL, fontsize=8.5, va="top", ha="center")

for i, (c, m) in enumerate(zip(carded, moves)):
    ax.text(c + 1.0, i + 0.20, f"{c:.0f}% cut", color=CARDED, fontsize=9, va="center")
    ax.text(m + 1.0, i - 0.16, f"{m:.0f}% moves", color=MOVES, fontsize=9, va="center")

s = d["scroll"]
ax.set_title(
    "the leaves were never under-swung — they were un-cut\n"
    f"whole scroll: {100*s['leafInkUnderACardPx']/s['leafInkPx']:.0f}% of the painted leaf has a card on it, "
    f"and {100*s['leafInkThatMovesPx']/s['leafInkUnderACardPx']:.0f}% of THAT moves",
    color=INK, fontsize=13, loc="left", pad=14)
ax.set_xlabel("% of the zone's painted leaf ink", color=MUTED, fontsize=10)
ax.set_xlim(0, 108)
ax.tick_params(colors=MUTED, labelsize=10)
for sp in ("top", "right", "bottom"): ax.spines[sp].set_visible(False)
ax.spines["left"].set_color("#2b3037")
ax.grid(axis="x", color="#2b3037", lw=0.6); ax.set_axisbelow(True)
lg = ax.legend(loc="lower right", frameon=False, fontsize=9)
for t in lg.get_texts(): t.set_color(MUTED)
fig.tight_layout(); fig.savefig(a.out, dpi=150, facecolor=SURFACE)
print(a.out)
