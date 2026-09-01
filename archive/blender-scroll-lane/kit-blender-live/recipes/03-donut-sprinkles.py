"""DONUT STAGE 3 -- sprinkles, via geometry nodes.

    tools/blender-live.py exec --file <this>

The tutorial does this with a particle system and a hand-modelled sprinkle.
Geometry nodes is the modern route and the only one that is fully scriptable.

THE SHAPE OF THE GRAPH:
    Mesh (the icing) -> keep only upward-facing faces -> scatter points
      -> store a random colour on each point -> instance a little baton
      -> rotate each one randomly -> realize -> assign material -> out

WHY BUILD THE BATON WITH A CUBE NODE instead of instancing a hidden object:
an Object Info node needs a real source object living in the scene, which then
has to be hidden without being hidden so hard that the node stops seeing it.
GeometryNodeMeshCube has no such problem and keeps the whole graph self-
contained -- nothing to accidentally delete.

WHY STORE A COLOUR ATTRIBUTE rather than several materials: per-instance random
is destroyed by Realize Instances. Writing a named attribute on the POINTS
before instancing survives realization, and the shader reads it back with an
Attribute node. One material, many colours.
"""
import bpy

icing = bpy.data.objects['icing']

# ---------------------------------------------------------------------------
def sock(node, name, direction='inputs'):
    """Look a socket up by name and, on a miss, SAY WHAT THE NAMES ACTUALLY ARE.
    Geometry-node socket names drift between Blender versions and a bare KeyError
    from bpy tells you nothing about which node or which release moved."""
    coll = getattr(node, direction)
    if name in coll:
        return coll[name]
    raise RuntimeError(
        f"{node.bl_idname}: no {direction[:-1]} named {name!r}. "
        f"available: {[s.name for s in coll]}")


for stale in ('sprinkles',):
    if stale in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[stale], do_unlink=True)
if 'sprinkle_graph' in bpy.data.node_groups:
    bpy.data.node_groups.remove(bpy.data.node_groups['sprinkle_graph'])

# --- an object to carry the graph, sitting exactly on the icing -------------
me = bpy.data.meshes.new_from_object(
    icing.evaluated_get(bpy.context.evaluated_depsgraph_get()))
sprinkles = bpy.data.objects.new('sprinkles', me)
bpy.context.collection.objects.link(sprinkles)
sprinkles.matrix_world = icing.matrix_world.copy()

ng = bpy.data.node_groups.new('sprinkle_graph', 'GeometryNodeTree')
# Blender 4.0 replaced node_group.inputs/.outputs with the interface API.
ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

n = ng.nodes
lk = ng.links.new

g_in = n.new('NodeGroupInput');  g_in.location = (-900, 0)
g_out = n.new('NodeGroupOutput'); g_out.location = (900, 0)

# keep only faces whose normal points up -- no sprinkles on the underside
normal = n.new('GeometryNodeInputNormal');   normal.location = (-900, -240)
sep    = n.new('ShaderNodeSeparateXYZ');     sep.location    = (-720, -240)
cmp    = n.new('FunctionNodeCompare');       cmp.location    = (-560, -240)
cmp.data_type, cmp.operation = 'FLOAT', 'GREATER_THAN'
sock(cmp, 'B').default_value = 0.25

dist = n.new('GeometryNodeDistributePointsOnFaces'); dist.location = (-360, 0)
sock(dist, 'Density').default_value = 420.0
sock(dist, 'Seed').default_value = 7

# a random colour per point, stored so it survives Realize Instances
# Random RGB in a cube gives mostly PASTEL MUD: the corners of RGB space are
# the saturated colours and the bulk of the volume is near the grey diagonal.
# Randomise HUE only and pin saturation and value in the shader instead.
rnd_col = n.new('FunctionNodeRandomValue'); rnd_col.location = (-360, -320)
rnd_col.data_type = 'FLOAT'
sock(rnd_col, 'Min').default_value = 0.0
sock(rnd_col, 'Max').default_value = 1.0

store = n.new('GeometryNodeStoreNamedAttribute'); store.location = (-160, 0)
store.data_type, store.domain = 'FLOAT', 'POINT'
sock(store, 'Name').default_value = 'sprinkle_hue'

# Instances land ON the surface point, so a baton rotated freely puts half its
# length inside the icing and some of them vanish entirely. Push each point out
# along the surface normal by roughly half a baton first.
lift_scale = n.new('ShaderNodeVectorMath'); lift_scale.location = (-160, -560)
lift_scale.operation = 'SCALE'
sock(lift_scale, 'Scale').default_value = 0.019
setpos = n.new('GeometryNodeSetPosition'); setpos.location = (-40, -160)

# A cube reads as CONFETTI, not sprinkles -- Ryan, 2026-08-26: "they're a little
# bit cubicular". A real sprinkle is an extruded cylinder with a round section,
# so use one and shade it smooth; the silhouette is what sells it, not the size.
baton = n.new('GeometryNodeMeshCylinder'); baton.location = (-160, -420)
sock(baton, 'Vertices').default_value = 10
sock(baton, 'Radius').default_value = 0.0085
sock(baton, 'Depth').default_value = 0.055
smooth = n.new('GeometryNodeSetShadeSmooth'); smooth.location = (-40, -420)

inst = n.new('GeometryNodeInstanceOnPoints'); inst.location = (60, 0)

rnd_rot = n.new('FunctionNodeRandomValue'); rnd_rot.location = (60, -360)
rnd_rot.data_type = 'FLOAT_VECTOR'
sock(rnd_rot, 'Min').default_value = (-3.14159, -3.14159, -3.14159)
sock(rnd_rot, 'Max').default_value = (3.14159, 3.14159, 3.14159)
sock(rnd_rot, 'Seed').default_value = 11

rot = n.new('GeometryNodeRotateInstances'); rot.location = (300, 0)
real = n.new('GeometryNodeRealizeInstances'); real.location = (500, 0)
setmat = n.new('GeometryNodeSetMaterial'); setmat.location = (700, 0)

# --- the material: one shader, colour driven by the stored attribute --------
m = bpy.data.materials.get('sprinkle') or bpy.data.materials.new('sprinkle')
m.use_nodes = True
bsdf = m.node_tree.nodes['Principled BSDF']
bsdf.inputs['Roughness'].default_value = 0.35
attr = m.node_tree.nodes.new('ShaderNodeAttribute')
attr.attribute_name = 'sprinkle_hue'
attr.location = (-520, 0)
# ShaderNodeCombineHSV was folded into CombineColor(mode='HSV') in 4.x.
comb = m.node_tree.nodes.new('ShaderNodeCombineColor')
comb.mode = 'HSV'
comb.location = (-320, 0)
comb.inputs['Green'].default_value = 0.88   # saturation
comb.inputs['Blue'].default_value = 0.95    # value
m.node_tree.links.new(attr.outputs['Fac'], comb.inputs['Red'])   # Red == Hue
m.node_tree.links.new(comb.outputs['Color'], bsdf.inputs['Base Color'])
sock(setmat, 'Material').default_value = m

# --- wire it ----------------------------------------------------------------
lk(normal.outputs['Normal'], sep.inputs['Vector'])
lk(sep.outputs['Z'], sock(cmp, 'A'))
lk(g_in.outputs[0], sock(dist, 'Mesh'))
lk(cmp.outputs['Result'], sock(dist, 'Selection'))
lk(dist.outputs['Points'], sock(store, 'Geometry'))
lk(rnd_col.outputs['Value'], sock(store, 'Value'))
lk(dist.outputs['Normal'], sock(lift_scale, 'Vector'))
lk(lift_scale.outputs['Vector'], sock(setpos, 'Offset'))
lk(store.outputs['Geometry'], sock(setpos, 'Geometry'))
lk(setpos.outputs['Geometry'], sock(inst, 'Points'))
lk(baton.outputs['Mesh'], sock(smooth, 'Geometry'))
lk(smooth.outputs['Geometry'], sock(inst, 'Instance'))
lk(inst.outputs['Instances'], sock(rot, 'Instances'))
lk(rnd_rot.outputs['Value'], sock(rot, 'Rotation'))
lk(rot.outputs['Instances'], sock(real, 'Geometry'))
lk(real.outputs['Geometry'], sock(setmat, 'Geometry'))
lk(setmat.outputs['Geometry'], g_out.inputs[0])

mod = sprinkles.modifiers.new('sprinkle_graph', type='NODES')
mod.node_group = ng

dg = bpy.context.evaluated_depsgraph_get(); dg.update()
# Report verts only. The old line divided by 8 (cube verts) to guess a sprinkle
# count and silently became wrong the moment the baton became a 20-vert cylinder
# -- a derived number with no check on it is worse than no number.
count = len(sprinkles.evaluated_get(dg).data.vertices)
print(f'sprinkles: {count} verts realized')
