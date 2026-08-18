#!/usr/bin/env python3
"""Cut a pan strip out of the master at the existing shot's exact scale.

The shot everything was built on -- shot-real.png, its masks, its clean plate --
is master[901:2585, 10604:13599] resampled by 2.34 master px per shot px, found
by locate-crop.py at 0.9576 correlation and confirmed at 5.0/255 mean abs error.

A pan needs more painting than one frame holds, but it must be the SAME painting
at the SAME scale, or every mask cut against shot-real lands in the wrong place.
So the strip extends the shot's own coordinate system: --left/--right/--up/--down
are in shot pixels, and strip.json records the offset to add to any shot-space
mask to move it into the strip.

  ./make-strip.py --master M.png --out strip.png --right 450 [--left 0] [--up 0] [--down 0]
"""
import argparse, json
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# measured by locate-crop.py, 2026-08-16
CROP = {'x': 901, 'y': 10604, 'w': 1684, 'h': 2995, 'k': 2.34, 'shot': [720, 1280]}

p = argparse.ArgumentParser()
p.add_argument('--master', required=True)
p.add_argument('--out', required=True)
for side in ('left', 'right', 'up', 'down'):
    p.add_argument(f'--{side}', type=int, default=0, help=f'shot px of painting to add {side}')
a = p.parse_args()

k = CROP['k']
SW, SH = CROP['shot']
mx0 = CROP['x'] - a.left * k
my0 = CROP['y'] - a.up * k
mx1 = CROP['x'] + CROP['w'] + a.right * k
my1 = CROP['y'] + CROP['h'] + a.down * k

M = Image.open(a.master).convert('RGB')
MW, MH = M.size
clip = [max(0, mx0), max(0, my0), min(MW, mx1), min(MH, my1)]
if [round(v) for v in clip] != [round(mx0), round(my0), round(mx1), round(my1)]:
    raise SystemExit(f'strip runs off the master: wanted {[mx0,my0,mx1,my1]}, master is {MW}x{MH}')

w = int(round((mx1 - mx0) / k))
h = int(round((my1 - my0) / k))
strip = M.crop((int(mx0), int(my0), int(round(mx1)), int(round(my1)))).resize((w, h), Image.LANCZOS)
strip.save(a.out)

meta = {'out': a.out, 'size': [w, h], 'masterBox': [int(mx0), int(my0), int(round(mx1)), int(round(my1))],
        'masterPxPerStripPx': k,
        'shotOffset': [a.left, a.up],
        'note': 'add shotOffset to any mask offset cut against shot-real.png to place it on this strip',
        'shotWindowInStrip': [a.left, a.up, a.left + SW, a.up + SH]}
json.dump(meta, open(a.out.rsplit('.', 1)[0] + '.json', 'w'), indent=2)
print(json.dumps(meta, indent=2))
