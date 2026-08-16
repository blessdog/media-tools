#!/usr/bin/env python3
"""media-tools — crop-region: cut a working region out of a big image, keeping the
transform. One job.

It cuts one region and records where it came from. It does not tile (crop-tiles),
find where a crop came from (locate-crop), or render anything.

WHY THIS INSTEAD OF A PLAIN CROP. Animation is built in a shot's coordinates:
masks, clean plates, clicked points. Then the camera needs to move and the shot
is suddenly too small. Re-cropping wider with a naive crop silently invalidates
every mask you own, because the origin moved and nothing recorded by how much.

So this extends an EXISTING crop rather than replacing it: --left/--right/--up
/--down are in the shot's own pixels, at the shot's own scale, and the sidecar
records `shotOffset` — the number to add to any mask cut against the original
shot to place it on the new region. Feed that straight to clean-plate and
walk-figure as --mask-offset.

The transform comes from crop.json (locate-crop), never from a constant in this
file. One fact, one place.

usage:
  crop-region.py --master BIG.png --crop crop.json --out REGION.png
                 [--left N] [--right N] [--up N] [--down N]

  --master PATH  the full-resolution source
  --crop PATH    crop.json from locate-crop: the master<->shot transform
  --out PATH     region image; a .json sidecar lands beside it
  --left/--right/--up/--down N   shot px of extra painting on that side

example:
  crop-region.py --master scroll.png --crop jobs/x/crop.json \
      --out jobs/x/strip.png --right 350 --up 100
  # then: clean-plate --mask-offset 0,100 ...   (left,up from the sidecar)
"""
import argparse, json
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

p = argparse.ArgumentParser()
p.add_argument('--master', required=True)
p.add_argument('--crop', required=True, help='crop.json from locate-crop')
p.add_argument('--out', required=True)
for side in ('left', 'right', 'up', 'down'):
    p.add_argument(f'--{side}', type=int, default=0, help=f'shot px of painting to add {side}')
a = p.parse_args()

meta = json.load(open(a.crop))
C = meta['crop']
k = C['masterPxPerShotPx']
SW, SH = meta['shotSize']

mx0 = C['x'] - a.left * k
my0 = C['y'] - a.up * k
mx1 = C['x'] + C['w'] + a.right * k
my1 = C['y'] + C['h'] + a.down * k

M = Image.open(a.master).convert('RGB')
MW, MH = M.size
if mx0 < 0 or my0 < 0 or mx1 > MW or my1 > MH:
    raise SystemExit(f'region runs off the master: wanted {[round(q) for q in (mx0,my0,mx1,my1)]}, '
                     f'master is {MW}x{MH}. Reduce the side that overruns.')

w = int(round((mx1 - mx0) / k))
h = int(round((my1 - my0) / k))
M.crop((int(mx0), int(my0), int(round(mx1)), int(round(my1)))).resize((w, h), Image.LANCZOS).save(a.out)

side = {'tool': 'crop-region', 'out': a.out, 'size': [w, h],
        'master': a.master, 'masterBox': [int(mx0), int(my0), int(round(mx1)), int(round(my1))],
        'masterPxPerRegionPx': k,
        'shotOffset': [a.left, a.up],
        'shotWindowInRegion': [a.left, a.up, a.left + SW, a.up + SH],
        'note': 'add shotOffset to any mask cut against the original shot; pass it to '
                'clean-plate / walk-figure as --mask-offset'}
json.dump(side, open(a.out.rsplit('.', 1)[0] + '.json', 'w'), indent=2)
print(json.dumps(side, indent=2))
