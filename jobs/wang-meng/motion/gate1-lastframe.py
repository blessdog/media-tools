#!/usr/bin/env python3
"""GATE 1 evidence — the last frame of each clip against the source still.

Motion hides drift; a still does not. This pulls frame 0 and the final frame
out of both clips and lays them beside the source so brushwork can be read
directly, and reports one comparative number.

THE NUMBER, and what it is NOT. The camera moves, so a pixel diff against the
source is meaningless — different content is legitimately in shot. What is
comparable is how far each clip drifts from ITS OWN first frame in tone
distribution (Wasserstein distance over the greyscale histogram). Hunyuan is
the control: it is the renderer already accepted on this painting, so its
drift is the yardstick for "acceptable", not zero.

usage: python3 gate1-lastframe.py
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
CLIPS = [("HUNYUAN 1.5 (control)", "push-real-fix1.mp4"),
         ("WAN 2.2 A14B (gate 1)", "GATE1-wan-ink.mp4")]


def grab(clip: Path, where: str) -> np.ndarray:
    """where: 'first' or 'last'."""
    out = Path(f"/tmp/g1-{clip.stem}-{where}.png")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if where == "last":
        cmd += ["-sseof", "-0.2", "-i", str(clip), "-update", "1", "-frames:v", "1"]
    else:
        cmd += ["-i", str(clip), "-frames:v", "1"]
    subprocess.run(cmd + [str(out)], check=True)
    return np.asarray(Image.open(out).convert("RGB"))


def wass(a: np.ndarray, b: np.ndarray) -> float:
    """Wasserstein-1 between two greyscale histograms, in tone levels."""
    ga = np.dot(a[..., :3], [.299, .587, .114]).astype(np.uint8)
    gb = np.dot(b[..., :3], [.299, .587, .114]).astype(np.uint8)
    ha = np.bincount(ga.ravel(), minlength=256).astype(float)
    hb = np.bincount(gb.ravel(), minlength=256).astype(float)
    ha /= ha.sum(); hb /= hb.sum()
    return float(np.abs(np.cumsum(ha) - np.cumsum(hb)).sum())


def main() -> int:
    src = np.asarray(Image.open(HERE / "shot-real.png").convert("RGB"))
    panels: list[tuple[str, np.ndarray]] = [("SOURCE STILL", src)]
    print(f"{'clip':26} {'tone drift (levels)':>20}   frame0→last")
    for label, name in CLIPS:
        p = HERE / name
        if not p.exists():
            print(f"missing {p}", file=sys.stderr)
            return 1
        f0, fl = grab(p, "first"), grab(p, "last")
        panels.append((f"{label} — LAST FRAME", fl))
        print(f"{label:26} {wass(f0, fl):>20.2f}")

    h = min(p.shape[0] for _, p in panels)
    tiles = []
    for _, arr in panels:
        im = Image.fromarray(arr)
        im = im.resize((int(im.width * h / im.height), h), Image.Resampling.LANCZOS)
        tiles.append(np.asarray(im))
    sheet = np.concatenate(tiles, axis=1)
    out = HERE / "GATE1-LASTFRAME.png"
    Image.fromarray(sheet).save(out)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
