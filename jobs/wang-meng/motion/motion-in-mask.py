#!/usr/bin/env python3
"""Did the motion land inside the stencil, or somewhere else?

The masking test's actual question. Per-pixel temporal std dev, then split by
region: inside the ENABLE mask (where motion is wanted), inside the PROTECT
masks (the figures, where the model likes to invent motion nobody asked for),
and the rest of the frame.

The number to read is selectivity = mean churn inside enable / mean churn in the
rest. Selectivity near 1 means the prompt steered nothing and the motion is
smeared over the whole picture -- a stencil then only hides the mess. Well above
1 means the region actually responded and compositing is doing real work.

Only valid on LOCKED-CAMERA clips. A camera move puts every pixel in motion and
the ratio collapses to 1 for reasons that have nothing to do with the prompt.

  ./motion-in-mask.py CLIP.mp4 --enable DIR [--protect DIR] [--out HEAT.png]
"""
import subprocess, sys, json
import numpy as np
from PIL import Image, ImageDraw

clip = sys.argv[1]
def opt(f, d=None):
    return sys.argv[sys.argv.index(f) + 1] if f in sys.argv else d
enable_dir, protect_dir, out = opt('--enable'), opt('--protect'), opt('--out')
# Size is probed, not assumed. Hardcoding 720x1280 broke on the 704x640 crop.
_pr = json.loads(subprocess.run(
    ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
     'stream=width,height', '-of', 'json', clip], capture_output=True, text=True).stdout)
W, H = _pr['streams'][0]['width'], _pr['streams'][0]['height']

def load(dirpath):
    m = np.zeros((H, W), np.float32)
    if not dirpath:
        return m
    meta = json.load(open(f'{dirpath}/layers.json'))
    for pl in meta['planeList']:
        mi = np.array(Image.open(f"{dirpath}/masks/{pl['n']:03d}.png").convert('L'), np.float32) / 255
        ox, oy = pl['offset']; mh, mw = mi.shape
        m[oy:oy + mh, ox:ox + mw] = np.maximum(m[oy:oy + mh, ox:ox + mw], mi)
    return m

en, pr = load(enable_dir), load(protect_dir)
E, P = en > 0.5, pr > 0.5
REST = ~E & ~P

raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', clip, '-f', 'rawvideo',
                      '-pix_fmt', 'gray', '-'], capture_output=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
sd = f.std(axis=0)

r = lambda x: round(float(x), 3)
enable_m, protect_m, rest_m = sd[E].mean(), (sd[P].mean() if P.any() else 0.0), sd[REST].mean()
res = {
    'clip': clip, 'frames': int(f.shape[0]),
    'areaPct': {'enable': r(E.mean() * 100), 'protect': r(P.mean() * 100), 'rest': r(REST.mean() * 100)},
    'meanChurn': {'enable': r(enable_m), 'protect': r(protect_m), 'rest': r(rest_m)},
    'selectivity_enable_over_rest': r(enable_m / max(rest_m, 1e-6)),
    'figureHijack_protect_over_rest': r(protect_m / max(rest_m, 1e-6)),
    'read': 'selectivity ~1 = prompt steered nothing; >>1 = the region responded',
}
print(json.dumps(res, indent=2))

if out:
    norm = np.clip(sd / max(float(np.percentile(sd, 99.5)), 1e-6), 0, 1)
    stops = np.array([[0, 0, 0], [60, 8, 60], [170, 30, 40], [240, 130, 20], [255, 255, 210]], np.float32)
    pos = np.linspace(0, 1, len(stops))
    heat = np.stack([np.interp(norm, pos, stops[:, c]) for c in range(3)], -1)
    base = np.repeat(f[0][..., None], 3, -1) * 0.30
    img = np.clip(base * (1 - norm[..., None]) + heat * norm[..., None], 0, 255).astype(np.uint8)
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    for mask, colour in ((E, (0, 220, 255)), (P, (0, 255, 90))):
        if mask.any():
            edge = mask ^ (np.roll(mask, 1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 0) & np.roll(mask, -1, 1))
            ys, xs = np.nonzero(edge)
            for x, y in zip(xs[::3], ys[::3]):
                d.point((int(x), int(y)), fill=colour)
    im.save(out)
