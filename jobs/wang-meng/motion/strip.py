#!/usr/bin/env python3
"""Frames from one or more clips, side by side, labelled. One job.

Built because the same comparison was hand-rolled three times on 2026-08-14. A
strip is the fastest way to see whether a clip HELD or DRIFTED, and every claim
about a render in this project has to be shown before it is believed.

  ./strip.py OUT.png LABEL=clip.mp4 [LABEL=clip.mp4 ...]
      [--at 0,24,48,72]      frame indices (default first/third/two-thirds/last)
      [--crop X0,Y0,X1,Y1]   zoom one region instead of the whole frame
      [--h 640]              tile height in px
  A LABEL=file.png source is treated as a single still and repeated once.
"""
import subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

out = sys.argv[1]
def opt(f, d=None):
    return sys.argv[sys.argv.index(f) + 1] if f in sys.argv else d
crop = [int(v) for v in opt('--crop').split(',')] if opt('--crop') else None
th = int(opt('--h', '640'))
at = [int(v) for v in opt('--at').split(',')] if opt('--at') else None
pairs = [a.split('=', 1) for a in sys.argv[2:] if '=' in a and not a.startswith('--')]

def frames(path):
    """Size is probed per clip. Hardcoding 720x1280 broke the moment a crop
    arrived at 704x640 (2026-08-14)."""
    if path.lower().endswith('.png'):
        return np.array(Image.open(path).convert('RGB'))[None]
    import json as _j
    pr = _j.loads(subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
         'stream=width,height', '-of', 'json', path], capture_output=True, text=True).stdout)
    w, h = pr['streams'][0]['width'], pr['streams'][0]['height']
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)

tiles = []
for label, path in pairs:
    f = frames(path)
    n = f.shape[0]
    idx = [0] if n == 1 else (at or [0, n // 3, 2 * n // 3, n - 1])
    for i in idx:
        im = f[min(i, n - 1)]
        if crop:
            im = im[crop[1]:crop[3], crop[0]:crop[2]]
        ih, iw = im.shape[:2]
        t = Image.fromarray(im).resize((max(1, int(iw * th / ih)), th), Image.LANCZOS)
        c = Image.new('RGB', (t.width + 12, th + 46), 'white'); c.paste(t, (6, 40))
        cap = label if n == 1 else f'{label}  f{i}'
        ImageDraw.Draw(c).text((10, 14), cap, fill='black')
        tiles.append(np.array(c))

Image.fromarray(np.concatenate(tiles, axis=1)).save(out)
print(out, f'{len(tiles)} tiles')
