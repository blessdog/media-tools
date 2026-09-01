#!/usr/bin/env python3
"""Read hand-drawn region marks out of a Blender scene into MASTER px. Run inside Blender.

    /Applications/Blender.app/Contents/MacOS/Blender -b \
        jobs/wang-meng/marks/z3w-marks.blend \
        --python tools/blender-read-marks.py -- \
        --out jobs/wang-meng/marks/z3w-polys.json [--simplify 6]

One Grease Pencil STROKE = one REGION. The layer name is the region's class.
Strokes on the `pivot` layer are not regions: each one contributes a PIVOT to
the region whose polygon contains its first point.

Output matches jobs/wang-meng/living/living-polys.json: {"polys":[{id, class,
points}]}, points in master px, so it can be merged straight in.

WHAT THIS IS NOT FOR: reading the Annotate tool. Annotation strokes are not
reachable from Python in Blender 4.3+ (issue #147732). This reads Grease Pencil
OBJECT strokes, which are. See tools/blender-mark-scene.py, which builds a scene
that can only be drawn on the readable way.
"""
import argparse, json, sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
p = argparse.ArgumentParser(prog='blender-read-marks.py')
p.add_argument('--out', required=True)
p.add_argument('--object', default='marks', help='Grease Pencil object name')
p.add_argument('--simplify', type=float, default=0.0,
               help='drop points closer than this many MASTER px to the running line')
p.add_argument('--min-points', type=int, default=3)
p.add_argument('--prefix', default='m', help='id prefix for generated regions')
a = p.parse_args(argv)

scene = bpy.context.scene
tf = scene.get('mark_transform')
if tf is None:
    sys.exit('scene has no mark_transform -- was it built by blender-mark-scene.py?')
def plain(v):
    """Blender custom properties come back as IDPropertyArray/IDPropertyGroup,
    which look like lists and dicts until json.dumps refuses them."""
    if hasattr(v, 'to_dict'):
        return {k: plain(x) for k, x in v.to_dict().items()}
    if hasattr(v, 'to_list'):
        return v.to_list()
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    return v


tf = {k: plain(v) for k, v in dict(tf).items()}
MX0, MY0 = tf['masterOrigin']
K = tf['masterPxPerImagePx']
S = tf['blenderUnitsPerImagePx']

gp = bpy.data.objects.get(a.object)
if gp is None or gp.type != 'GREASEPENCIL':
    sys.exit(f'no Grease Pencil object named {a.object!r}')


def to_master(pos):
    """Blender world XY -> master px. The exact inverse of the scene builder."""
    x, y, _ = pos
    return [round(MX0 + (x / S) * K), round(MY0 + (-y / S) * K)]


def perpendicular_distance(pt, start, end):
    (px, py), (x0, y0), (x1, y1) = pt, start, end
    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return ((px - x0) ** 2 + (py - y0) ** 2) ** 0.5
    t = ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return ((px - (x0 + t * dx)) ** 2 + (py - (y0 + t * dy)) ** 2) ** 0.5


def rdp(points, eps):
    """Ramer-Douglas-Peucker. A hand-drawn loop is hundreds of points; the
    polygon that matters is a dozen. Runs in MASTER px so the tolerance is a
    real distance on the painting, not a viewport-zoom artifact."""
    if eps <= 0 or len(points) < 3:
        return points
    worst, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = perpendicular_distance(points[i], points[0], points[-1])
        if d > worst:
            worst, idx = d, i
    if worst <= eps:
        return [points[0], points[-1]]
    return rdp(points[:idx + 1], eps)[:-1] + rdp(points[idx:], eps)


def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xint = (x1 - x0) * (y - y0) / (y1 - y0) + x0
            if x < xint:
                inside = not inside
    return inside


polys, pivots, skipped = [], [], []
counters = {}

for layer in gp.data.layers:
    cls = layer.name
    if cls.startswith('ref-'):          # seeded reference, not a new mark
        continue
    for frame in layer.frames:
        for stroke in frame.drawing.strokes:
            pts = [to_master(pt.position) for pt in stroke.points]
            # collapse consecutive duplicates from a slow pen/mouse
            dedup = [pts[0]] if pts else []
            for q in pts[1:]:
                if q != dedup[-1]:
                    dedup.append(q)
            if cls == 'pivot':
                if dedup:
                    pivots.append(dedup[0])
                continue
            simplified = rdp(dedup, a.simplify)
            if len(simplified) < a.min_points:
                skipped.append({'class': cls, 'points': len(simplified)})
                continue
            counters[cls] = counters.get(cls, 0) + 1
            polys.append({
                'id': f'{a.prefix}-{cls}-{counters[cls]:03d}',
                'class': cls,
                'points': simplified,
                'note': 'authored in Blender',
            })

# assign each pivot to the region that contains it
unassigned = []
for pv in pivots:
    for poly in polys:
        if point_in_poly(pv, poly['points']):
            poly.setdefault('pivots', []).append(pv)
            break
    else:
        unassigned.append(pv)

out = {
    'note': ('Authored by hand in Blender via tools/blender-mark-scene.py. '
             'One stroke = one region; layer name = class. Points are MASTER px '
             'and merge into living-polys.json.'),
    'source': bpy.data.filepath,
    'transform': tf,
    'polys': polys,
}
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))

print(json.dumps({
    'out': a.out,
    'regions': len(polys),
    'byClass': counters,
    'pivotsPlaced': sum(len(p.get('pivots', [])) for p in polys),
    'pivotsUnassigned': len(unassigned),
    'skippedTooFewPoints': skipped,
}, indent=1))
