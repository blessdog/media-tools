#!/usr/bin/env python3
"""Find where a shot crop came from in the master scroll. One-off measurement.

Nothing recorded the crop box that made shot-real.png, and the pan needs it: to
slide a window across the painting I have to know which pixels of the master the
existing shot, its masks and its clean plate correspond to.

Multi-scale normalised cross-correlation. The crop may have been taken at any
zoom, so search scale k = (master px per shot px) as well as position. Coarse
pass on a pyramid, then refine at full resolution in the winning neighbourhood.
"""
import argparse, json
import numpy as np, cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

p = argparse.ArgumentParser()
p.add_argument('--master', required=True)
p.add_argument('--shot', required=True)
p.add_argument('--kmin', type=float, default=1.0)
p.add_argument('--kmax', type=float, default=12.0)
p.add_argument('--ksteps', type=int, default=45)
p.add_argument('--coarse', type=float, default=6.0, help='shot downscale for the coarse pass')
a = p.parse_args()

master = cv2.cvtColor(np.array(Image.open(a.master).convert('RGB')), cv2.COLOR_RGB2GRAY)
shot = cv2.cvtColor(np.array(Image.open(a.shot).convert('RGB')), cv2.COLOR_RGB2GRAY)
MH, MW = master.shape
SH, SW = shot.shape

# coarse template: the shot at a fixed small size; the master is then resized so
# that one template pixel equals one master pixel at the trial scale k
tw = max(24, int(SW / a.coarse))
th = max(24, int(SH * tw / SW))
tmpl = cv2.resize(shot, (tw, th), interpolation=cv2.INTER_AREA)

best = None
for k in np.linspace(a.kmin, a.kmax, a.ksteps):
    mw = int(MW * tw / (SW * k))
    mh = int(MH * th / (SH * k))
    if mw < tw or mh < th:
        continue
    m = cv2.resize(master, (mw, mh), interpolation=cv2.INTER_AREA)
    r = cv2.matchTemplate(m, tmpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    if best is None or mx > best['score']:
        best = {'score': float(mx), 'k': float(k),
                'x': loc[0] * MW / mw, 'y': loc[1] * MH / mh}
print(json.dumps({'coarse': best}, indent=2))

# refine: full-resolution match inside a window around the coarse hit
k = best['k']
cw, ch = int(SW * k), int(SH * k)
pad = int(max(cw, ch) * 0.25)
x0 = int(max(0, best['x'] - pad)); y0 = int(max(0, best['y'] - pad))
x1 = int(min(MW, best['x'] + cw + pad)); y1 = int(min(MH, best['y'] + ch + pad))
region = master[y0:y1, x0:x1]

fine = None
for kk in np.linspace(k * 0.9, k * 1.1, 21):
    t = cv2.resize(shot, (int(SW * kk / 2), int(SH * kk / 2)), interpolation=cv2.INTER_AREA)
    m = cv2.resize(region, (region.shape[1] // 2, region.shape[0] // 2), interpolation=cv2.INTER_AREA)
    if m.shape[0] < t.shape[0] or m.shape[1] < t.shape[1]:
        continue
    r = cv2.matchTemplate(m, t, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    if fine is None or mx > fine['score']:
        fine = {'score': float(mx), 'k': float(kk),
                'x': x0 + loc[0] * 2, 'y': y0 + loc[1] * 2}

out = {'master': a.master, 'shot': a.shot, 'shotSize': [SW, SH],
       'masterSize': [MW, MH], 'coarse': best,
       'crop': {'x': int(fine['x']), 'y': int(fine['y']),
                'w': int(SW * fine['k']), 'h': int(SH * fine['k']),
                'masterPxPerShotPx': round(fine['k'], 4),
                'score': round(fine['score'], 4)}}
print(json.dumps(out, indent=2))
