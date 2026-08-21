#!/usr/bin/env python3
"""Draw a labelled catalogue over its tile, so a model's inventory can be CHECKED.

    draw-catalogue.py --tile DIR/t005.jpg --catalogue t005.json --out overlay.png

Boxes are normalised to the tile. Colour is by `kind`, so a rock labelled as a
tree is visible at a glance -- which is the whole point: a labelling pass nobody
looks at is a labelling pass nobody can trust.
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

p = argparse.ArgumentParser()
p.add_argument('--tile', required=True)
p.add_argument('--catalogue', required=True)
p.add_argument('--out', required=True)
a = p.parse_args()

COL = {'tree': (60, 210, 90), 'rock': (235, 70, 60), 'water': (70, 150, 255),
       'figure': (255, 210, 40), 'building': (200, 110, 255), 'void': (150, 150, 150),
       'bridge': (255, 140, 40), 'path': (120, 200, 220)}
im = Image.open(a.tile).convert('RGB')
W, H = im.size
d = ImageDraw.Draw(im, 'RGBA')
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)
except OSError:
    font = ImageFont.load_default()
cat = json.loads(Path(a.catalogue).read_text())
for o in cat['objects']:
    x0, y0, x1, y1 = (o['box'][0]*W, o['box'][1]*H, o['box'][2]*W, o['box'][3]*H)
    c = COL.get(o['kind'], (255, 255, 255))
    d.rectangle([x0, y0, x1, y1], outline=c, width=4)
    d.rectangle([x0, y0, x1, y1], fill=c + (22,))
    lbl = f"{o['kind']}: {o['id']}" + ('' if o['motion'] == 'still' else f"  [{o['motion']}]")
    tb = d.textbbox((0, 0), lbl, font=font)
    d.rectangle([x0, max(0, y0 - (tb[3]+8)), x0 + tb[2] + 12, y0], fill=(0, 0, 0, 210))
    d.text((x0 + 6, max(0, y0 - (tb[3]+6))), lbl, fill=c, font=font)
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
im.save(a.out)
print(json.dumps({'out': a.out, 'objects': len(cat['objects']),
                  'byKind': {k: sum(1 for o in cat['objects'] if o['kind'] == k)
                             for k in sorted({o['kind'] for o in cat['objects']})}}, indent=1))
