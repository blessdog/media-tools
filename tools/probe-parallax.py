#!/usr/bin/env python3
"""media-tools — probe-parallax: does this depth map actually carry depth? One job.

THIS IS AN INSTRUMENT, NOT A RENDERER. render-parallax is the renderer: it puts
each plane at its own z behind a real pinhole camera. This one forward-splats
pixels far-to-near with a z-buffer specifically so it LEAVES the holes visible
wherever a move uncovers ground the picture never contained. A renderer hides
those behind smearing, which is exactly the thing worth measuring.

WHY IT EXISTS. Three separate parallax claims on this project each looked like
proof and each died to a control: a per-band residual that scored 1.75 on a
STATIC clip; a radial-expansion signature that plain camera translation fakes;
and a residual-after-fitting-scale that a synthetic flat zoom beat. A number
about a rendered move means nothing without the null beside it, so the null is
a flag here rather than something you must remember to build.

  --null   constant depth. Same zoom, same splat, parallax impossible by
           construction. Whatever hole fraction this reports is the floor —
           it is splat lattice, not disocclusion. Subtract it before quoting
           anything. Measured 24.8% at zoom 0.18 against 25.5% for a real map:
           without the null that 25% reads as catastrophic tearing, when the
           real disocclusion is under one point.
           THE NULL MUST EXPAND AS MUCH AS THE MAP IT CONTROLS FOR. A first
           attempt normalised a constant map to all-ZERO instead of mid-grey, so
           it zoomed at a lower rate, produced fewer lattice gaps (11.4%), and
           made the disocclusion look 14 points bigger than it is. A null that
           is not matched on everything except the effect is not a null.
  --flat N quantise the depth to N levels: the FLAT-CARD null, the thing a
           graded map has to beat. Measured: it does not. 25.0% vs 25.5%, and
           indistinguishable on screen, because blurring a plane stack only
           feathers seams (every plane interior stayed 0.0% off its nominal
           depth). A card with a soft edge is still a card.
  --marks  paint the holes magenta instead of filling them, and look.

usage:
  probe-parallax.py --image IN --depth D.png --out O.mp4
      [--zoom 0.18] [--frames 72] [--fps 24] [--marks] [--flat N] [--null]

example:
  probe-parallax.py --image shot.png --depth depth.png --out probe.mp4 --null
  probe-parallax.py --image shot.png --depth depth.png --out probe.mp4 --flat 3
  probe-parallax.py --image shot.png --depth depth.png --out probe.mp4 --marks
"""
import argparse, json, subprocess
import numpy as np
import cv2
from PIL import Image

p = argparse.ArgumentParser()
p.add_argument('--image', required=True); p.add_argument('--depth', required=True)
p.add_argument('--out', required=True)
p.add_argument('--zoom', type=float, default=0.18, help='how far in, as a fraction of frame')
p.add_argument('--frames', type=int, default=72); p.add_argument('--fps', type=float, default=24)
p.add_argument('--marks', action='store_true', help='paint disocclusion holes magenta')
p.add_argument('--flat', type=int, default=0, help='quantise depth to N levels (the card null)')
p.add_argument('--null', action='store_true',
               help='replace the depth map with a constant: the no-parallax floor')
a = p.parse_args()

img = np.asarray(Image.open(a.image).convert('RGB'), np.float32)
dep = np.asarray(Image.open(a.depth)).astype(np.float32)
dep = (dep - dep.min()) / (dep.max() - dep.min() + 1e-9)
H, W = img.shape[:2]
if dep.shape != (H, W):
    dep = cv2.resize(dep, (W, H), interpolation=cv2.INTER_LINEAR)
if a.null:
    dep = np.full_like(dep, 0.5)
elif a.flat > 1:
    dep = np.round(dep * (a.flat - 1)) / (a.flat - 1)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
cx, cy = W / 2, H / 2
enc = subprocess.Popen(
    ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
     '-r', str(a.fps), '-i', '-', '-c:v', 'libx264', '-crf', '15', '-pix_fmt', 'yuv420p', a.out],
    stdin=subprocess.PIPE)

holes = []
for i in range(a.frames):
    u = i / max(a.frames - 1, 1)
    # nearer pixels expand faster: that difference IS the parallax
    s = 1 + a.zoom * u * (0.35 + dep)
    sx = cx + (xx - cx) * s
    sy = cy + (yy - cy) * s
    ix, iy = np.round(sx).astype(np.int32), np.round(sy).astype(np.int32)
    ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
    frame = np.zeros((H, W, 3), np.float32)
    zbuf = np.full((H, W), -1.0, np.float32)
    # painter's order: far first, near overwrites
    order = np.argsort(dep[ok].ravel())
    tx, ty = ix[ok].ravel()[order], iy[ok].ravel()[order]
    tv = img[ok][order]
    td = dep[ok].ravel()[order]
    frame[ty, tx] = tv
    zbuf[ty, tx] = td
    hole = zbuf < 0
    holes.append(float(hole.mean()))
    if a.marks:
        frame[hole] = (255, 0, 200)
    else:  # fill holes from the nearest written pixel so the clip is watchable
        frame = cv2.inpaint(frame.astype(np.uint8), hole.astype(np.uint8), 3, cv2.INPAINT_TELEA).astype(np.float32)
    enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()

print(json.dumps({'out': a.out, 'zoom': a.zoom,
                  'mode': 'null(constant depth)' if a.null else (f'flat {a.flat} levels' if a.flat > 1 else 'as given'),
                  'holeFractionFinal': round(holes[-1], 5),
                  'holeFractionMax': round(max(holes), 5),
                  'note': ('run again with --null and SUBTRACT that figure: most of this is splat '
                           'lattice, not disocclusion. A hole fraction quoted without its null is '
                           'not a measurement.')}, indent=2))
