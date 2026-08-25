#!/usr/bin/env python3
"""Build a Blender scene for MARKING regions on a painting by hand. Run inside Blender.

    /Applications/Blender.app/Contents/MacOS/Blender -b \
        --python tools/blender-mark-scene.py -- \
        --plate jobs/wang-meng/journey/z3w/plate.json \
        --out jobs/wang-meng/marks/z3w-marks.blend

Then open the .blend, pick a Grease Pencil layer named for the class you are
marking, and draw. One STROKE = one REGION. Read it back with
tools/blender-read-marks.py, which writes polygons in MASTER px.

PRIOR ART (searched 2026-08-25, per LAW #0 -- do not delete this block):

  · COA Tools 2 -- github.com/Aodaruma/coa_tools2, 2D cutout rigging inside
    Blender, tested on 5.1. It rigs a sprite that is ALREADY CUT into layers by
    Photoshop/GIMP/Krita exporters. It has no opinion about WHICH ink is one
    bushel on an uncut painting, which is the only question here. Adopt it later
    for the bone/mesh half if hinge-foliage's own rig stops being enough.
  · Frame By Plane -- the multiplane/import half, already used by
    blender-multiplane.py. Its importers are GUI-only (verified: 63 of 353
    operators register headless, zero importers), and it imports LAYERED art;
    it does not author the layers.
  · Roboflow Smart Polygon / V7 / Label Studio -- browser SAM annotation, all
    shipping and all solved. Rejected for this job because none has a concept of
    a PIVOT, they are cloud dataset labellers, and the marks must land in this
    repo's own living-polys.json, not in a labelling project.
  · Blender "Annotate" tool -- the obvious choice and the WRONG one. Creating
    annotation strokes/points via the Python API is unavailable in Blender 4.3+
    (blender issue #147732) and this is 5.2.1. Grease Pencil OBJECT strokes read
    back fine via drawing.attributes. They look identical while drawing.

WHY A SCENE AND NOT A WEB PAGE: the pen drives the Mac cursor directly, so the
input is the same pointer stream in any app. Blender wins because the multiplane
camera, the plane stack and the render already live here, so a mark can be seen
against the thing it will affect without a round trip.

WHAT THIS IS NOT FOR: cutting the cards. This writes REGION OUTLINES and PIVOTS
-- human judgement that is not in the pixels (see knowledge/no-whole-tree-to-
segment.md). hinge-foliage.py still does the cutting, from these outlines.
"""
import argparse, json, sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
p = argparse.ArgumentParser(prog='blender-mark-scene.py')
p.add_argument('--plate', required=True,
               help='plate.json holding size + masterBox + masterPxPerRegionPx')
p.add_argument('--image', help='override the image; default is plate.png beside plate.json')
p.add_argument('--out', required=True, help='.blend to write')
p.add_argument('--classes', default='foliage,water,figure',
               help='one Grease Pencil layer per class, plus a pivot layer')
p.add_argument('--span', type=float, default=20.0,
               help='Blender units across the longest side (keeps viewport clipping sane)')
p.add_argument('--seed-from', help='existing living-polys.json: draw its polys in as reference')
a = p.parse_args(argv)

plate_path = Path(a.plate).resolve()
plate = json.loads(plate_path.read_text())
IW, IH = plate['size']
MX0, MY0 = plate['masterBox'][0], plate['masterBox'][1]
K = plate['masterPxPerRegionPx']
img_path = Path(a.image).resolve() if a.image else plate_path.with_name('plate.png')
if not img_path.exists():
    sys.exit(f'image not found: {img_path}')

# ---- the transform, defined ONCE and stored in the .blend -------------------
# Blender units per IMAGE px. The image lies in the XY plane with its top-left
# at the origin, +x right and -y down, so it reads like an image and the sign
# convention never has to be remembered.
S = a.span / max(IW, IH)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'NONE'

# The reader gets the transform from here. One source of truth: if the scene is
# rebuilt at a different span, marks drawn in it still resolve correctly.
scene['mark_transform'] = {
    'imageSize': [IW, IH],
    'masterOrigin': [MX0, MY0],
    'masterPxPerImagePx': K,
    'blenderUnitsPerImagePx': S,
    'plate': str(plate_path),
}

# ---- the painting, as a reference empty ------------------------------------
# An IMAGE empty draws in solid view with no material and cannot be selected by
# a stray click while drawing, which a textured mesh plane cannot promise.
img = bpy.data.images.load(str(img_path))
emp = bpy.data.objects.new('painting', None)
emp.empty_display_type = 'IMAGE'
emp.data = img
emp.empty_image_offset = (0.0, -1.0)      # anchor top-left at the object origin
emp.empty_display_size = IW * S           # width in Blender units
emp.location = (0.0, 0.0, -0.01)          # a hair behind the drawing plane
emp.hide_select = True
scene.collection.objects.link(emp)

# ---- the drawing surface ----------------------------------------------------
bpy.ops.object.grease_pencil_add(type='EMPTY', location=(0, 0, 0))
gp = bpy.context.object
gp.name = 'marks'
gpd = gp.data

classes = [c.strip() for c in a.classes.split(',') if c.strip()]
for name in classes + ['pivot']:
    gpd.layers.new(name)

# grease_pencil_add leaves a default layer called "Layer". Left in place it is a
# live trap: a stroke drawn on it reads back as a region of class "Layer".
for stray in [l for l in gpd.layers if l.name == 'Layer']:
    gpd.layers.remove(stray)

# One material per class, so what you are marking is obvious while you mark it
# and a mis-filed stroke is visible instead of silent.
PALETTE = {
    'foliage': (0.15, 0.85, 0.35, 1.0),
    'water':   (0.20, 0.55, 1.00, 1.0),
    'figure':  (1.00, 0.35, 0.75, 1.0),
    'pivot':   (1.00, 0.85, 0.10, 1.0),
}
for name in classes + ['pivot']:
    mat = bpy.data.materials.new(f'mark-{name}')
    bpy.data.materials.create_gpencil_data(mat)
    mat.grease_pencil.color = PALETTE.get(name, (0.9, 0.9, 0.9, 1.0))
    mat.grease_pencil.show_stroke = True
    mat.grease_pencil.show_fill = False
    gp.data.materials.append(mat)

# Draw on the flat XY plane at z=0 regardless of view angle, so a mark lands
# where it looks like it lands.
ts = scene.tool_settings
ts.gpencil_stroke_placement_view3d = 'ORIGIN'
if hasattr(ts, 'gpencil_sculpt'):
    ts.use_gpencil_draw_onback = False

# ---- optional: seed with the polys that already exist -----------------------
seeded = 0
if a.seed_from:
    polys = json.loads(Path(a.seed_from).read_text()).get('polys', [])
    by_class = {}
    for poly in polys:
        by_class.setdefault(poly.get('class', 'foliage'), []).append(poly)
    for cls, items in by_class.items():
        lay = gpd.layers.get(f'ref-{cls}') or gpd.layers.new(f'ref-{cls}')
        lay.lock = True
        frame = lay.frames.new(1) if len(lay.frames) == 0 else lay.frames[0]
        drawing = frame.drawing
        for poly in items:
            pts = poly.get('points') or []
            if len(pts) < 2:
                continue
            drawing.add_strokes([len(pts)])
            stroke = drawing.strokes[-1]
            for i, (mx, my) in enumerate(pts):
                stroke.points[i].position = (
                    (mx - MX0) / K * S, -(my - MY0) / K * S, 0.0)
            seeded += 1

# ---- a camera, so the whole plate is framed on open ------------------------
cam_data = bpy.data.cameras.new('mark-cam')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = max(IW, IH) * S
cam_data.clip_end = 1000.0
cam = bpy.data.objects.new('mark-cam', cam_data)
cam.location = (IW * S / 2, -IH * S / 2, 10.0)
scene.collection.objects.link(cam)
scene.camera = cam

# ---- open ready to draw ------------------------------------------------------
# A scene that needs five clicks of setup before the first mark is a scene that
# does not get used. Frame the plate, look straight down it, and be in Draw mode.
gpd.layers.active = gpd.layers[classes[0]]
cx, cy = IW * S / 2.0, -IH * S / 2.0
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            if space.type != 'VIEW_3D':
                continue
            space.shading.type = 'SOLID'
            space.overlay.show_floor = False
            space.overlay.show_axis_x = False
            space.overlay.show_axis_y = False
            space.clip_start = 0.01
            space.clip_end = 10000.0
            r3d = space.region_3d
            r3d.view_perspective = 'ORTHO'
            r3d.view_rotation = (1.0, 0.0, 0.0, 0.0)   # straight down -Z
            r3d.view_location = (cx, cy, 0.0)
            r3d.view_distance = max(IW, IH) * S * 0.62

bpy.context.view_layer.objects.active = gp
gp.select_set(True)

Path(a.out).parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.out).resolve()))

print(json.dumps({
    'out': a.out,
    'image': str(img_path),
    'imageSize': [IW, IH],
    'masterOrigin': [MX0, MY0],
    'masterPxPerImagePx': K,
    'blenderUnitsPerImagePx': round(S, 8),
    'layers': classes + ['pivot'],
    'seededStrokes': seeded,
}, indent=1))
