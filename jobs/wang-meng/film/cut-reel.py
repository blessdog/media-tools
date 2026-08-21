#!/usr/bin/env python3
"""Dissolve a zone's station legs into one reel, in station order.

    cut-reel.py --zone z3w [--xfade 0.7] [--out film/STATIONS-z3w.mp4]

Order comes from stations-slow.json, never from filenames. Each leg's length
is probed, so legs of unequal duration still dissolve at the right offsets.
"""
import argparse, json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--zone', required=True)
ap.add_argument('--xfade', type=float, default=None, help='seconds; default pacing.crossfade')
ap.add_argument('--out')
a = ap.parse_args()

spec = json.loads((HERE / 'stations-slow.json').read_text())
xf = a.xfade if a.xfade is not None else spec.get('pacing', {}).get('crossfade', 0.7)
legs = [HERE / f"ST-{a.zone}-{s['name']}.mp4" for s in spec['stations'] if s['zone'] == a.zone]
missing = [str(l) for l in legs if not l.exists()]
if missing:
    raise SystemExit('missing legs:\n  ' + '\n  '.join(missing))

def dur(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                          '-of', 'csv=p=0', str(p)]).decode().strip())
durs = [dur(l) for l in legs]
cmd = ['ffmpeg', '-y', '-loglevel', 'error']
for l in legs:
    cmd += ['-i', str(l)]
filt, prev, acc = [], '[0:v]', durs[0]
for i in range(1, len(legs)):
    off = acc - xf
    filt.append(f'{prev}[{i}:v]xfade=transition=fade:duration={xf}:offset={off:.3f}[v{i}]')
    prev = f'[v{i}]'
    acc = off + durs[i]
out = Path(a.out) if a.out else HERE / f'STATIONS-{a.zone}.mp4'
cmd += ['-filter_complex', ';'.join(filt), '-map', prev, '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', str(out)]
subprocess.run(cmd, check=True)
print(json.dumps({'out': str(out), 'stations': [l.stem.split(f'{a.zone}-', 1)[1] for l in legs],
                  'seconds': round(acc, 2), 'xfade': xf}, indent=1))
