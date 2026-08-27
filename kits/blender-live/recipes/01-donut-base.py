"""DONUT STAGE 1 -- the torus and its irregular shape.

Run against a LIVE Blender:  tools/blender-live.py exec --file <this>

Blender Guru's tutorial deforms the torus by hand with proportional editing.
That is a mouse gesture and has no script form, so this uses a Displace modifier
driven by a Clouds texture -- the same irregularity, authored as a parameter
instead of a drag. Ryan can still grab verts by hand afterwards; the modifier
sits above the mesh and does not fight manual edits.
"""
import bpy, math, sys, importlib

# --- refuse to run in a scene that holds someone's work ---------------------
sys.path.insert(0, '/Users/SSDrive/projects/media-tools/kits/blender-live/recipes')
import _guard; importlib.reload(_guard)
_guard.assert_scratch()

# --- clean slate ------------------------------------------------------------
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.materials, bpy.data.textures, bpy.data.node_groups):
    for b in list(block):
        if b.users == 0:
            block.remove(b)

# --- the torus --------------------------------------------------------------
bpy.ops.mesh.primitive_torus_add(
    major_radius=1.0, minor_radius=0.38,
    major_segments=32, minor_segments=16,
    location=(0, 0, 0))
donut = bpy.context.active_object
donut.name = 'donut'
bpy.ops.object.shade_smooth()

# --- irregularity: clouds displace, then subdivide ---------------------------
tex = bpy.data.textures.new('donut_lumps', type='CLOUDS')
tex.noise_scale = 1.1
disp = donut.modifiers.new('lumps', type='DISPLACE')
disp.texture = tex
disp.strength = 0.16
disp.mid_level = 0.5

sub = donut.modifiers.new('subsurf', type='SUBSURF')
sub.levels = 2          # viewport
sub.render_levels = 3

# a touch of squash so it sits like dough rather than a maths primitive
donut.scale = (1.0, 1.0, 0.82)

# --- camera, key light, backdrop -------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.42))
bpy.context.active_object.name = 'backdrop'

bpy.ops.object.camera_add(location=(0, -3.1, 1.75), rotation=(math.radians(62), 0, 0))
cam = bpy.context.active_object
cam.data.lens = 62
bpy.context.scene.camera = cam

bpy.ops.object.light_add(type='AREA', location=(2.2, -2.4, 3.4))
key = bpy.context.active_object
key.data.energy = 420
key.data.size = 3.0
key.rotation_euler = (math.radians(38), 0, math.radians(42))

bpy.ops.object.light_add(type='AREA', location=(-2.8, -1.2, 1.6))
fill = bpy.context.active_object
fill.data.energy = 90
fill.data.size = 4.0
fill.rotation_euler = (math.radians(72), 0, math.radians(-58))

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
w = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.045, 0.045, 0.055, 1)

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        sp = area.spaces.active
        sp.shading.type = 'RENDERED'
        sp.region_3d.view_perspective = 'CAMERA'
        sp.overlay.show_overlays = False

print(f"donut: {len(donut.data.vertices)} verts, modifiers "
      f"{[m.name for m in donut.modifiers]}, engine {sc.render.engine}")
