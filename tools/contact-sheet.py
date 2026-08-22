#!/usr/bin/env python3
"""media-tools — contact-sheet: tile several rendered loops into ONE sheet. One job.

Ryan sees every candidate AT ONCE and gives one verdict, instead of being shown
them one at a time over an hour. Measured 2026-08-21: eight canopy variants were
rendered and two were ever put on screen, sequentially, and the question they
were meant to settle is still open.

WHAT THIS IS NOT FOR, AND WHAT IS:

  (a renderer)       This tool does not render anything. It takes cells that
                     ALREADY EXIST and tiles them. Sweeping a parameter is a
                     lane's job -- a small script that calls the effect tool N
                     times and then calls this one -- because the tool contract
                     says no tool invokes another tool. That separation is what
                     lets a sheet mix sources: a hinge-foliage sweep beside a
                     swing-card cycle beside last week's mp4.
  ab-cycle.py        TWO clips, full size, side by side, for a close look at one
                     difference. Use it when the question is "which of these
                     two", not "which of these nine".
  --still            when the answer is legible in one frame (a mask, a plate, a
                     hole opening). A moving sheet costs nine renders of
                     attention; a still costs one.

CELLS may be a directory of frames, an .mp4, or a single image (a still cell is
a legitimate control -- the null beside the effect). They need not share a size
or an aspect: each is fitted into its box and letterboxed, so a portrait strip
and a landscape crop can sit in the same grid without either being distorted.

LABELS ARE DRAWN WITH PIL, NOT ffmpeg. This machine's ffmpeg is built without
libfreetype, so `drawtext` does not exist and a filtergraph using it dies at
encode time -- after the render, which is the expensive half.

FRAMES ARE PIPED TO ffmpeg AS RAW RGB and never written to disk. A sheet of
nine 480px cells is ~1.5GB of PNGs if staged; measured 2026-08-21, one concat
left 583MB of intermediates behind and Ryan had to clear space by hand.

usage:
  contact-sheet.py --cells DIR|MP4|IMG [...] --out SHEET.mp4
      [--labels "a,b,c"] [--cols N] [--cell-width 480] [--seconds 2] [--fps 24]
      [--focus none|motion] [--crop x0,y0,x1,y1] [--title TEXT]
      [--still] [--at 0.15]

example:
  contact-sheet.py --out sheet.mp4 --title "z1 canopies at swing 6" \\
      --cells jobs/wang-meng/journey/z1/living-work/*/drawings --focus motion

exit 0 clean · exit 2 with a one-line reason the sheet cannot be built.
JSON on stdout. Progress on stderr.
"""
import argparse, json, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
# Pillow 10 moved the filters onto Image.Resampling and Pillow 9 has not got it.
LANCZOS = getattr(getattr(Image, 'Resampling', Image), 'LANCZOS')
IMG_EXT = {'.png', '.jpg', '.jpeg', '.tif', '.tiff'}
VID_EXT = {'.mp4', '.mov', '.mkv', '.webm'}


def die(msg):
    """Exit 2 with ONE line, the same contract as the linter. A violation the
    human has to scroll to read is a violation they will not read."""
    print(f'contact-sheet: {msg}', file=sys.stderr)
    sys.exit(2)


def load_cell(path, want):
    """Return up to `want` frames as a list of HxWx3 uint8, looping if short."""
    p = Path(path)
    if not p.exists():
        die(f'no such cell: {path}')
    if p.is_dir():
        fs = sorted(f for f in p.iterdir() if f.suffix.lower() in IMG_EXT)
        if not fs:
            die(f'cell has no frames: {path}')
        fs = fs[:want] if len(fs) >= want else fs
        frames = [np.asarray(Image.open(f).convert('RGB')) for f in fs]
    elif p.suffix.lower() in VID_EXT:
        import cv2
        cap = cv2.VideoCapture(str(p))
        frames = []
        while len(frames) < want:
            ok, fr = cap.read()
            if not ok:
                break
            frames.append(fr[..., ::-1].copy())
        cap.release()
        if not frames:
            die(f'cell decoded 0 frames: {path}')
    elif p.suffix.lower() in IMG_EXT:
        frames = [np.asarray(Image.open(p).convert('RGB'))]
    else:
        die(f'cell is not a frame dir, a video or an image: {path}')
    if len({f.shape for f in frames}) > 1:
        die(f'cell has frames of differing size: {path}')
    return frames


def motion_box(frames, pad=0.10):
    """Crop to WHERE THE CELL ACTUALLY CHANGES, padded.

    A 253x988 canopy strip whose top quarter moves wastes three quarters of its
    box on ink that is identical in every candidate. Sampled, because the bbox
    of change is stable long before every frame has been read.
    """
    if len(frames) < 2:
        return None
    idx = np.linspace(0, len(frames) - 1, min(24, len(frames))).astype(int)
    a = np.stack([frames[i].astype(np.int16) for i in idx])
    d = (a.max(0) - a.min(0)).max(-1) > 6
    if not d.any():
        return None
    ys, xs = np.nonzero(d)
    h, w = d.shape
    py, px = int(h * pad), int(w * pad)
    return (max(0, xs.min() - px), max(0, ys.min() - py),
            min(w, xs.max() + px + 1), min(h, ys.max() + py + 1))


def fit(arr, bw, bh, bg):
    """Letterbox into the box. NEVER distort: a squashed painting is a lie about
    the painting, and this sheet exists to be judged by eye."""
    h, w = arr.shape[:2]
    s = min(bw / w, bh / h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    im = Image.fromarray(arr).resize((nw, nh), LANCZOS)
    box = Image.new('RGB', (bw, bh), bg)
    box.paste(im, ((bw - nw) // 2, (bh - nh) // 2))
    return box


def font(sz, bold=False):
    for f in (f'/System/Library/Fonts/Supplemental/Arial{" Bold" if bold else ""}.ttf',
              '/System/Library/Fonts/Helvetica.ttc'):
        try:
            return ImageFont.truetype(f, sz)
        except Exception:
            continue
    return ImageFont.load_default()


p = argparse.ArgumentParser(add_help=True)
p.add_argument('--cells', nargs='+', required=True,
               help='frame dirs, videos or images — one per candidate')
p.add_argument('--labels', default=None,
               help='comma-separated, one per cell; default is each cell\'s own name')
p.add_argument('--cols', type=int, default=0, help='grid columns (default: near-square)')
p.add_argument('--cell-width', type=int, default=480)
p.add_argument('--cell-height', type=int, default=0,
               help='default: cell-width x the median aspect of the cells')
p.add_argument('--seconds', type=float, default=2.0)
p.add_argument('--fps', type=int, default=24)
p.add_argument('--focus', choices=('none', 'motion'), default='none',
               help='motion: crop each cell to where it changes across its loop')
p.add_argument('--crop', default=None,
               help='x0,y0,x1,y1 applied to EVERY cell; requires cells of one size')
p.add_argument('--title', default=None)
p.add_argument('--still', action='store_true', help='one PNG instead of a loop')
p.add_argument('--at', type=float, default=0.15,
               help='point in the loop for --still (default 0.15, the gust peak)')
p.add_argument('--pad', type=int, default=10)
p.add_argument('--out', required=True)
a = p.parse_args()

out = Path(a.out)
if a.still and out.suffix.lower() != '.png':
    die(f'--still writes a PNG; --out is {out.suffix or "(no suffix)"}')
if not a.still and out.suffix.lower() not in VID_EXT:
    die(f'--out must be {"/".join(sorted(VID_EXT))} (or pass --still for a PNG); got {out.suffix or "(no suffix)"}')

n = len(a.cells)
labels = [s.strip() for s in a.labels.split(',')] if a.labels else \
    [Path(c).name if Path(c).name not in ('drawings', 'cycle', 'frames') else Path(c).parent.name
     for c in a.cells]
if len(labels) != n:
    die(f'{len(labels)} labels for {n} cells — they must match one to one')

cols = a.cols or math.ceil(math.sqrt(n))
if cols < 1 or cols > n:
    die(f'--cols {cols} is not between 1 and the {n} cells given')
rows = math.ceil(n / cols)

want = 1 if a.still else max(1, round(a.seconds * a.fps))
print(f'  reading {n} cells', file=sys.stderr)
cells = [load_cell(c, 10 ** 6 if a.still else want) for c in a.cells]

if a.crop:
    try:
        cx0, cy0, cx1, cy1 = (int(v) for v in a.crop.split(','))
    except ValueError:
        die(f'--crop must be x0,y0,x1,y1; got {a.crop!r}')
    sizes = {c[0].shape[:2] for c in cells}
    if len(sizes) > 1:
        die(f'--crop needs cells of one size, but {len(sizes)} sizes are present '
            f'({", ".join(f"{w}x{h}" for h, w in sorted(sizes))}) — use --focus motion instead')
    h, w = cells[0][0].shape[:2]
    if not (0 <= cx0 < cx1 <= w and 0 <= cy0 < cy1 <= h):
        die(f'--crop {a.crop} is outside the {w}x{h} cell')
    cells = [[f[cy0:cy1, cx0:cx1] for f in c] for c in cells]
elif a.focus == 'motion':
    for i, c in enumerate(cells):
        b = motion_box(c)
        if b:
            x0, y0, x1, y1 = b
            cells[i] = [f[y0:y1, x0:x1] for f in c]
            print(f'    focus {labels[i]}: {x1-x0}x{y1-y0} of {c[0].shape[1]}x{c[0].shape[0]}',
                  file=sys.stderr)

CW = a.cell_width
CH = a.cell_height or max(60, round(CW * float(np.median([c[0].shape[0] / c[0].shape[1] for c in cells]))))
LAB, PAD, BG = 26, a.pad, (20, 20, 22)
TITLE = 34 if a.title else 0
SW = PAD + cols * (CW + PAD)
SH = TITLE + PAD + rows * (CH + LAB + PAD)
SW += SW % 2
SH += SH % 2
f_lab, f_ttl = font(15), font(19, bold=True)

if a.still:
    picks = [min(len(c) - 1, int(round(a.at * len(c)))) for c in cells]
else:
    picks = None
nframes = 1 if a.still else want


def compose(t):
    sheet = Image.new('RGB', (SW, SH), BG)
    dr = ImageDraw.Draw(sheet)
    if a.title:
        dr.text((PAD, 9), a.title, font=f_ttl, fill=(240, 240, 235))
    for i, c in enumerate(cells):
        r, k = divmod(i, cols)
        x = PAD + k * (CW + PAD)
        y = TITLE + PAD + r * (CH + LAB + PAD)
        fr = c[picks[i]] if (a.still and picks) else c[t % len(c)]
        dr.text((x + 2, y + 4), labels[i], font=f_lab, fill=(235, 215, 150))
        sheet.paste(fit(fr, CW, CH, BG), (x, y + LAB))
    return sheet


out.parent.mkdir(parents=True, exist_ok=True)
if a.still:
    compose(0).save(out)
else:
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{SW}x{SH}', '-r', str(a.fps), '-i', '-',
           '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', str(out)]
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    except FileNotFoundError:
        die('ffmpeg is not on PATH')
    assert proc.stdin is not None
    for t in range(nframes):
        proc.stdin.write(np.asarray(compose(t), np.uint8).tobytes())
        if t % 12 == 0:
            print(f'    {t+1}/{nframes}', file=sys.stderr)
    proc.stdin.close()
    if proc.wait() != 0:
        die('ffmpeg refused the sheet')

print(json.dumps({'tool': 'contact-sheet', 'out': str(out), 'cells': n,
                  'grid': f'{cols}x{rows}', 'size': f'{SW}x{SH}',
                  'frames': nframes, 'fps': None if a.still else a.fps,
                  'labels': labels, 'focus': a.focus,
                  'still': a.still}, indent=1))
