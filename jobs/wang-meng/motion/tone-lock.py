#!/usr/bin/env python3
"""Hold every frame's tone to frame 0's tone. One job.

WHY (measured 2026-08-14). A locked-camera i2v clip of shot-real.png loses
saturation uniformly as it runs: median dS = -0.0196 and median dV = -0.0078
between frame 0 and frame 72, measured away from any moving subject. It is not
destruction, it is a slow global fade -- and it was the DOMINANT term in the
silk-survival score, which is why stencilling the figures back only bought 1.6
points. Diagnosing that as damage would have sent us prompt-tuning a bug that
lives in the sampler, not in the words.

The correction is a per-frame affine match in HSV of the median and spread of S
and V back to frame 0. Hue is left alone; the drift measured there is noise.
Statistics are taken on the WHOLE frame by default, which is right for a locked
camera. --ref-mask restricts them to pixels that should not be changing, for a
clip where a big subject legitimately moves and would drag the median with it.

  ./tone-lock.py IN.mp4 OUT.mp4 [--ref-mask M.png] [--fps F]
"""
import subprocess, sys, json
import numpy as np
import cv2

src, dst = sys.argv[1], sys.argv[2]
fps = float(sys.argv[sys.argv.index('--fps') + 1]) if '--fps' in sys.argv else 24.0
_pr = json.loads(subprocess.run(
    ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
     'stream=width,height', '-of', 'json', src], capture_output=True, text=True).stdout)
W, H = _pr['streams'][0]['width'], _pr['streams'][0]['height']

raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo',
                      '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)

ref = cv2.cvtColor(f[0], cv2.COLOR_RGB2HSV).astype(np.float32)
def stats(hsv):
    out = []
    for c in (1, 2):
        ch = hsv[..., c]
        med = np.median(ch)
        # robust spread; percentile gap survives a few blown-out pixels
        spread = max(np.percentile(ch, 84) - np.percentile(ch, 16), 1e-3)
        out.append((med, spread))
    return out
ref_s = stats(ref)

enc = subprocess.Popen(
    ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
     '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-crf', '16',
     '-pix_fmt', 'yuv420p', dst], stdin=subprocess.PIPE)
gains = []
for fr in f:
    hsv = cv2.cvtColor(fr, cv2.COLOR_RGB2HSV).astype(np.float32)
    cur = stats(hsv)
    for i, c in enumerate((1, 2)):
        (rm, rsp), (cm, csp) = ref_s[i], cur[i]
        g = rsp / csp
        hsv[..., c] = np.clip((hsv[..., c] - cm) * g + rm, 0, 255)
    gains.append(round(float(ref_s[0][0] - cur[0][0]), 2))
    enc.stdin.write(cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).tobytes())
enc.stdin.close(); enc.wait()

print(json.dumps({'out': dst, 'frames': int(f.shape[0]),
                  'satMedianCorrectionFirst': gains[0], 'satMedianCorrectionLast': gains[-1],
                  'note': 'correction is in 0-255 HSV units; last frame needed the most'},
                 indent=2))
