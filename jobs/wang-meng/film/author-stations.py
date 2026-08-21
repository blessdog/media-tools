#!/usr/bin/env python3
"""Turn station-moves.json into one camera path per station.

    author-stations.py --zone z3w

Reads stations-slow.json (where each place is, in master px) and
station-moves.json (which move from knowledge/shot-vocabulary.md), writes
paths/st-<zone>-<station>.json. Every key is clamped so the view stays inside
the zone plate at its fov. Render with render-leg.sh st-<zone>-<station> <zone>.
"""
import argparse, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--zone', required=True)
a = ap.parse_args()

K, OUT_W, OUT_H = 2.34, 1920, 1080
spec = json.loads((HERE / 'stations-slow.json').read_text())
moves = json.loads((HERE / 'station-moves.json').read_text())
box = json.loads((HERE / f'../journey/{a.zone}/plate.json').resolve().read_text())['masterBox']
x0, y0, x1, y1 = box
content = spec.get('contentRect', box)
SEC = moves.get('seconds', 10)

def clamp(mx, my, fov):
    hw, hh = OUT_W / 2 * K / fov, OUT_H / 2 * K / fov
    lx0, ly0 = max(x0, content[0]), max(y0, content[1])
    lx1, ly1 = min(x1, content[2]), min(y1, content[3])
    mx = min(max(mx, lx0 + hw), lx1 - hw)
    my = min(max(my, ly0 + hh), ly1 - hh)
    return mx, my

def key(t, mx, my, fov, z=0.0, rx=0.0, ry=0.0):
    mx, my = clamp(mx, my, fov)
    k = {'t': round(t, 2), 'x': round(mx / (x1 - x0), 5), 'y': round((my - y0) / (y1 - y0), 5),
         'z': round(z, 3), 'fov': round(fov, 3)}
    if rx: k['rx'] = round(rx, 3)
    if ry: k['ry'] = round(ry, 3)
    return k

def author(st, move):
    w, d = st['wide'], st['detail']
    mx, my, f = w['mx'], w['my'], w['fov']
    if move == 'hold':
        fov = f * 1.25
        return [key(0, mx, my, fov), key(SEC, mx, my, fov * 1.012)]
    if move == 'track':
        fov, dx = 1.3, 450
        return [key(0, mx - dx, my, fov), key(SEC, mx + dx, my, fov)]
    if move == 'unroll':
        fov, dy = f * 1.1, 450
        return [key(0, mx, my + dy, fov), key(SEC, mx, my - dy, fov)]
    if move == 'push':
        return [key(0, mx, my, f * 1.15),
                key(2.0, mx, my, f * 1.15),
                key(SEC, d['mx'], d['my'], d['fov'] * 0.85, z=d.get('z', 0.2) * 0.6,
                    rx=d.get('rx', 0) * 0.5, ry=d.get('ry', 0) * 0.5)]
    if move == 'peek':
        fov, z, dx = 1.35, 0.18, 250
        cx, cy = d['mx'], d['my']
        return [key(0, cx - dx, cy, fov, z=z, ry=-0.22),
                key(6.0, cx + dx, cy, fov, z=z, ry=0.22),
                key(SEC, cx, cy, fov, z=z, ry=0.0)]
    raise SystemExit(f'unknown move {move!r}')

out = []
prev = None
for st in spec['stations']:
    if st['zone'] != a.zone:
        continue
    m = moves[a.zone][st['name']]
    if m['move'] == prev:
        raise SystemExit(f"{st['name']}: same move as the previous station ({prev}) -- vocabulary rule")
    prev = m['move']
    path = {'fps': 24, 'duration': float(SEC), 'move': m['move'], 'station': st['name'],
            '_note': f"{m['move'].upper()} -- {m['why']}. {st.get('why','')}",
            'keys': author(st, m['move'])}
    p = HERE / 'paths' / f"st-{a.zone}-{st['name']}.json"
    p.write_text(json.dumps(path, indent=1))
    out.append({'station': st['name'], 'move': m['move'], 'path': p.name})
print(json.dumps(out, indent=1))
