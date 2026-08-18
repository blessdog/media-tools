#!/usr/bin/env python3
"""Freeze masked regions of a clip back to a still plate. One job.

WHY THIS EXISTS (measured 2026-08-14). On a locked-camera i2v run of
shot-real.png at cfg 3 whose prompt said "nothing moves", 92.3% of the frame
never changed -- and 100% of the churn landed on Ge Hong, the deer and the two
servants. The model redraws faces and animals because faces and animals are its
most heavily trained subject classes; no prompt has to ask for it. So the fix is
not a better prompt, it is a stencil: keep the generated pixels everywhere the
model behaved, and paste the untouched painting back everywhere it did not.

REGISTRATION IS THE WHOLE CONSTRAINT. A static mask only lines up if the camera
is locked. This tool therefore assumes GRAMMAR A: i2v supplies living matter
only, and any camera move is applied afterwards by render-parallax.py, where the
transform is known exactly instead of guessed. Do not point this at a clip whose
prompt asked for a dolly -- the stencil will slide off the figure.

  ./composite-protect.py --clip C.mp4 --plate P.png --masks DIR --out O.mp4
    [--feather N]   extra gaussian blur on the mask edge, px (default 6)
    [--invert]      keep the CLIP inside the masks and the plate outside,
                    i.e. an ENABLE mask instead of a PROTECT mask
    [--only NAME]   use just one named mask from layers.json
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

p = argparse.ArgumentParser()
p.add_argument('--clip', required=True); p.add_argument('--plate', required=True)
p.add_argument('--masks', required=True, action='append',
               help='mask dir; repeat to union several (water from mask-liubai '
                    'plus foliage from segment-points)')
p.add_argument('--out', required=True)
p.add_argument('--feather', type=int, default=6)
p.add_argument('--invert', action='store_true')
p.add_argument('--only', default=None)
p.add_argument('--fps', type=float, default=24.0)
a = p.parse_args()

plate = np.array(Image.open(a.plate).convert('RGB'))
H, W = plate.shape[:2]

names, m = [], np.zeros((H, W), np.float32)
for d in a.masks:
    meta = json.load(open(Path(d) / 'layers.json'))
    for pl in meta['planeList']:
        if a.only and pl['name'] != a.only:
            continue
        # segment-points writes masks/NNN.png; older stacks used NNN-<name>.png
        f = Path(d) / 'masks' / f"{pl['n']:03d}.png"
        if not f.exists():
            cands = sorted((Path(d) / 'masks').glob(f"{pl['n']:03d}*.png"))
            if not cands:
                sys.exit(f'no mask png for {pl["name"]}')
            f = cands[0]
        # each mask png is cropped to its own bbox; layers.json carries the
        # offset. Resizing it to the full frame instead of pasting it (first
        # attempt) put the stencil over 85% of the picture rather than 8%.
        mi = np.array(Image.open(f).convert('L'), np.float32) / 255.0
        ox, oy = pl['offset']; mh, mw = mi.shape
        m[oy:oy + mh, ox:ox + mw] = np.maximum(m[oy:oy + mh, ox:ox + mw], mi)
        names.append(pl['name'])

if a.feather:
    m = np.array(Image.fromarray((m * 255).astype(np.uint8))
                 .filter(ImageFilter.GaussianBlur(a.feather)), np.float32) / 255.0
keep_plate = m if not a.invert else 1.0 - m
kp = keep_plate[..., None]

raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.clip, '-f', 'rawvideo',
                      '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.float32)

# seam check: how far apart are clip and plate right where the stencil edge sits?
edge = (keep_plate > 0.15) & (keep_plate < 0.85)
seam = float(np.abs(frames[-1] - plate).mean(-1)[edge].mean()) if edge.any() else 0.0

enc = subprocess.Popen(
    ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
     '-s', f'{W}x{H}', '-r', str(a.fps), '-i', '-', '-c:v', 'libx264',
     '-crf', '16', '-pix_fmt', 'yuv420p', a.out], stdin=subprocess.PIPE)
for fr in frames:
    out = plate * kp + fr * (1.0 - kp)
    enc.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()

print(json.dumps({
    'out': a.out, 'frames': int(frames.shape[0]), 'masks': names,
    'mode': 'enable(clip inside mask)' if a.invert else 'protect(plate inside mask)',
    'maskCoveragePct': round(float(m.mean()) * 100, 2),
    'seamMeanAbsDiff': round(seam, 2),
    'seamNote': 'mean |clip-plate| on the feather band of the LAST frame; '
                'high = the stencil is hiding a big disagreement and may read as a cutout',
}, indent=2))
