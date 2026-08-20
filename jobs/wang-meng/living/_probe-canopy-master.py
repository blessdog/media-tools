#!/usr/bin/env python3
"""Same canopy read, run at MASTER resolution instead of the zone plate's.

The z6w plate is the master downsampled 2.34x. Down there the compound
canopies are still hundreds of px across, but a summit tree ribbon is ~50
master px tall, i.e. ~20 plate px -- about the size of the density window
itself, so the read cannot resolve it and returns the whole ridge shoulder.
Analysis resolution has to match feature size; this shows whether that is in
fact the whole story.
"""
import json, sys
import numpy as np, cv2
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
from pathlib import Path

HERE = Path(__file__).parent; JOB = HERE.parent
ROOT = JOB.parents[1]
rid = sys.argv[1]
R = json.loads((HERE / "regions.json").read_text())
poly = next(p for p in json.loads((HERE / "living-polys.json").read_text())["polys"]
            if p["id"] == rid)
master = Image.open(ROOT / R["master"]).convert("RGB")

xs = [x for x, _ in poly["points"]]; ys = [y for _, y in poly["points"]]
GROW = 120
bx = (max(0, min(xs) - GROW - 60), max(0, min(ys) - GROW - 60),
      min(master.width, max(xs) + GROW + 60), min(master.height, max(ys) + GROW + 60))
crop = master.crop(bx)
rgb = np.array(crop)
pm = Image.new("L", crop.size, 0)
ImageDraw.Draw(pm).polygon([(x - bx[0], y - bx[1]) for x, y in poly["points"]], fill=255)
pm = np.array(pm)

def read(win, dens_t, comp_t, grow, off, close, minpx, tex_t=None):
    g = cv2.dilate(pm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*grow+1,)*2))
    sel = g > 128
    v = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[..., 2].astype(np.float32)/255
    ground = float(np.percentile(v[sel], 75))
    ink = ((v < ground - off) & sel).astype(np.float32)
    d = cv2.blur(ink, (win, win))
    e = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_GRADIENT,
                         np.ones((3,3), np.uint8)).astype(np.float32)
    c = cv2.blur(e, (win, win)) / np.maximum(d, 1e-6)
    ok = (d > dens_t) & (c < comp_t) & sel
    if tex_t is not None:
        # A DARK WASH IS NOT A CANOPY, and compactness cannot say so: a solid
        # wash has the same low boundary-per-ink as a solid leaf mass. What the
        # trees have and the wash does not is LOCAL CONTRAST -- 苔點 dots and
        # needle clusters are discrete dark marks against silk, a wash is a
        # smooth dark field. Measure it as high-pass energy at the scale of the
        # marks.
        hp = np.abs(v - cv2.blur(v, (win * 4 + 1,) * 2))
        ok &= cv2.blur(hp, (win, win)) > tex_t
    mm = ok.astype(np.uint8)
    mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close,)*2))
    n, lab, st, cen = cv2.connectedComponentsWithStats(mm, 8)
    keep = np.zeros_like(mm)
    for i in range(1, n):
        if st[i,4] < minpx: continue
        cx, cy = int(round(cen[i][0])), int(round(cen[i][1]))
        if pm[cy, cx] > 128: keep[lab == i] = 1
    return keep

SETTINGS = [
    ("no contrast test               win31 d.40 c0.9 grow120 off.08 close21", (31,0.40,0.9,120,0.08,21,4000,None)),
    ("+ local contrast > 0.020       win31 d.30 c1.2 grow120 off.06 close21", (31,0.30,1.2,120,0.06,21,4000,0.020)),
    ("+ local contrast > 0.030       win31 d.30 c1.2 grow120 off.06 close21", (31,0.30,1.2,120,0.06,21,4000,0.030)),
    ("+ local contrast > 0.040       win31 d.25 c1.4 grow120 off.06 close15", (31,0.25,1.4,120,0.06,15,3000,0.040)),
]
tiles = []
for label, args in SETTINGS:
    k = read(*args)
    a_ = rgb.copy(); kk = k > 0
    a_[kk] = (0.4*a_[kk] + 0.6*np.array([40,190,90])).astype(np.uint8)
    tiles.append((f"{label}   {100*kk.mean():.1f}% of this crop", Image.fromarray(a_)))

W = 1480; tw = W//2 - 6; th = int(crop.height * tw / crop.width)
sheet = Image.new("RGB", (W, (th+22)*((len(tiles)+2)//2) + 46), (250,248,244))
d = ImageDraw.Draw(sheet)
d.text((6,8), f"{rid} at MASTER resolution ({crop.width}x{crop.height})", fill=(20,20,20))
sheet.paste(crop.resize((tw,th), Image.LANCZOS), (0,26))
d.text((6, 26+th+4), "the painting", fill=(60,60,60))
for i,(lab_, im) in enumerate(tiles):
    r, c = (i+1)//2, (i+1)%2
    x, y = c*(tw+12), 26 + r*(th+22)
    sheet.paste(im.resize((tw,th), Image.LANCZOS), (x,y))
    d.text((x+4, y+th+4), lab_, fill=(20,110,50))
out = HERE / f"_probe-master-{rid}.png"
sheet.save(out); print(out)
