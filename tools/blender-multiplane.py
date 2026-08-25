#!/usr/bin/env python3
"""Build a Blender MULTIPLANE scene from a cut layer stack. Run inside Blender.

    /Applications/Blender.app/Contents/MacOS/Blender -b \
        --python tools/blender-multiplane.py -- \
        --layers jobs/wang-meng/journey/z3w/layers-filled \
        --geometry jobs/wang-meng/journey/z3w/geometry.json \
        --out /tmp/mp --frames 1 [--path path.json] [--save scene.blend]

PRIOR ART (searched 2026-08-25, per LAW #0 — do not delete this block):

  · Frame By Plane — free GPL-3.0 Blender add-on, github.com/Cre-Pan/frame-by-plane.
    Image planes at camera depth, multiplane camera setups, parallax, cutout
    animation, 62 effects, and it imports layered PSD/PROCREATE preserving
    transparency and layer order. Requires Blender 5.2 LTS. UPDATED
    2026-08-25: this machine is on 5.2.1 LTS now, so that blocker is GONE and the
    add-on is installable today. IT IS THE RIGHT TOOL for the authoring half of
    LAYERED art — but note it imports layers someone else already cut; deciding
    WHICH INK IS ONE BUSHEL is authored via tools/blender-mark-scene.py.
  · Blender "Images as Planes" (built in) — does the import, not the depth rig.
  · After Effects 3D layers + camera — industry default, not scriptable from
    this pipeline, not free.
  · Pixera 2.5D — virtual production, wrong scale of tool.

  WHY THIS FILE EXISTS ANYWAY, stated so it can be deleted when it stops being
  true: Frame By Plane is a UI add-on for a human arranging artwork. This repo
  needs the same scene built HEADLESS from an existing layers.json that SAM
  already cut, with the plane tilts a previous verdict measured. That is 90
  lines of bpy against an add-on that cannot be driven from a shell. UPDATED 2026-08-25: the
  Procreate half of that sentence is DEAD — the pen surface is an XP-Pen Deco
  driving this Mac, not an iPad, so authoring happens in Blender itself
  (tools/blender-mark-scene.py) and no Procreate round trip exists.

WHAT THIS REPLACES: tools/render-parallax.py (639 lines) — a hand-rolled
multiplane camera with its own projection maths, written while Blender sat
installed on the same disk and named in this project's own design document
(docs/specs/2026-08-11-media-tools-design.md, day one). See
knowledge/store/a-directive-is-a-decision-not-a-suggestion.md.

WHAT THIS IS NOT FOR: the living layer. Card cutting and swinging stay in
hinge-foliage.py, whose gust envelope and `--under hold` double-layer are
MEASURED verdicts on this painting and are not reproduced by any generic tool.
This script consumes their output as image sequences on planes.
"""
import argparse, json, math, sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument('--layers', required=True, help='dir holding layers.json + layers/')
p.add_argument('--geometry', help='per-plane tiltX/tiltY, as render-parallax reads')
p.add_argument('--out', required=True)
p.add_argument('--frames', type=int, default=1)
p.add_argument('--width', type=int, default=1920)
p.add_argument('--height', type=int, default=1080)
p.add_argument('--fov', type=float, default=1.0,
               help='zoom multiplier, matching render-parallax: 1.0 = the '
                    'framing that fits the output width, higher = tighter')
p.add_argument('--z-step', type=float, default=0.30,
               help='world units between adjacent depth indices. The ONE number '
                    'that decides how much parallax a dolly produces.')
p.add_argument('--dolly', type=float, default=0.0,
               help='world units the camera travels toward the stack over the '
                    'shot. render-parallax measured THE-RISE at 5.5% of stack '
                    'depth, which is why it read as a zoom.')
p.add_argument('--save', help='also write a .blend for opening in the GUI')
a = p.parse_args(argv)

LD = Path(a.layers)
man = json.loads((LD / 'layers.json').read_text())
W_SRC, H_SRC = man['size']
geom = json.loads(Path(a.geometry).read_text()) if a.geometry else {}

# --- clean scene ------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = a.width, a.height
sc.render.film_transparent = False
ENGINES = {e.identifier for e in
           bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items}
sc.render.engine = ('BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in ENGINES
                    else 'BLENDER_EEVEE')
sc.render.image_settings.file_format = 'PNG'

# --- the camera distance, needed BEFORE the planes so they can be fitted ------
# fov 1.0 = the framing that fits the output width, matching render-parallax.
# A plane of half-width 1.0 fills a 36mm sensor at D = lens / (sensor_width/2).
LENS, SENSOR = 50.0, 36.0
CAM_BACK = (LENS / (SENSOR / 2.0)) / max(a.fov, 1e-6)

# --- the planes -------------------------------------------------------------
# One image plane per cut layer, spaced along -Y by its depth index.
#
# EACH LAYER PNG IS CROPPED TO ITS OWN BBOX, NOT THE FULL PLATE. Measured
# 2026-08-25 on z3w: the plate is 2815x3368 and the seven layers are 217x345 up
# to 2815x3368. `offset` in layers.json is the PNG's top-left within the plate,
# which is exactly what render-parallax.py:293 reads as (ox, oy). Treating them
# all as full-plate planes stretches a 538px tree across the whole painting —
# which is what the first two renders did.
by_name = {q['name']: q for q in man['planeList']}
files = sorted((LD / 'layers').glob('*.png'))
depths = [by_name[f.stem.split('-', 1)[1]]['depth'] for f in files
          if f.stem.split('-', 1)[1] in by_name]
dmin, dmax = min(depths), max(depths)
aspect = H_SRC / W_SRC
UPP = 2.0 / W_SRC            # world units per plate pixel: the plate is 2.0 wide
built = []

for f in files:
    name = f.stem.split('-', 1)[1]
    if name not in by_name:
        print(f'  skip (not in manifest): {f.name}', file=sys.stderr)
        continue
    rec = by_name[name]
    d = rec['depth']
    img = bpy.data.images.load(str(f.resolve()))
    pw, ph = img.size
    ox, oy = rec.get('offset', [0, 0])

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = (math.radians(90), 0, 0)      # face the camera down +Y

    y = (dmax - d) * a.z_step
    # PLANE FIT — the thing that makes a multiplane a multiplane. A distant plane
    # subtends a smaller angle, so left at unit scale it renders inset with black
    # around it and frame zero does not match the painting. Disney solved this
    # physically: distant artwork was painted LARGER. Scale each plane AND its
    # offset from the axis by its own distance ratio, and every plane subtends
    # the same angle AT REST; parallax then emerges only when the camera moves,
    # which is the whole point.
    fit = (CAM_BACK + y) / CAM_BACK

    ob.scale = (pw * UPP * fit, ph * UPP * fit, 1.0)
    cx = (ox + pw / 2.0) - W_SRC / 2.0        # plate px, from plate centre
    cy = (oy + ph / 2.0) - H_SRC / 2.0        # +y is DOWN in image space
    ob.location = (cx * UPP * fit, y, -cy * UPP * fit)

    g = geom.get(name, {})
    if g:
        # tiltX/tiltY are per-pixel slopes in render-parallax; as an ORIENTED
        # PLANE they become real rotations, which is what makes a plane turn as
        # you pass it. knowledge: corner-pin is not rx/ry.
        ob.rotation_euler.x += math.atan(g.get('tiltY', 0.0) * H_SRC)
        ob.rotation_euler.z += math.atan(g.get('tiltX', 0.0) * W_SRC)

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
    tex.interpolation = 'Cubic'
    emit = nt.nodes.new('ShaderNodeEmission')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    outn = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(tex.outputs['Color'], emit.inputs['Color'])
    nt.links.new(tex.outputs['Alpha'], mix.inputs['Fac'])
    nt.links.new(tr.outputs['BSDF'], mix.inputs[1])
    nt.links.new(emit.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], outn.inputs['Surface'])
    ob.data.materials.append(mat)
    built.append((name, d, ob.location.y, pw, ph))

built.sort(key=lambda t: t[2])
stack_depth = (dmax - dmin) * a.z_step
print(f'planes: {len(built)}   depth index {dmin}-{dmax}   '
      f'stack depth {stack_depth:.2f} world units', file=sys.stderr)
for n, d, y, pw, ph in built:
    print(f'   y={y:6.2f}  depth {d:3d}  {pw:5d}x{ph:<5d} {n}', file=sys.stderr)

# --- camera -----------------------------------------------------------------
cam_data = bpy.data.cameras.new('cam')
cam_data.lens = LENS
cam_data.sensor_width = SENSOR
cam = bpy.data.objects.new('cam', cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
# FRAME THE NEAREST PLANE BY WIDTH, matching render-parallax's convention that
# fov 1.0 = "the framing that fits the output width". A plane of half-width 1.0
# fills the sensor at distance D = half_width * lens / (sensor_width / 2).
# Getting this wrong is not subtle: the first run used D = sensor/lens = 0.72
# and framed a few hundred source pixels, magnified to mush.
cam_data.sensor_fit = 'HORIZONTAL'
back = -CAM_BACK
cam.location = (0.0, back, 0.0)
cam.rotation_euler = (math.radians(90), 0, 0)

sc.frame_start, sc.frame_end = 1, max(1, a.frames)
if a.dolly and a.frames > 1:
    cam.location.y = back
    cam.keyframe_insert('location', frame=1)
    cam.location.y = back + a.dolly
    cam.keyframe_insert('location', frame=a.frames)
    pct = 100.0 * abs(a.dolly) / stack_depth if stack_depth else 0.0
    print(f'dolly: {a.dolly:.2f} world units = {pct:.1f}% of stack depth '
          f'(THE-RISE measured 5.5%, which read as a zoom)', file=sys.stderr)

out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
sc.render.filepath = str(out / 'f')
if a.save:
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.save).resolve()))
    print(f'scene: {a.save}', file=sys.stderr)
bpy.ops.render.render(animation=a.frames > 1, write_still=a.frames == 1)
print(f'rendered -> {out}', file=sys.stderr)
