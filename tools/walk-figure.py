#!/usr/bin/env python3
"""Walk a painted figure across a plate as a cut-out puppet. One job.

WHY THIS IS TRACTABLE AT ALL (2026-08-14). The warning about a walk cycle was
that the far leg and arm do not exist in the painting and would have to be
invented every frame. That warning is wrong for THIS figure: Ge Hong wears a
full-length robe to the ground, so his legs are already hidden. A robed walk in
cel animation is the hem swinging, the body bobbing and the whole figure
travelling -- the legs are never drawn. Nothing has to be invented.

What a walk DOES require, which standing never did, is the background he leaves
behind: use clean-plate.py, whose patch synthesis keeps the silk texture that
averaging inpainters destroy.

THE GAIT, and every term is a thing an animator would draw:
  travel  the figure crosses the plate
  bob     the body rises and falls twice per stride (weight over each foot)
  lean    a slow forward pitch, largest at mid-stride
  swing   the hem lags the body -- a shear that grows toward the ground, so the
          skirt trails and catches up, alternating with each step

THE CAMERA (2026-08-16). Travel alone runs out of frame in about 70px, which is
under one second of walking. The cel answer is not a longer travel, it is the
pan bar: the background is a strip wider than the frame, and a window slides
across it while the figure walks. Give --window and --pan and the plate may be
any size; --travel is then measured in PLATE space, so travel == pan is walking
in place and the figure never leaves frame no matter how long the shot runs.
The frame is no longer the limit -- the painting is.

Exposure follows the same split a cel setup does: the background pans on ONES,
because a stepped pan strobes, while the drawings hold on TWOS.

  ./walk-figure.py --plate CLEAN.png --figure SRC.png --masks DIR [--only NAME]
      --out O.mp4 [--travel -200,0] [--strides 4] [--bob 3] [--lean 0.9]
      [--swing 5] [--frames 72] [--on 2]
      [--window 720,1280] [--start 0,0] [--pan 450,0] [--ease]
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None

p = argparse.ArgumentParser()
p.add_argument('--plate', required=True, help='background with the figure already removed')
p.add_argument('--figure', required=True, help='the original image, still containing the figure')
p.add_argument('--masks', required=True, action='append'); p.add_argument('--only', default=None)
p.add_argument('--mask-offset', default=None, help='x,y to add to every mask offset, when the masks '
                                                   'were cut against a smaller crop of this image')
p.add_argument('--over', action='append', default=None,
               help='mask dir whose pixels are laid back OVER the figure: the overlay cel, so the '
                    'puppet can pass behind painted foreground')
p.add_argument('--limbs', action='append', default=None,
               help='mask dir whose planes each carry pivot+phase: legs, swung individually. '
                    'Limb pixels are removed from the body, because a limb is not the body')
p.add_argument('--stance', type=float, default=0.6,
               help='fraction of each leg cycle the hoof is planted on the ground')
p.add_argument('--lift', type=float, default=4.0, help='px the hoof rises while it swings forward')
p.add_argument('--limb-swing', type=float, default=0.0,
               help='degrees each limb swings; 0 derives it from stride length and leg length')
p.add_argument('--out', required=True)
p.add_argument('--travel', default='-200,0', help='dx,dy in PLATE px over the whole clip')
p.add_argument('--strides', type=float, default=4.0, help='footfalls over the clip')
p.add_argument('--bob', type=float, default=3.0, help='px the body rises and falls')
p.add_argument('--lean', type=float, default=0.9, help='degrees of forward pitch')
p.add_argument('--swing', type=float, default=5.0, help='px the hem lags at the ground')
p.add_argument('--frames', type=int, default=72); p.add_argument('--on', type=int, default=2)
p.add_argument('--fps', type=float, default=24); p.add_argument('--feather', type=int, default=2)
p.add_argument('--window', default=None, help='W,H of the output frame; default is the whole plate')
p.add_argument('--start', default='0,0', help='x,y of the window on the plate at frame 0')
p.add_argument('--pan', default='0,0', help='dx,dy the window travels over the clip')
p.add_argument('--ease', action='store_true', help='ease the pan in and out instead of a linear move')
a = p.parse_args()

plate = np.array(Image.open(a.plate).convert('RGB')).astype(np.float32)
src = np.array(Image.open(a.figure).convert('RGB')).astype(np.float32)
PH, PW = plate.shape[:2]
if src.shape[:2] != plate.shape[:2]:
    raise SystemExit(f'plate is {PW}x{PH} but figure is {src.shape[1]}x{src.shape[0]}; '
                     'both must be the same painting at the same scale')

mox, moy = (int(q) for q in a.mask_offset.split(',')) if a.mask_offset else (0, 0)


def load(dirs, only=None):
    """Union of the named planes across mask dirs, in plate coordinates."""
    acc = np.zeros((PH, PW), np.float32)
    got = []
    for d in dirs:
        meta = json.load(open(Path(d) / 'layers.json'))
        # a mask cut against a 720x1280 shot silently lands in the wrong place on
        # a 1070x1380 pan strip, and the damage looks plausible. Refuse instead.
        if meta.get('size') and list(meta['size']) != [PW, PH] and not a.mask_offset:
            raise SystemExit(f'masks in {d} were cut against {meta["size"]} but the plate is '
                             f'{[PW, PH]}; pass --mask-offset to say where they belong')
        for pl in meta['planeList']:
            if only and pl['name'] != only:
                continue
            mi = np.array(Image.open(Path(d) / 'masks' / f"{pl['n']:03d}.png").convert('L'), np.float32) / 255
            ox, oy = pl['offset'][0] + mox, pl['offset'][1] + moy
            mh, mw = mi.shape
            acc[oy:oy + mh, ox:ox + mw] = np.maximum(acc[oy:oy + mh, ox:ox + mw], mi)
            got.append(pl['name'])
    return acc, got


m, names = load(a.masks, a.only)
if not names:
    raise SystemExit('no planes matched --only')
if a.feather:
    m = np.array(Image.fromarray((m * 255).astype(np.uint8))
                 .filter(ImageFilter.GaussianBlur(a.feather)), np.float32) / 255

# --- limbs: each one is its own drawing, hinged at its own pivot ---------------
# A quadruped's legs defeat the body deform: the hem shear is built for cloth and
# it thins and smears a leg. A leg is a rigid part on a hinge, so it gets one.
limbs = []
for d in a.limbs or []:
    meta = json.load(open(Path(d) / 'layers.json'))
    for pl in meta['planeList']:
        mi = np.array(Image.open(Path(d) / 'masks' / f"{pl['n']:03d}.png").convert('L'), np.float32) / 255
        ox, oy = pl['offset'][0] + mox, pl['offset'][1] + moy
        full = np.zeros((PH, PW), np.float32)
        full[oy:oy + mi.shape[0], ox:ox + mi.shape[1]] = mi
        px, py = pl['pivot'][0] + ox, pl['pivot'][1] + oy
        limbs.append({'name': pl['name'], 'alpha': full, 'pivot': (float(px), float(py)),
                      'phase': float(pl.get('phase', 0.0)),
                      'length': float(pl.get('lengthPx', 1)),
                      'behind': bool(pl.get('behind', pl['name'].startswith('far')))})
if limbs:
    # the body keeps only what is not a limb
    lim = np.zeros((PH, PW), np.float32)
    for L in limbs:
        lim = np.maximum(lim, L['alpha'])
    # subtract exactly the limb's own footprint and no more. Dilating here opens a
    # ring the limb cannot cover, and the inpainted plate shows through it as a
    # bright sliver where the leg meets the body.
    m = m * (1 - np.clip(lim, 0, 1))

over, overNames = load(a.over) if a.over else (None, [])
if over is not None and a.feather:
    over = np.array(Image.fromarray((over * 255).astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(a.feather)), np.float32) / 255

ys, xs = np.nonzero(m > 0.5)
top, bot = int(ys.min()), int(ys.max())
height = max(bot - top, 1)

dx_t, dy_t = (float(q) for q in a.travel.split(','))
pan_x, pan_y = (float(q) for q in a.pan.split(','))
sx, sy = (int(q) for q in a.start.split(','))
if a.window:
    FW, FH = (int(q) for q in a.window.split(','))
else:
    FW, FH, sx, sy, pan_x, pan_y = PW, PH, 0, 0, 0.0, 0.0
if FW > PW or FH > PH:
    raise SystemExit(f'window {FW}x{FH} is bigger than the plate {PW}x{PH}')
for u in (0.0, 1.0):
    wx, wy = sx + pan_x * u, sy + pan_y * u
    if not (0 <= wx <= PW - FW and 0 <= wy <= PH - FH):
        raise SystemExit(f'the pan leaves the plate: window at u={u} is ({wx:.0f},{wy:.0f}), '
                         f'plate allows x 0..{PW-FW}, y 0..{PH-FH}')

# The sprite is cut once, from the figure's own bounding box plus room for the
# gait to push ink outside it. Everything below deforms this patch, never the
# whole plate, so a 3000px pan strip costs no more than a single frame.
pad = int(max(abs(a.swing) * 2 + abs(a.bob) * 2 + height * np.deg2rad(abs(a.lean)) + 8, 12))
gx0, gx1 = max(0, int(xs.min()) - pad), min(PW, int(xs.max()) + pad + 1)
gy0, gy1 = max(0, top - pad), min(PH, bot + pad + 1)
sprite = src[gy0:gy1, gx0:gx1]
alpha = m[gy0:gy1, gx0:gx1]
gh, gw = alpha.shape
yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
# how far down the figure a pixel sits, 0 at the head and 1 at the ground: the
# hem shear and the pitch both key off this
depth = np.clip((yy + gy0 - top) / height, 0, 1)
foot = float(bot - gy0)

ease = (lambda u: u * u * (3 - 2 * u)) if a.ease else (lambda u: u)
ndraw = max(1, a.frames // max(a.on, 1))

# the drawings: gait only, no translation. Held on twos.
drawings = []
for k in range(ndraw):
    step = 2 * np.pi * a.strides * (k / ndraw)
    dy = -a.bob * abs(np.sin(step))                # rises over each foot
    pitch = np.deg2rad(a.lean) * np.sin(step * 0.5)
    shear = a.swing * np.sin(step - 0.9) * depth ** 1.5   # hem lags, alternating
    px_ = -(yy - foot) * np.sin(pitch)                    # pitch about the feet
    mapx = (xx - (shear + px_)).astype(np.float32)
    mapy = (yy - dy).astype(np.float32)
    drawings.append((
        cv2.remap(sprite, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE),
        cv2.remap(alpha, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)))

enc = subprocess.Popen(
    ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
     '-s', f'{FW - FW % 2}x{FH - FH % 2}', '-r', str(a.fps), '-i', '-',
     '-c:v', 'libx264', '-crf', '15', '-pix_fmt', 'yuv420p', a.out], stdin=subprocess.PIPE)

stride = abs(dx_t) / max(a.strides, 1e-6)          # ground covered per leg cycle
for L in limbs:
    if a.limb_swing:
        L['amp'] = np.deg2rad(a.limb_swing)
    else:
        # the hoof is planted through stance, so the leg must sweep exactly far
        # enough to carry the body one stride: half a stride either side of the
        # pivot. Derive it, do not dial it.
        L['amp'] = float(np.arcsin(np.clip(stride / 2 / max(L['length'], 1), 0, 0.95)))
    ys_, xs_ = np.nonzero(L['alpha'] > 0.02)
    px_, py_ = L['pivot']
    pad = int(L['length'] * L['amp'] + a.lift + 8)
    L['box'] = (max(0, int(min(xs_.min(), px_)) - pad), max(0, int(min(ys_.min(), py_)) - pad),
                min(PW, int(max(xs_.max(), px_)) + pad + 1), min(PH, int(max(ys_.max(), py_)) + pad + 1))
    bx0, by0, bx1, by1 = L['box']
    L['src'] = src[by0:by1, bx0:bx1]
    L['al'] = L['alpha'][by0:by1, bx0:bx1]
    L['plocal'] = (px_ - bx0, py_ - by0)


def limb_angle(L, u):
    """Where this leg is in its own cycle, and how far the hoof is off the ground.

    Stance is the half an animator draws first: the foot does not move, so the
    leg rotates backward at the rate the ground passes. Swing is the fast return.
    A sine through both is what makes a cheap walk cycle skate."""
    c = (a.strides * u + L['phase']) % 1.0
    if c < a.stance:
        return L['amp'] * (1 - 2 * c / a.stance), 0.0
    s = (c - a.stance) / max(1 - a.stance, 1e-6)
    s = s * s * (3 - 2 * s)                                    # ease the return
    return L['amp'] * (-1 + 2 * s), a.lift * np.sin(np.pi * s)


def blit(frame, rgbpatch, alphapatch, ix, iy):
    gh_, gw_ = alphapatch.shape
    dx0, dy0 = max(0, ix), max(0, iy)
    dx1, dy1 = min(FW, ix + gw_), min(FH, iy + gh_)
    if dx1 <= dx0 or dy1 <= dy0:
        return
    s_ = (slice(dy0 - iy, dy1 - iy), slice(dx0 - ix, dx1 - ix))
    av_ = alphapatch[s_][..., None]
    frame[dy0:dy1, dx0:dx1] = frame[dy0:dy1, dx0:dx1] * (1 - av_) + rgbpatch[s_] * av_


def draw_limb(frame, L, u, wx, wy):
    ang, lift = limb_angle(L, u)
    bx0, by0, bx1, by1 = L['box']
    fx_ = bx0 + dx_t * u - wx
    fy_ = by0 + dy_t * u - wy - lift
    ix_, iy_ = int(np.floor(fx_)), int(np.floor(fy_))
    Mr = cv2.getRotationMatrix2D(L['plocal'], float(np.rad2deg(ang)), 1.0)
    Mr[0, 2] += fx_ - ix_
    Mr[1, 2] += fy_ - iy_
    wh = (bx1 - bx0, by1 - by0)
    rgbp = cv2.warpAffine(L['src'], Mr, wh, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    alp = cv2.warpAffine(L['al'], Mr, wh, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    blit(frame, rgbp, alp, ix_, iy_)


for i in range(a.frames):
    u = ease(i / max(a.frames - 1, 1))
    wx, wy = sx + pan_x * u, sy + pan_y * u                # the pan, on ones
    fig, al = drawings[(i // a.on) % ndraw]                # the drawing, on twos
    # where the sprite sits in the frame: its plate position, plus how far the
    # figure has travelled, minus where the camera is looking
    fx = gx0 + dx_t * u - wx
    fy = gy0 + dy_t * u - wy
    ix, iy = int(np.floor(fx)), int(np.floor(fy))
    frx, fry = fx - ix, fy - iy
    if frx or fry:                                        # keep travel subpixel-smooth
        Mt = np.array([[1, 0, frx], [0, 1, fry]], np.float32)
        figf = cv2.warpAffine(fig, Mt, (gw, gh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        alf = cv2.warpAffine(al, Mt, (gw, gh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    else:
        figf, alf = fig, al

    # The window is sampled at subpixel precision. Rounding it to whole pixels
    # measured a pan that stepped 3.95-5.01px against an ideal 4.59: on ink
    # texture that uneven step reads as a shimmer, and it is the single thing
    # that would make a hand-built pan look machine-made.
    iwx, iwy = int(np.floor(wx)), int(np.floor(wy))
    frame = plate[iwy:iwy + FH + 1, iwx:iwx + FW + 1]
    Mw = np.array([[1, 0, iwx - wx], [0, 1, iwy - wy]], np.float32)
    frame = cv2.warpAffine(frame, Mw, (FW, FH), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)

    # far legs, then the body, then near legs: the order the cels sit in
    for L in limbs:
        if L['behind']:
            draw_limb(frame, L, u, wx, wy)
    blit(frame, figf, alf, ix, iy)
    for L in limbs:
        if not L['behind']:
            draw_limb(frame, L, u, wx, wy)

    if over is not None:
        # the overlay cel: painted foreground laid back on top, so the puppet
        # walks behind the pine instead of through it
        ov = cv2.warpAffine(over[iwy:iwy + FH + 1, iwx:iwx + FW + 1], Mw, (FW, FH),
                            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)[..., None]
        fg = cv2.warpAffine(src[iwy:iwy + FH + 1, iwx:iwx + FW + 1], Mw, (FW, FH),
                            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        frame = frame * (1 - ov) + fg * ov

    enc.stdin.write(np.clip(frame[:FH - FH % 2, :FW - FW % 2], 0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()

print(json.dumps({'out': a.out, 'figure': names, 'overlay': overNames,
                  'limbs': [{'name': L['name'], 'phase': L['phase'],
                             'swingDeg': round(float(np.rad2deg(L['amp'])), 2),
                             'lengthPx': L['length']} for L in limbs],
                  'stance': a.stance if limbs else None, 'frames': a.frames,
                  'uniqueDrawings': ndraw, 'on': a.on,
                  'plate': [PW, PH], 'window': [FW, FH],
                  'panPx': [pan_x, pan_y], 'travelPx': [dx_t, dy_t],
                  'walksInPlace': abs(dx_t - pan_x) < 1 and abs(dy_t - pan_y) < 1,
                  'strides': a.strides, 'figureHeightPx': int(height),
                  'pxPerStride': round(abs(dx_t) / max(a.strides, 1e-6), 1),
                  'note': ('each limb is a rigid part on its own hinge; the hoof is planted '
                           'through stance, so the swing angle is derived from stride and leg '
                           'length rather than dialled')
                  if limbs else
                          ('legs are never drawn: the robe hides them, which is why '
                           'this is displacement and not invention')}, indent=2))
