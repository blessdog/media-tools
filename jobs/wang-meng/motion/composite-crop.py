#!/usr/bin/env python3
"""Put an animated CROP back into the full still plate, through a mask. One job.

The other half of composite-protect.py. That one keeps a clip and freezes part
of it; this one takes a clip that only ever covered a sub-rectangle of the
picture, scales it back to that rectangle, and lets it show through a mask over
an otherwise motionless plate.

WHY A CROP AT ALL (measured 2026-08-14). Full-frame at cfg 3, the prompt cannot
aim: naming water moved the water LESS than average (selectivity 0.48) while the
model animated Ge Hong and the deer instead. Full-frame at cfg 6, the prompt
wins and replaces the painting with photographic footage. Crop the conditioning
image down to water only and cfg 6 becomes safe -- a prompt strong enough to
command water cannot dissolve a face that is not in the frame. So the crop is
what confines the motion, and this script is only the way home.

  ./composite-crop.py --clip C.mp4 --plate P.png --box X0,Y0,X1,Y1
      --masks DIR [--only NAME] --out O.mp4 [--feather 8] [--fps 24]
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

p = argparse.ArgumentParser()
p.add_argument('--clip', required=True);  p.add_argument('--plate', required=True)
p.add_argument('--box', required=True);   p.add_argument('--masks', required=True, action='append')
p.add_argument('--only', default=None);   p.add_argument('--out', required=True)
p.add_argument('--feather', type=int, default=8)
p.add_argument('--fps', type=float, default=24.0)
a = p.parse_args()

def read_clip(path):
    pr = json.loads(subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
         'stream=width,height', '-of', 'json', path], capture_output=True, text=True).stdout)
    w, h = pr['streams'][0]['width'], pr['streams'][0]['height']
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)

# --plate takes a still OR a clip. A clip lets these chain: composite the tree
# into the plate, then hand THAT to a second pass for the river, so several
# animated regions land in one picture without a bespoke script per combination.
if a.plate.lower().endswith(('.mp4', '.mov')):
    plates = read_clip(a.plate).astype(np.float32)
    plate = plates[0]
else:
    plates = None
    plate = np.array(Image.open(a.plate).convert('RGB')).astype(np.float32)
H, W = plate.shape[:2]
x0, y0, x1, y1 = (int(v) for v in a.box.split(','))
bw, bh = x1 - x0, y1 - y0

m = np.zeros((H, W), np.float32)
names = []
for d in a.masks:
    meta = json.load(open(Path(d) / 'layers.json'))
    for pl in meta['planeList']:
        if a.only and pl['name'] != a.only:
            continue
        mi = np.array(Image.open(Path(d) / 'masks' / f"{pl['n']:03d}.png").convert('L'), np.float32) / 255
        ox, oy = pl['offset']; mh, mw = mi.shape
        m[oy:oy + mh, ox:ox + mw] = np.maximum(m[oy:oy + mh, ox:ox + mw], mi)
        names.append(pl['name'])
if not names:
    sys.exit('no masks matched')
# the clip only covers the box, so nothing outside it may show through
box_only = np.zeros((H, W), np.float32); box_only[y0:y1, x0:x1] = 1.0
m = m * box_only
if a.feather:
    m = np.array(Image.fromarray((m * 255).astype(np.uint8))
                 .filter(ImageFilter.GaussianBlur(a.feather)), np.float32) / 255
mm = m[..., None]

pr = json.loads(subprocess.run(
    ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
     'stream=width,height', '-of', 'json', a.clip], capture_output=True, text=True).stdout)
cw, ch = pr['streams'][0]['width'], pr['streams'][0]['height']
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.clip, '-f', 'rawvideo',
                      '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, ch, cw, 3)

enc = subprocess.Popen(
    ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
     '-s', f'{W}x{H}', '-r', str(a.fps), '-i', '-', '-c:v', 'libx264', '-crf', '16',
     '-pix_fmt', 'yuv420p', a.out], stdin=subprocess.PIPE)
for i, fr in enumerate(frames):
    base = plates[min(i, len(plates) - 1)] if plates is not None else plate
    full = base.copy()
    full[y0:y1, x0:x1] = np.array(Image.fromarray(fr).resize((bw, bh), Image.LANCZOS), np.float32)
    enc.stdin.write(np.clip(base * (1 - mm) + full * mm, 0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()

print(json.dumps({'out': a.out, 'frames': int(frames.shape[0]), 'masks': names,
                  'clipSize': [cw, ch], 'placedInto': [x0, y0, x1, y1],
                  'maskCoveragePctOfFrame': round(float((m > 0.5).mean()) * 100, 2)}, indent=2))
