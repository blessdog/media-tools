#!/usr/bin/env python3
"""GATE evidence — Flux fill vs our classical fill, on identical holes.

HARD COMPOSITE. The model's output is kept ONLY inside the mask; every pixel
outside is copied back from our own render. This is enforced here rather than
requested of the model, which is the whole lesson of the Wan gate: a model asked
to leave things alone eventually will not.

FOUR PANELS, and the third is the one that matters:
    HOLES      the raw defect, what a card stack does at a 0.45 dolly
    CLASSICAL  SHIFTMAP patch synthesis — the control. Beating HOLES proves
               nothing; this is the bar.
    FLUX       the diffusion fill, hard-composited
    MASK       where any of them were allowed to touch

The number reported is how far each fill sits from the classical one INSIDE the
mask only. It is a difference, not a score — it says how much Flux changed, not
whether the change is better. Only Ryan's eyes decide better.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent / "fill"


def load(name: str) -> np.ndarray:
    p = HERE / name
    if not p.exists():
        raise SystemExit(f"missing {p} — run gate-fill.sh then flux-fill.mjs")
    return np.asarray(Image.open(p).convert("RGB")).astype(np.uint8)


def main() -> int:
    holed = load("holed.png")
    classical = load("classical.png")
    raw = load("flux-raw.png")
    mask = np.asarray(Image.open(HERE / "mask.png").convert("L")) > 127

    if raw.shape != holed.shape:
        raw = np.asarray(Image.fromarray(raw).resize(
            (holed.shape[1], holed.shape[0]), Image.Resampling.LANCZOS))

    # The hard composite: model pixels inside the mask, ours everywhere else.
    flux = np.where(mask[..., None], raw, holed)
    Image.fromarray(flux).save(HERE / "flux-composited.png")

    # Sanity check the composite actually held — outside the mask this must be
    # byte-identical to the input, or the guarantee is not a guarantee.
    outside = int(np.abs(flux.astype(int) - holed.astype(int)).sum(2)[~mask].sum())
    print(f"pixels changed OUTSIDE the mask: {outside}   (must be 0)")

    d = np.abs(flux.astype(int) - classical.astype(int)).sum(2)
    print(f"mean |flux - classical| inside mask: {d[mask].mean():6.2f} / 765")
    print(f"mask covers {mask.mean()*100:.2f}% of the frame")

    panels = [("HOLES", holed), ("CLASSICAL (control)", classical),
              ("FLUX 1 FILL", flux),
              ("MASK", np.repeat((mask * 255).astype(np.uint8)[..., None], 3, 2))]
    h = holed.shape[0]
    bar = 46
    sheet = Image.new("RGB", (holed.shape[1] * len(panels), h + bar), (18, 18, 18))
    from PIL import ImageDraw, ImageFont
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 24)
    except OSError:
        f = ImageFont.load_default()
    d2 = ImageDraw.Draw(sheet)
    for i, (label, arr) in enumerate(panels):
        sheet.paste(Image.fromarray(arr), (i * holed.shape[1], bar))
        x0, _, x1, _ = d2.textbbox((0, 0), label, font=f)
        d2.text((i * holed.shape[1] + (holed.shape[1] - (x1 - x0)) / 2, 11),
                label, font=f, fill=(255, 255, 255))
    out = HERE.parent / "FILL-COMPARE.png"
    sheet.save(out)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
