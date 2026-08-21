#!/usr/bin/env python3
"""Stitch each tree's pivots.png into one labelled sheet.

usage: pivot-sheet.py --work journey/z3w/living-work --out evidence.png [--cols 3] [--width 900]
green dot = card hinged where it meets branch ink; red = no branch within reach, foot fallback.
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument('--work', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--cols', type=int, default=3)
ap.add_argument('--width', type=int, default=900)
a = ap.parse_args()

tiles = []
for wd in sorted(Path(a.work).glob('s-*')):
    pv = wd / 'pivots.png'
    cj = wd / 'drawings' / 'cycle.json'
    if not pv.exists():
        continue
    c = json.loads(cj.read_text()) if cj.exists() else {}
    im = Image.open(pv).convert('RGB')
    s = a.width / im.width
    im = im.resize((a.width, int(im.height * s)), Image.LANCZOS)
    label = (f"{wd.name}   r={c.get('branchRadius','?')} ({c.get('branchRadiusMode','')})   "
             f"hinged at branch {c.get('cardsAttached','?')} / foot {c.get('cardsFoot','?')}")
    tiles.append((im, label))

try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 26)
except OSError:
    font = ImageFont.load_default()
H = 44
cols = a.cols
# sort short tiles together so a tall one does not stretch every row
tiles.sort(key=lambda t: t[0].height)
rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
row_h = [max(im.height for im, _ in r) + H for r in rows]
sheet = Image.new('RGB', (cols * a.width, sum(row_h)), (24, 24, 24))
d = ImageDraw.Draw(sheet)
y = 0
for r, rh in zip(rows, row_h):
    for j, (im, label) in enumerate(r):
        x = j * a.width
        d.text((x + 12, y + 9), label, fill=(235, 235, 235), font=font)
        sheet.paste(im, (x, y + H))
    y += rh
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
sheet.save(a.out)
print(a.out, sheet.size, len(tiles), 'trees')
