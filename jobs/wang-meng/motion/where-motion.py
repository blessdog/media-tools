#!/usr/bin/env python3
"""Where in the frame did the pixels actually move?

Per-pixel temporal standard deviation across every frame of a clip, rendered as
a heatmap over a dimmed copy of frame 0. Answers "which REGION moved", which is
the question a mask has to answer before a mask is worth building.

Reading the output: black = that pixel never changed. Hot = that pixel churned.
For a locked-camera clip, hot regions are where the model chose to invent motion
on its own. For a camera-move clip everything is hot and the map says nothing --
this tool is only meaningful on locked-camera clips.

  ./where-motion.py CLIP.mp4 OUT.png [--stride N]
"""
import subprocess, sys, json
import numpy as np
from PIL import Image

clip, out = sys.argv[1], sys.argv[2]
stride = int(sys.argv[sys.argv.index('--stride') + 1]) if '--stride' in sys.argv else 1

probe = json.loads(subprocess.run(
    ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
     'stream=width,height', '-of', 'json', clip], capture_output=True, text=True).stdout)
W, H = probe['streams'][0]['width'], probe['streams'][0]['height']

raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', clip, '-f', 'rawvideo',
                      '-pix_fmt', 'gray', '-'], capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W)[::stride].astype(np.float32)
print(f'{clip}: {frames.shape[0]} frames @ {W}x{H}', file=sys.stderr)

sd = frames.std(axis=0)                       # per-pixel temporal std dev, 0..255
peak = float(np.percentile(sd, 99.5))
norm = np.clip(sd / max(peak, 1e-6), 0, 1)

# inferno-ish ramp: black -> deep red -> orange -> white
stops = np.array([[0, 0, 0], [60, 8, 60], [170, 30, 40], [240, 130, 20], [255, 255, 210]], np.float32)
pos = np.linspace(0, 1, len(stops))
heat = np.stack([np.interp(norm, pos, stops[:, c]) for c in range(3)], -1)

plate = np.array(Image.open(clip.replace('.mp4', '.png'))) if False else None
base = np.repeat(frames[0][..., None], 3, -1) * 0.30      # dim frame 0 underneath
img = np.clip(base * (1 - norm[..., None]) + heat * norm[..., None] * 1.0, 0, 255)
Image.fromarray(img.astype(np.uint8)).save(out)

print(json.dumps({
    'clip': clip, 'frames': int(frames.shape[0]),
    'sd_mean': round(float(sd.mean()), 3),
    'sd_p99_5': round(peak, 3),
    'pct_pixels_over_5': round(float((sd > 5).mean()) * 100, 2),
    'pct_pixels_over_15': round(float((sd > 15).mean()) * 100, 2),
}, indent=2))
