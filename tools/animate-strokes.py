#!/usr/bin/env python3
"""Animate painted strokes by cycling them, the way a cel animator would.

WHY THIS EXISTS (Ryan, 2026-08-14). Seven diffusion renders and $1.15 went into
making a river move, and the honest summary is that a model was the wrong
instrument: this is a few ink lines on bare silk, and moving a few lines is the
oldest solved problem in animation. Worse, a video model interpolates smoothly at
24fps, and smoothness is exactly what makes drawn water stop reading as drawn.
Traditional ink animation runs on twos or threes -- 8 to 12 drawings a second --
and the step is part of the idiom.

HOW IT WORKS, and it is deliberately not clever:
  1. inside the mask, split the picture into INK (dark, busy) and SILK (the bare
     ground). 留白 is defined by its material here, same as mask-liubai.py.
  2. inpaint the silk behind the ink, giving a clean ground plate.
  3. displace the ink layer with a field that is PERIODIC in time, so the cycle
     loops seamlessly, plus a constant drift along the current direction.
  4. hold each drawing for --on frames, then composite over the ground.

Nothing is invented and nothing is re-drawn: every frame contains exactly Wang
Meng's ink, moved. That is the difference from the model, which redraws the
strokes and quietly changes how many there are.

  ./animate-strokes.py --image P.png --masks DIR [--only NAME] --out O.mp4
    [--frames 72] [--fps 24] [--on 2]        --on 1 = ones, 2 = twos, 3 = threes
    [--drift 6]      px of along-current sway (the long axis of the ellipse)
    [--angle 8]      flow direction, degrees clockwise from +x (screen right)
    [--wobble 2.4]   px of cross-current undulation
    [--scale 90]     size of the cross-current chop in px
    [--wavelength 240] px between wave crests travelling along the current
    [--boil 0.0]     px of per-drawing random jitter — the hand-drawn "boil"
    [--field wave|sway]  wave = water surface · sway = foliage on a branch
    [--pivot X,Y]    sway only: where the branch meets the trunk
    [--stiffness 1.6] sway only: taper exponent toward the tip
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageFilter

p = argparse.ArgumentParser()
p.add_argument('--image', required=True); p.add_argument('--masks', required=True, action='append')
p.add_argument('--only', default=None);   p.add_argument('--out', required=True)
p.add_argument('--out-frames', default=None,
               help='also write the UNIQUE drawings as lossless PNGs here '
                    '(dr-%%03d.png + cycle.json) for compositors that need '
                    'exact pixels; the mp4 stays the preview artifact')
p.add_argument('--frames', type=int, default=72); p.add_argument('--fps', type=float, default=24)
p.add_argument('--on', type=int, default=2)
p.add_argument('--drift', type=float, default=6.0)
p.add_argument('--angle', type=float, default=8.0)
p.add_argument('--wobble', type=float, default=2.4)
p.add_argument('--scale', type=float, default=90.0)
p.add_argument('--wavelength', type=float, default=240.0,
               help='px between wave crests along the current')
p.add_argument('--boil', type=float, default=0.0)
p.add_argument('--max-thick', type=float, default=3.0,
               help='px: keep ink whose distance-to-edge never exceeds this. '
                    'Separates drawn LINES from painted masses like rocks.')
p.add_argument('--field', choices=['wave', 'sway'], default='wave',
               help='wave = water: a crest travels through a flat surface. '
                    'sway = foliage: the mass pivots about --pivot, amplitude '
                    'growing toward the tip.')
p.add_argument('--pivot', default=None, help='sway: X,Y where branch meets trunk')
p.add_argument('--stiffness', type=float, default=1.6,
               help='sway: taper exponent. 1 = a rope, 3 = a stiff limb that only '
                    'the tips of move.')
p.add_argument('--keep', choices=['thin', 'all'], default=None,
               help="which ink to move. 'thin' keeps only strokes (water lines, "
                    "default for wave); 'all' keeps filled shapes too, which is "
                    "what leaf clusters are (default for sway).")
p.add_argument('--mode', choices=['lift', 'warp'], default=None,
               help="how the ink is moved. 'lift' extracts the strokes, inpaints "
                    "the ground behind them and moves them over it -- right for "
                    "water, where the ground is blank silk and the rocks in the "
                    "river must NOT move. 'warp' displaces the region bodily, "
                    "background included -- right for foliage, where the ground "
                    "behind the leaves is textured cliff that cannot be "
                    "reconstructed and does not need to be. Defaults: lift for "
                    "wave, warp for sway.")
p.add_argument('--seed', type=int, default=7)
a = p.parse_args()

img = np.array(Image.open(a.image).convert('RGB')).astype(np.float32)
H, W = img.shape[:2]

region = np.zeros((H, W), np.float32)
names = []
for d in a.masks:
    meta = json.load(open(Path(d) / 'layers.json'))
    for pl in meta['planeList']:
        if a.only and pl['name'] != a.only:
            continue
        mi = np.array(Image.open(Path(d) / 'masks' / f"{pl['n']:03d}.png").convert('L'), np.float32) / 255
        ox, oy = pl['offset']; mh, mw = mi.shape
        region[oy:oy + mh, ox:ox + mw] = np.maximum(region[oy:oy + mh, ox:ox + mw], mi)
        names.append(pl['name'])
R = region > 0.4

# ── 1. what is ink, inside the region ────────────────────────────────────────
v = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2HSV)[..., 2].astype(np.float32) / 255
ground = np.percentile(v[R], 70)
ink = ((v < ground - 0.055) & R).astype(np.uint8)
ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

# A LINE IS THIN. The water mask's feather and close inevitably bleed onto the
# rock masses sitting in the river, and the first version displaced those too --
# it inpainted the rocks away and smeared them (visible immediately, invisible in
# every metric). The discriminator is the thing that defines a brushstroke:
# distance-to-edge. A drawn ripple line is 1-3px from its own edge everywhere; a
# painted rock is a filled mass many px thick. Keep the thin, leave the massive.
keep_rule = a.keep or ('all' if a.field == 'sway' else 'thin')
dist = cv2.distanceTransform(ink, cv2.DIST_L2, 3)
n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
keep = np.zeros_like(ink)
dropped = 0
for i in range(1, n):
    sel = lab == i
    if keep_rule == 'all' or dist[sel].max() <= a.max_thick:
        keep[sel] = 1
    else:
        dropped += 1
ink = keep
solid = (lab > 0) & (ink == 0)            # the masses we are deliberately NOT moving

# ── 2. the silk behind it ────────────────────────────────────────────────────
clean = cv2.inpaint(img.astype(np.uint8), cv2.dilate(ink, np.ones((3, 3), np.uint8)),
                    5, cv2.INPAINT_TELEA).astype(np.float32)
# SOLVE the matte, do not threshold it. The first version set alpha from a
# hand-picked contrast ramp, which under-estimated coverage: at zero displacement
# the composite mixed silk back into every stroke and the lines came out visibly
# fainter than the source. Since the background behind the ink is now known
# (that is what `clean` is), the matte is determined rather than guessed:
#     img = clean*(1-alpha) + C*alpha   =>   alpha = (clean-img)/(clean-C)
# with C the ink's own colour. Round-trip fidelity then holds by construction,
# and the self-test at the bottom of this script checks it every run.
inkpx = ink > 0
C = (np.percentile(img[inkpx], 3, axis=0) if inkpx.any() else np.zeros(3)).astype(np.float32)
den = np.maximum(clean - C, 6.0)
alpha = np.clip(((clean - img) / den).mean(-1), 0, 1) * R
alpha[solid] = 0                                            # rocks stay put
alpha[~cv2.dilate(ink, np.ones((5, 5), np.uint8)).astype(bool)] = 0

mode = a.mode or ('warp' if a.field == 'sway' else 'lift')
# the feathered region, used by warp mode so the displacement dies out at the
# boundary instead of tearing a straight edge across the picture
rf = np.array(Image.fromarray((np.clip(region, 0, 1) * 255).astype(np.uint8))
              .filter(ImageFilter.GaussianBlur(9)), np.float32) / 255
rf = np.minimum(rf, np.clip(region * 1.6, 0, 1))

# ── 3. a displacement field that is periodic in the cycle ────────────────────
rng = np.random.default_rng(a.seed)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
th = np.deg2rad(a.angle)
fx, fy = np.cos(th), np.sin(th)                 # along the current
px, py = -fy, fx                                # across it
along = xx * fx + yy * fy
across = xx * px + yy * py
phase = 2 * np.pi * across / max(a.scale, 1e-3)
phase2 = 2 * np.pi * along / max(a.wavelength, 1e-3)

ndraw = max(1, a.frames // max(a.on, 1))
jit = rng.normal(0, 1, (ndraw, 2)) * a.boil

# A TRAVELLING WAVE, not a slide. The first version added a constant drift that
# ramped from 0 to --drift across the cycle and then snapped back, so the "loop"
# popped every time it wrapped. Worse, sliding ink sideways reads as a decal
# moving, not as water.
# What real water does -- and what an animator draws -- is a wave passing THROUGH
# the surface while the water itself stays put: each point travels a small ellipse
# as the wave goes by. So the displacement is a wave whose phase runs ALONG the
# current: perpendicular amplitude --wobble, along-current amplitude --drift, a
# quarter cycle out of phase. Periodic in t by construction, so the cycle closes.

# SWAY is a different physics and needs a different field. Water carries a wave
# through a flat surface; foliage does not. A branch is a cantilever anchored at
# the trunk: it PIVOTS, the amplitude grows toward the tip, and the gust arrives
# at the base before the tip, so the outer leaves lag. Applying the water field to
# a tree slides the whole canopy sideways like a sticker, which is exactly the
# tell that betrays cheap 2.5D foliage.
#   displacement = perpendicular to the radius from --pivot
#   amplitude    = --wobble * (d/dmax)^--stiffness      cantilever taper
#   phase        = t - d/--wavelength * 2pi             gust travels outward
if a.field == 'sway':
    if not a.pivot:
        sys.exit('--field sway needs --pivot X,Y (where the branch meets the trunk)')
    cxp, cyp = (float(q) for q in a.pivot.split(','))
    rx, ry = xx - cxp, yy - cyp
    d = np.sqrt(rx * rx + ry * ry)
    dmax = max(float(d[alpha > 0.02].max()) if (alpha > 0.02).any() else 1.0, 1.0)
    taper = np.clip(d / dmax, 0, 1) ** a.stiffness
    tx, ty = -ry / np.maximum(d, 1e-3), rx / np.maximum(d, 1e-3)   # unit tangent
    lag = 2 * np.pi * d / max(a.wavelength, 1e-3)

drawings = []
for k in range(ndraw):
    t = 2 * np.pi * k / ndraw                   # closes the loop exactly
    if a.field == 'sway':
        # a gust, not a metronome: one dominant swing plus a weaker second
        # harmonic, so the canopy breathes unevenly the way wind actually is
        swing = (np.sin(t - lag) + 0.32 * np.sin(2 * (t - lag) + 1.1)) / 1.32
        amp = a.wobble * taper * swing
        mx = tx * amp + jit[k, 0] * taper
        my = ty * amp + jit[k, 1] * taper
        # a little radial breathing so leaves nod as well as swing
        mx += (rx / np.maximum(d, 1e-3)) * a.drift * taper * np.cos(t - lag)
        my += (ry / np.maximum(d, 1e-3)) * a.drift * taper * np.cos(t - lag)
    else:
        ph = phase2 - t                         # wave crest moves along the flow
        w_perp = a.wobble * np.sin(ph) + 0.35 * a.wobble * np.sin(2.3 * phase + 1.7 * t)
        w_along = a.drift * np.cos(ph)
        mx = fx * w_along + px * w_perp + jit[k, 0]
        my = fy * w_along + py * w_perp + jit[k, 1]
    mapx = (xx - mx).astype(np.float32); mapy = (yy - my).astype(np.float32)
    wa = cv2.remap(alpha, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    wa = wa * R                                  # ink never leaves the water
    if mode == 'warp':
        wi = cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        drawings.append(np.clip(img * (1 - rf[..., None]) + wi * rf[..., None], 0, 255))
    else:
        drawings.append(np.clip(clean * (1 - wa[..., None]) + C * wa[..., None], 0, 255))

# SELF-TEST, and it must test the right thing per mode. A first attempt checked
# drawings[0] against the source and reported a large error -- but drawing 0 is
# not undisplaced: at t=0 the field is already mid-swing. That was the test being
# wrong, not the render.
#   lift: the meaningful check is the MATTE. Composite the extracted strokes back
#         with zero displacement; it must reproduce the source, or the strokes are
#         being lifted at the wrong density and every line changes weight.
#   warp: nothing is extracted, so the matte check is vacuous. The real risk is
#         LEAKAGE -- displacement bleeding past the feathered region and dragging
#         the rest of the painting. So measure the error OUTSIDE the region, which
#         must be zero, and report the largest displacement actually applied.
if mode == 'lift':
    zero = np.clip(clean * (1 - alpha[..., None]) + C * alpha[..., None], 0, 255)
    err = np.abs(zero - img).mean(-1)
    rt_mean, rt_p99 = float(err[R].mean()), float(np.percentile(err[R], 99))
    rt_what = 'matte round-trip inside the mask, zero displacement'
else:
    outside = rf < 0.002
    errs = [np.abs(d - img).mean(-1)[outside].max() for d in drawings]
    rt_mean = float(np.mean(errs)); rt_p99 = float(np.max(errs))
    rt_what = 'leakage outside the feathered region, worst frame'
peak_disp = float(np.sqrt(mx * mx + my * my)[R].max())

if a.out_frames:
    fd = Path(a.out_frames)
    fd.mkdir(parents=True, exist_ok=True)
    for di, d in enumerate(drawings):
        Image.fromarray(d.astype(np.uint8)).save(fd / f"dr-{di:03d}.png")
    (fd / 'cycle.json').write_text(json.dumps(
        {'drawings': ndraw, 'on': a.on, 'fps': a.fps, 'image': a.image,
         'masks': names, 'field': a.field}))

import subprocess
enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                        '-s', f'{W}x{H}', '-r', str(a.fps), '-i', '-', '-vf', 'crop=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264',
                        '-crf', '15', '-pix_fmt', 'yuv420p', a.out], stdin=subprocess.PIPE)
for i in range(a.frames):
    enc.stdin.write(drawings[(i // a.on) % ndraw].astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()

print(json.dumps({'out': a.out, 'masks': names, 'frames': a.frames,
                  'uniqueDrawings': ndraw, 'on': a.on,
                  'effectiveDrawingsPerSecond': round(a.fps / a.on, 1),
                  'inkPctOfRegion': round(float(ink[R].mean()) * 100, 2),
                  'field': a.field, 'mode': mode, 'keepRule': keep_rule, 'massesLeftAlone': dropped,
                  'inkColour': [round(float(x)) for x in C],
                  'roundTripMeanErr': round(rt_mean, 2),
                  'roundTripP99Err': round(rt_p99, 2),
                  'roundTripMeasures': rt_what,
                  'peakDisplacementPx': round(peak_disp, 2),
                  'loops': True}, indent=2))
