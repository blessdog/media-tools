#!/usr/bin/env python3
"""Turn per-tile catalogues into ONE catalogue in master-image pixels.

    catalogue-to-master.py --tiles jobs/.../tiles.json --catalogues jobs/.../ \
                           --out master-catalogue.json [--iou 0.35]

A very large painting is labelled tile by tile because a VLM can only read a
tile. That leaves two problems this tool exists to fix:

  1. Boxes are normalised to their own tile. Only master px compose with
     regions.json, living-polys.json and every renderer in this repo.
  2. Tiles OVERLAP, so one tree at a seam is labelled twice, under two ids,
     with two half-boxes. Left alone it becomes two cards that swing out of
     phase across a join -- visible, and exactly the kind of defect that
     survives review because each tile looks right on its own.

Merging rule: same `kind`, and the two master boxes either exceed --iou or one
sits mostly inside the other. Merged boxes take the UNION, the longer note, and
the more urgent depth (near > mid > far), because a tree straddling a seam is
as near as its nearest half.

WHAT THIS IS NOT FOR: deciding what a thing IS (that is the VLM pass that
writes the tile catalogues) or finding an exact edge (that is
refine-mask-sam.py, which takes this file via --boxes).
"""
import argparse, json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--tiles', required=True, help='tiles.json written by tile-image.py')
p.add_argument('--catalogues', required=True, help='directory holding t*.json')
p.add_argument('--out', required=True)
p.add_argument('--iou', type=float, default=0.35, help='above this, two same-kind boxes are one object')
p.add_argument('--contain', type=float, default=0.70, help='or this much of the smaller box lies inside the larger')
a = p.parse_args()

tiles = json.loads(Path(a.tiles).read_text())
by_file = {t['file']: t for t in tiles['tiles']}
cdir = Path(a.catalogues)

objs, missing = [], []
for t in tiles['tiles']:
    cj = cdir / (Path(t['file']).stem + '.json')
    if not cj.exists():
        missing.append(t['file']); continue
    cat = json.loads(cj.read_text())
    x0, y0, x1, y1 = t['sourceBox']
    w, h = x1 - x0, y1 - y0
    for o in cat['objects']:
        bx0, by0, bx1, by1 = o['box']
        m = dict(o)
        m['box'] = [round(x0 + bx0 * w), round(y0 + by0 * h),
                    round(x0 + bx1 * w), round(y0 + by1 * h)]
        m['tile'] = t['file']
        m['id'] = f"{Path(t['file']).stem}:{o['id']}"
        objs.append(m)

DEPTH = {'near': 0, 'mid': 1, 'far': 2}

def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])

def inter(a_, b_):
    return area([max(a_[0], b_[0]), max(a_[1], b_[1]), min(a_[2], b_[2]), min(a_[3], b_[3])])

def same(a_, b_):
    if a_.get('kind') != b_.get('kind'):
        return False
    i = inter(a_['box'], b_['box'])
    if not i:
        return False
    u = area(a_['box']) + area(b_['box']) - i
    if u and i / u >= a.iou:
        return True
    return i / max(1, min(area(a_['box']), area(b_['box']))) >= a.contain

merged = []
for o in sorted(objs, key=lambda o: -area(o['box'])):
    for m in merged:
        if same(m, o):
            m['box'] = [min(m['box'][0], o['box'][0]), min(m['box'][1], o['box'][1]),
                        max(m['box'][2], o['box'][2]), max(m['box'][3], o['box'][3])]
            m['mergedFrom'] = m.get('mergedFrom', [m['id']]) + [o['id']]
            if len(o.get('note', '')) > len(m.get('note', '')):
                m['note'] = o['note']
            if DEPTH.get(o.get('depth'), 9) < DEPTH.get(m.get('depth'), 9):
                m['depth'] = o['depth']
            m['leavesVisible'] = m.get('leavesVisible') or o.get('leavesVisible')
            break
    else:
        merged.append(dict(o))

merged.sort(key=lambda o: (o['box'][1], o['box'][0]))
out = {'tool': 'catalogue-to-master', 'image': tiles.get('image'),
       'sourceSize': tiles.get('sourceSize'), 'space': 'master-px',
       'tilesTotal': len(tiles['tiles']), 'tilesCatalogued': len(tiles['tiles']) - len(missing),
       'tilesMissing': missing, 'objectsBeforeMerge': len(objs), 'objects': merged}
Path(a.out).write_text(json.dumps(out, indent=1))
kinds = {}
for m in merged:
    kinds[m.get('kind')] = kinds.get(m.get('kind'), 0) + 1
print(json.dumps({'out': a.out, 'tilesCatalogued': out['tilesCatalogued'], 'tilesMissing': missing,
                  'objectsBeforeMerge': len(objs), 'objectsAfterMerge': len(merged),
                  'byKind': kinds,
                  'seamMerges': sum(1 for m in merged if 'mergedFrom' in m)}, indent=1))
