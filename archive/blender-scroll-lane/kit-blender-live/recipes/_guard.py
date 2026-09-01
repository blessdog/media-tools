"""Refuse to wipe a scene that has a human's work in it.

Every destructive recipe calls assert_scratch() FIRST. The failure this exists
to prevent is concrete and nearly happened on 2026-08-26: two Blender processes
were running, Ryan's storyboard file (Grease Pencil strokes, two sequencer
shots, Frame By Plane layers) and a scratch instance. The donut recipes open
with `select_all` + `delete`, and a one-line change of which socket they point
at would have destroyed the storyboard with no undo and no prompt.

A scene is SCRATCH only if it says so. Marking is explicit and deliberate:

    tools/blender-live.py exec --code "import bpy; bpy.context.scene['blender_live_scratch'] = True"
"""
import bpy


def assert_scratch(scene=None):
    scene = scene or bpy.context.scene
    if scene.get('blender_live_scratch'):
        return True

    reasons = []
    if bpy.data.filepath:
        reasons.append(f'file is saved as {bpy.data.filepath!r}')
    gp = [o.name for o in bpy.data.objects if o.type in {'GPENCIL', 'GREASEPENCIL'}]
    if gp:
        reasons.append(f'grease pencil objects present: {gp[:5]}')
    se = scene.sequence_editor
    if se:
        # Blender 5.0 renamed sequence_editor.sequences -> .strips
        strips = getattr(se, 'strips', None) or getattr(se, 'sequences', None) or []
        if len(strips):
            reasons.append(f'{len(strips)} sequencer strips present')
    if bpy.data.is_dirty:
        reasons.append('unsaved changes in this session')

    if reasons:
        raise RuntimeError(
            'REFUSING to wipe this scene -- it looks like real work: '
            + '; '.join(reasons)
            + ". If this really is a scratch scene, mark it: "
              "scene['blender_live_scratch'] = True"
        )
    return True
