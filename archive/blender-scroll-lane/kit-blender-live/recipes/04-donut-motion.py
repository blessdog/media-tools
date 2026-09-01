"""DONUT STAGE 4 -- animate it and render an actual video file.

    tools/blender-live.py --timeout 900 exec --file <this> --no-shot

Proves the last link: a live scene goes to a finished mp4 on disk without a
human touching Blender. Squash-and-stretch, not a camera orbit -- a camera move
over a static object is the corner being cut (CLAUDE.md, MOTION BEFORE CAMERA).
"""
import bpy, math

donut = bpy.data.objects['donut']

if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
for n in ('icing', 'sprinkles'):
    bpy.data.objects[n].hide_set(False)

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        sp = area.spaces.active
        sp.shading.type = 'RENDERED'
        sp.overlay.show_overlays = False
        sp.region_3d.view_perspective = 'CAMERA'

sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 96
sc.render.fps = 24

donut.animation_data_clear()
BASE_Z, SQUASH = 0.0, 0.82   # 0.82 is the dough squash already baked into scale

def key(frame, z, sx, sz):
    donut.location.z = z
    donut.scale = (sx, sx, sz)
    donut.keyframe_insert('location', index=2, frame=frame)
    donut.keyframe_insert('scale', frame=frame)

# two bounces: fall, splat, rise, fall, splat, settle. The splat frames carry
# the squash -- a bounce with no deformation reads as a floating ball.
key(1,  1.30, 0.97, SQUASH * 1.06)
key(14, 0.00, 1.06, SQUASH * 0.80)
key(15, 0.00, 1.07, SQUASH * 0.78)
key(30, 0.85, 0.98, SQUASH * 1.04)
key(46, 0.00, 1.05, SQUASH * 0.84)
key(60, 0.45, 0.99, SQUASH * 1.02)
key(74, 0.00, 1.02, SQUASH * 0.92)
key(84, 0.12, 1.00, SQUASH * 1.00)
key(96, 0.00, 1.00, SQUASH)

# a slow turn underneath the bounce so every side of the sprinkling is seen
donut.rotation_euler.z = 0.0
donut.keyframe_insert('rotation_euler', index=2, frame=1)
donut.rotation_euler.z = math.radians(150)
donut.keyframe_insert('rotation_euler', index=2, frame=96)

sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.resolution_percentage = 100
# Blender 5.0 put video behind a media_type switch: FFMPEG is not even IN the
# file_format enum until media_type is VIDEO, so the obvious 4.x line fails with
# a confusing "enum FFMPEG not found" listing only still-image formats.
sc.render.image_settings.media_type = 'VIDEO'
sc.render.image_settings.file_format = 'FFMPEG'
sc.render.ffmpeg.format = 'MPEG4'
sc.render.ffmpeg.codec = 'H264'
sc.render.ffmpeg.constant_rate_factor = 'HIGH'
sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
sc.render.filepath = '/Users/SSDrive/projects/media-tools/jobs/blender-live/evidence/2026-08-26-donut-bounce.mp4'
sc.render.engine = 'BLENDER_EEVEE'

print(f'rendering {sc.frame_end} frames at {sc.render.resolution_x}x{sc.render.resolution_y} ...')
bpy.ops.render.render(animation=True)
print('done ->', sc.render.filepath)
