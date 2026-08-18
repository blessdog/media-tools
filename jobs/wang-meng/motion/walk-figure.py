#!/usr/bin/env python3
"""Walk a painted figure across a plate as a cut-out puppet. One job.

WHY THIS IS TRACTABLE AT ALL (2026-08-14). The warning about a walk cycle was
that the far leg and arm do not exist in the painting and would have to be
invented every frame. That warning is wrong for THIS figure: Ge Hong wears a
full-length robe to the ground, so his legs are already hidden. A robed walk in
cel animation is the hem swinging, the body bobbing and the whole figure
travelling -- the legs are never drawn. Nothing has to be invented.

What a walk DOES require, which standing never did, is the background he leaves
behind. Classical diffusion inpainting (TELEA, NS) smears a figure-sized hole
into mush. Patch-based SHIFTMAP synthesis does not, because it copies real silk
from elsewhere in the painting instead of averaging: 3.7s, free, and the texture
survives. So the clean plate needs no model either.

THE GAIT, and every term is a thing an animator would draw:
  travel  the figure crosses the plate
  bob     the body rises and falls twice per stride (weight over each foot)
  lean    a slow forward pitch, largest at mid-stride
  swing   the hem lags the body -- a shear that grows toward the ground, so the
          skirt trails and catches up, alternating with each step

  ./walk-figure.py --plate CLEAN.png --figure SRC.png --masks DIR [--only NAME]
      --out O.mp4 [--travel -200,0] [--strides 4] [--bob 3] [--lean 0.9]
      [--swing 5] [--frames 72] [--on 2]
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageFilter

p = argparse.ArgumentParser()
p.add_argument('--plate', required=True, help='background with the figure already removed')
p.add_argument('--figure', required=True, help='the original image, still containing the figure')
p.add_argument('--masks', required=True, action='append'); p.add_argument('--only', default=None)
p.add_argument('--out', required=True)
p.add_argument('--travel', default='-200,0', help='dx,dy in px over the whole clip')
p.add_argument('--strides', type=float, default=4.0, help='footfalls over the clip')
p.add_argument('--bob', type=float, default=3.0, help='px the body rises and falls')
p.add_argument('--lean', type=float, default=0.9, help='degrees of forward pitch')
p.add_argument('--swing', type=float, default=5.0, help='px the hem lags at the ground')
p.add_argument('--frames', type=int, default=72); p.add_argument('--on', type=int, default=2)
p.add_argument('--fps', type=float, default=24); p.add_argument('--feather', type=int, default=2)
a = p.parse_args()

plate = np.array(Image.open(a.plate).convert('RGB')).astype(np.float32)
src = np.array(Image.open(a.figure).convert('RGB')).astype(np.float32)
H, W = plate.shape[:2]

m = np.zeros((H, W), np.float32)
names = []
for d in a.masks:
    for pl in json.load(open(Path(d) / 'layers.json'))['planeList']:
        if a.only and pl['name'] != a.only:
            continue
        mi = np.array(Image.open(Path(d) / 'masks' / f"{pl['n']:03d}.png").convert('L'), np.float32) / 255
        ox, oy = pl['offset']; mh, mw = mi.shape
        m[oy:oy + mh, ox:ox + mw] = np.maximum(m[oy:oy + mh, ox:ox + mw], mi)
        names.append(pl['name'])
if a.feather:
    m = np.array(Image.fromarray((m * 255).astype(np.uint8))
                 .filter(ImageFilter.GaussianBlur(a.feather)), np.float32) / 255

ys, xs = np.nonzero(m > 0.5)
top, bot = ys.min(), ys.max()
cx = float(xs.mean())
height = max(bot - top, 1)

dx_t, dy_t = (float(q) for q in a.travel.split(','))
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
# how far down the figure a pixel sits, 0 at the head and 1 at the ground: the
# hem shear and the pitch both key off this
depth = np.clip((yy - top) / height, 0, 1)

ndraw = max(1, a.frames // max(a.on, 1))
drawings = []
for k in range(ndraw):
    u = k / ndraw                                  # 0..1 through the clip
    step = 2 * np.pi * a.strides * u
    tx = dx_t * u
    ty = dy_t * u - a.bob * abs(np.sin(step))      # rises over each foot
    pitch = np.deg2rad(a.lean) * np.sin(step * 0.5)
    # hem lags: a horizontal shear growing toward the ground, alternating
    shear = a.swing * np.sin(step - 0.9) * depth ** 1.5
    # pitch about the feet
    px_ = -(yy - bot) * np.sin(pitch)
    mapx = (xx - (tx + shear + px_)).astype(np.float32)
    mapy = (yy - ty).astype(np.float32)
    fig = cv2.remap(src, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    al = cv2.remap(m, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    drawings.append(np.clip(plate * (1 - al[..., None]) + fig * al[..., None], 0, 255))

enc = subprocess.Popen(
    ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
     '-s', f'{W}x{H}', '-r', str(a.fps), '-i', '-',
     '-vf', 'crop=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-crf', '15',
     '-pix_fmt', 'yuv420p', a.out], stdin=subprocess.PIPE)
for i in range(a.frames):
    enc.stdin.write(drawings[(i // a.on) % ndraw].astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()

print(json.dumps({'out': a.out, 'figure': names, 'frames': a.frames,
                  'uniqueDrawings': ndraw, 'on': a.on,
                  'travelPx': [dx_t, dy_t], 'strides': a.strides,
                  'figureHeightPx': int(height),
                  'pxPerStride': round(abs(dx_t) / max(a.strides, 1e-6), 1),
                  'note': 'legs are never drawn: the robe hides them, which is why '
                          'this is displacement and not invention'}, indent=2))
