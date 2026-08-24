#!/usr/bin/env python3
"""Union the per-band foliage masters into the ONE mask the builder reads.

    union-masters.py            # every foliage-master-*.png -> foliage-master.png

One job. It does not segment, refine, or cut -- it merges masks that already
exist, so that classes.foliage.leafMask can name a single file.

WHY IT IS A SCRIPT AND NOT A COMMAND SOMEONE RAN ONCE. The catalogue is built in
BANDS -- z3w covers master y 4712-12594, z1lower 12594-15923, summit 0-4712 --
because a person can only label a tile at a time. But a zone plate straddles
band boundaries (z1 spans 9596-15923 and needs two of them), so the builder must
see one mask. The first union was typed at a prompt and left no record, which
means the next band silently would not have been in it: the derived file would
have drifted from its own inputs with nothing to catch it. Same failure as a
hand-written STATE.md.

DISJOINT BANDS, SO OR IS CORRECT. The bands do not overlap in y, so a pixel is
claimed by exactly one of them and a union cannot double-count.
"""
import argparse, glob, os, sys
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bands", default=os.path.join(HERE, "foliage-master-*.png"))
    ap.add_argument("--out", default=os.path.join(HERE, "foliage-master.png"))
    a = ap.parse_args()

    files = sorted(f for f in glob.glob(a.bands)
                   if os.path.abspath(f) != os.path.abspath(a.out))
    if not files:
        sys.exit(f"no band masters matched {a.bands} -- run the sam-*.sh passes first")

    acc, per = None, {}
    for f in files:
        m = np.asarray(Image.open(f).convert("L")) > 127
        if acc is None:
            acc = np.zeros_like(m)
        elif m.shape != acc.shape:
            sys.exit(f"{os.path.basename(f)} is {m.shape}, expected {acc.shape} -- "
                     f"every band master must be full master size, not a crop")
        per[os.path.basename(f)] = int(m.sum())
        acc |= m
    Image.fromarray((acc * 255).astype(np.uint8)).save(a.out)

    w = max(len(k) for k in per)
    for k, v in per.items():
        print(f"  {k:{w}s} {v:>9,d} px")
    print(f"  {'UNION':{w}s} {int(acc.sum()):>9,d} px "
          f"({100.0 * acc.mean():.2f}% of the master) -> {os.path.basename(a.out)}")


if __name__ == "__main__":
    main()
