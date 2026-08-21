#!/usr/bin/env python3
"""Draw a MASTER-px catalogue over the whole painting, downscaled to look at.

    draw-master-catalogue.py --image scroll.png --catalogue master-z3w.json \
                             --out CHECK-master.png [--max-side 2600] [--crop x0 y0 x1 y1]

draw-catalogue.py checks ONE tile. This checks the composed inventory -- which
is where a different class of error lives: boxes that survived the tile pass but
land in the wrong place after conversion to master px, and seam merges that
swallowed two different objects into one union box.

Colour is by `kind`. Boxes that came from a merge are drawn with a doubled edge,
because a merge is an ASSERTION that two labels named one thing and is the most
likely place for the composition to be wrong.

WHAT THIS IS NOT FOR: judging whether a boundary is exact -- these are boxes,
not masks. refine-mask-sam.py turns a box into an edge.
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
p = argparse.ArgumentParser()
p.add_argument('--image', required=True)
p.add_argument('--catalogue', required=True)
p.add_argument('--out', required=True)
p.add_argument('--max-side', type=int, default=2600)
p.add_argument('--crop', nargs=4, type=int, metavar=('X0', 'Y0', 'X1', 'Y1'))
p.add_argument('--kinds', default='', help='comma-separated kinds to draw (default all)')
a = p.parse_args()

COL = {'tree': (60, 210, 90), 'rock': (235, 70, 60), 'water': (70, 150, 255),
       'figure': (255, 210, 40), 'building': (200, 110, 255), 'void': (150, 150, 150),
       'structure': (255, 140, 40), 'trunk': (170, 110, 50), 'seal': (255, 0, 200),
       'unknown': (255, 255, 255)}
cat = json.loads(Path(a.catalogue).read_text())
im = Image.open(a.image).convert('RGB')
ox, oy = 0, 0
if a.crop:
    ox, oy = a.crop[0], a.crop[1]
    im = im.crop(tuple(a.crop))
sc = min(1.0, a.max_side / max(im.size))
if sc < 1.0:
    im = im.resize((round(im.size[0] * sc), round(im.size[1] * sc)), Image.LANCZOS)
d = ImageDraw.Draw(im, 'RGBA')
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', max(11, int(15 * sc * 4)))
except OSError:
    font = ImageFont.load_default()

want = {k.strip() for k in a.kinds.split(',') if k.strip()}
drawn = 0
for o in cat['objects']:
    k = o.get('kind', 'unknown')
    if want and k not in want:
        continue
    x0, y0, x1, y1 = o['box']
    b = [(x0 - ox) * sc, (y0 - oy) * sc, (x1 - ox) * sc, (y1 - oy) * sc]
    if b[2] < 0 or b[3] < 0 or b[0] > im.size[0] or b[1] > im.size[1]:
        continue
    c = COL.get(k, (255, 255, 255))
    d.rectangle(b, outline=c, width=3)
    if 'mergedFrom' in o:
        d.rectangle([b[0] - 4, b[1] - 4, b[2] + 4, b[3] + 4], outline=c + (150,), width=2)
    lab = f"{k}"
    tb = d.textbbox((0, 0), lab, font=font)
    d.rectangle([b[0], b[1], b[0] + tb[2] + 8, b[1] + tb[3] + 6], fill=c + (210,))
    d.text((b[0] + 4, b[1] + 2), lab, fill=(0, 0, 0), font=font)
    drawn += 1
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
im.save(a.out)
print(json.dumps({'out': a.out, 'drawn': drawn, 'of': len(cat['objects']),
                  'scale': round(sc, 4), 'size': im.size}, indent=1))
