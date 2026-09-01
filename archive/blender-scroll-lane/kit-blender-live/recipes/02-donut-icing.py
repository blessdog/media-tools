"""DONUT STAGE 2 -- icing lifted off the donut's own surface, plus materials.

    tools/blender-live.py exec --file <this>

The tutorial does this by selecting top faces in edit mode and hitting Shift+D /
P. Both are mouse gestures. The script equivalent is to BAKE the modifier stack
(evaluated_get + new_from_object), which returns the lumpy subdivided surface as
real geometry, then delete the faces below a cut line with bmesh. The cut line
wobbles with angle so the icing DRIPS instead of terminating on a perfect ring.

WHY BAKE RATHER THAN DUPLICATE THE OBJECT: a duplicate shares the modifier
stack, so its verts are still the naked 512-vert torus and any cut would follow
the primitive, not the lumps you can see. The evaluated mesh is what is on
screen -- cut that.
"""
import bpy, bmesh, math

donut = bpy.data.objects['donut']

for stale in ('icing',):
    if stale in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[stale], do_unlink=True)

# --- bake the visible surface ----------------------------------------------
# new_from_object evaluates at VIEWPORT subdivision. At level 2 a face is wider
# than the wobble amplitude below, so the cut quantises to the quad grid and the
# icing edge comes out as a staircase. Bake denser than the viewport shows, then
# put the level back so Ryan's viewport stays fast.
sub = donut.modifiers['subsurf']
was = sub.levels
sub.levels = 4
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
me = bpy.data.meshes.new_from_object(donut.evaluated_get(dg))
sub.levels = was
icing = bpy.data.objects.new('icing', me)
bpy.context.collection.objects.link(icing)
icing.matrix_world = donut.matrix_world.copy()

# --- cut away everything below a wobbling line ------------------------------
bm = bmesh.new(); bm.from_mesh(me)
zs = [v.co.z for v in bm.verts]
z_lo, z_hi = min(zs), max(zs)

doomed = []
for f in bm.faces:
    c = f.calc_center_median()
    theta = math.atan2(c.y, c.x)
    # three overlapping harmonics -> an edge that never repeats around the ring
    wobble = (0.055 * math.sin(theta * 3.0)
              + 0.032 * math.sin(theta * 7.0 + 1.3)
              + 0.018 * math.sin(theta * 13.0 + 0.4))
    cut = z_lo + (z_hi - z_lo) * 0.52 + wobble
    if c.z < cut or f.normal.z < -0.15:
        doomed.append(f)
bmesh.ops.delete(bm, geom=doomed, context='FACES')
bm.to_mesh(me); bm.free()

# --- give it thickness and lift it clear of the dough -----------------------
sol = icing.modifiers.new('thickness', type='SOLIDIFY')
sol.thickness = 0.035
sol.offset = 1.0
# NO SHRINKWRAP. It was here and it was the bug: this mesh is baked at subsurf
# 4 (63k faces) while `donut` evaluates in the viewport at subsurf 2, so every
# dense icing vert snapped onto a coarser cage and quilted the surface with
# concentric ridges and a dimple grid -- clearly visible at full window size and
# invisible in a 1200px screenshot. The bake already conforms exactly to the
# surface it came from, so the correct offset is along the normals, not a
# re-projection: solidify with offset=1.0 pushes the shell outward on its own.

for ob in (icing,):
    ob.select_set(True)
bpy.context.view_layer.objects.active = icing
bpy.ops.object.shade_smooth()

# --- materials --------------------------------------------------------------
def principled(name, base, rough, subsurf=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*base, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    if 'Subsurface Weight' in bsdf.inputs:
        bsdf.inputs['Subsurface Weight'].default_value = subsurf
    return m

dough = principled('dough', (0.62, 0.38, 0.17), 0.72, 0.12)
glaze = principled('glaze', (0.93, 0.42, 0.58), 0.18, 0.25)
floor = principled('backdrop_mat', (0.28, 0.27, 0.30), 0.85)

donut.data.materials.clear(); donut.data.materials.append(dough)
icing.data.materials.clear(); icing.data.materials.append(glaze)
bd = bpy.data.objects['backdrop']
bd.data.materials.clear(); bd.data.materials.append(floor)

print(f"icing: {len(me.polygons)} faces kept, modifiers "
      f"{[m.name for m in icing.modifiers]}")
