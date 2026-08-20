#!/usr/bin/env python3
"""Sweep the canopy read over ONE authored box and show every setting's mask.

The summit crests are a thin ribbon of dots on pale rock, not the fat leaf
masses the compound read was tuned on, so the tuned numbers are a hypothesis
up here, not a result. This renders the hypothesis.
"""
import json, sys, itertools
import numpy as np, cv2
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
from pathlib import Path

HERE = Path(__file__).parent; JOB = HERE.parent
zone, rid = sys.argv[1], sys.argv[2]
pj = json.loads((JOB / "journey" / zone / "plate.json").read_text())
X0, Y0 = pj["masterBox"][0], pj["masterBox"][1]
K = pj["masterPxPerRegionPx"]
plate = Image.open(JOB / "journey" / zone / "plate.png").convert("RGB")
PW, PH = plate.size
poly = next(p for p in json.loads((HERE / "living-polys.json").read_text())["polys"]
            if p["id"] == rid)
pts = [((mx - X0) / K, (my - Y0) / K) for mx, my in poly["points"]]
m = Image.new("L", (PW, PH), 0); ImageDraw.Draw(m).polygon(pts, fill=255)
pm = np.array(m)
rgb = np.array(plate)

def read(win, dens_t, comp_t, grow, off, close, tex_t=None):
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
        # A DARK WASH IS NOT A CANOPY. Density asks how much ink; up here the
        # shadowed rock below a crest is plenty of ink and perfectly smooth, so
        # density and compactness both wave it through. Leaf dots are HIGH
        # FREQUENCY and a wash is low frequency, so measure the high-pass
        # energy: v minus a wide blur of v, rectified, averaged in the window.
        hp = np.abs(v - cv2.blur(v, (win * 4 + 1,) * 2))
        tex = cv2.blur(hp, (win, win))
        ok &= tex > tex_t
    mm = ok.astype(np.uint8)
    if close:
        mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close,)*2))
    n, lab, st, cen = cv2.connectedComponentsWithStats(mm, 8)
    keep = np.zeros_like(mm)
    for i in range(1, n):
        if st[i,4] < 900: continue
        cx, cy = int(round(cen[i][0])), int(round(cen[i][1]))
        if 0 <= cy < PH and 0 <= cx < PW and pm[cy, cx] > 128:
            keep[lab == i] = 1
    return keep

ys, xs = np.nonzero(pm)
pad = 60
bx = (max(0,xs.min()-pad), max(0,ys.min()-pad), min(PW,xs.max()+pad), min(PH,ys.max()+pad))
SETTINGS = [
    ("no texture test (today's rule)     win11 d.40 c0.9 grow40 off.08 close7", (11,0.40,0.9,40,0.08,7,None)),
    ("+ texture > 0.012                  win11 d.40 c0.9 grow40 off.08 close7", (11,0.40,0.9,40,0.08,7,0.012)),
    ("+ texture > 0.020                  win11 d.40 c0.9 grow40 off.08 close7", (11,0.40,0.9,40,0.08,7,0.020)),
    ("+ texture > 0.028                  win11 d.35 c1.0 grow40 off.08 close7", (11,0.35,1.0,40,0.08,7,0.028)),
]
tiles = []
base = plate.crop(bx)
for label, args in SETTINGS:
    k = read(*args)
    a_ = np.array(base).copy()
    kk = k[bx[1]:bx[3], bx[0]:bx[2]] > 0
    a_[kk] = (0.4*a_[kk] + 0.6*np.array([40,190,90])).astype(np.uint8)
    tiles.append((f"{label}   {100*k.sum()/(PW*PH):.2f}% of plate", Image.fromarray(a_)))

W = 1480
tw = W // 2 - 6
th = int(base.height * tw / base.width)
sheet = Image.new("RGB", (W, (th+22)*((len(tiles)+2)//2) + 46), (250,248,244))
d = ImageDraw.Draw(sheet)
d.text((6,8), f"{rid} ({zone}) - the painting, then four canopy reads", fill=(20,20,20))
sheet.paste(base.resize((tw,th), Image.LANCZOS), (0, 26))
d.text((6, 26+th+4), "the painting", fill=(60,60,60))
for i,(lab_, im) in enumerate(tiles):
    r, c = (i+1)//2, (i+1)%2
    x, y = c*(tw+12), 26 + r*(th+22)
    sheet.paste(im.resize((tw,th), Image.LANCZOS), (x,y))
    d.text((x+4, y+th+4), lab_, fill=(20,110,50))
out = HERE / f"_probe-canopy-{rid}.png"
sheet.save(out); print(out)
