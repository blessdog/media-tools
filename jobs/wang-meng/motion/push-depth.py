#!/usr/bin/env python3
"""Push a camera into an image using a depth map, and SHOW what tears.

This is a diagnostic, not the final renderer. It forward-splats pixels far-to-
near with a z-buffer, which resolves occlusion correctly and leaves a HOLE
wherever the move uncovers ground the painting never contained. Those holes are
the whole point: they are the honest cost of a Z-push, and a renderer that
hides them behind smearing is hiding the thing worth measuring.

  ./push-depth.py --image IN --depth D.png --out O.mp4 [--zoom 0.18] [--frames 72]
      [--marks] [--flat N]

--flat N quantises the depth to N levels first: that is the FLAT-CARD null, the
thing the graded map has to beat.
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
a = p.parse_args()

img = np.asarray(Image.open(a.image).convert('RGB'), np.float32)
dep = np.asarray(Image.open(a.depth)).astype(np.float32)
dep = (dep - dep.min()) / (dep.max() - dep.min() + 1e-9)
H, W = img.shape[:2]
if dep.shape != (H, W):
    dep = cv2.resize(dep, (W, H), interpolation=cv2.INTER_LINEAR)
if a.flat:
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

print(json.dumps({'out': a.out, 'zoom': a.zoom, 'flatLevels': a.flat or None,
                  'holeFractionFinal': round(holes[-1], 5),
                  'holeFractionMax': round(max(holes), 5),
                  'note': 'holes are pixels the push uncovered that the painting never had'},
                 indent=2))
