# kit: blender-live — building in a Blender that Ryan is watching

The live lane. Every recipe here runs against an ALREADY-OPEN Blender over a
socket, so the change lands in the viewport on Ryan's screen while he watches.
Headless batch work is not this kit — that is `tools/blender-multiplane.py` and
`tools/blender-mark-scene.py` under `Blender -b --python`.

## Connect

    tools/blender-live.py ping        # is anything listening on 9876
    tools/blender-live.py info        # what is in the scene right now
    tools/blender-live.py exec --file kits/blender-live/recipes/<x>.py
    tools/blender-live.py shot --out jobs/<job>/evidence/<name>.png
    tools/blender-live.py activity    # what RYAN just changed by hand

## ⛔ ONE SOCKET, POSSIBLY SEVERAL BLENDERS

Port 9876 is bound by whichever Blender started its server FIRST. On 2026-08-26
two were running — Ryan's storyboard file and a scratch instance — and every
script went to the one he could not see, because his was behind the browser.

**Before any destructive recipe, prove which Blender you are in:**

    lsof -nP -iTCP:9876 -sTCP:LISTEN     # the PID that owns the socket
    ps -Ao pid,etime,command | grep [B]lender

`recipes/_guard.py::assert_scratch()` is the mechanism, not the reminder: it
REFUSES to wipe a scene that has a saved filepath, grease pencil objects,
sequencer strips, or unsaved changes. Mark a genuine scratch scene explicitly:

    tools/blender-live.py exec --code "import bpy; bpy.context.scene['blender_live_scratch']=True"

## Recipes

| file | stage | teaches |
|---|---|---|
| `_guard.py` | — | refuse to wipe a scene holding real work |
| `01-donut-base.py` | torus, lumps, subsurf, camera, 2-point light | Displace+Clouds replaces the tutorial's proportional-edit drag, which has no script form |
| `02-donut-icing.py` | icing lifted off the surface, materials | bake the modifier stack (`evaluated_get` + `new_from_object`), cut with bmesh on a wobbling line |

## Measured traps, all found on 5.2.1

- **`action.fcurves` is gone** — actions are slotted. See
  `knowledge/blender-5x-broke-actions-and-eevee.md`.
- **`BLENDER_EEVEE_NEXT` is gone** — the enum is `BLENDER_EEVEE`.
- **Duplicating an object does not duplicate its shape.** A duplicate shares the
  modifier stack, so its verts are still the naked primitive. Cutting a copy
  follows the primitive, not the lumps on screen. Bake first.
- **Cut resolution must beat the wobble.** `new_from_object` evaluates at
  VIEWPORT subdivision; at level 2 a face was wider than the 0.055 wobble and the
  icing edge came out a staircase. Bake at 4, restore after.
- **Never shrinkwrap a dense mesh onto a coarser evaluated target.** Icing baked
  at subsurf 4 snapped onto `donut` at viewport subsurf 2 and quilted with
  concentric ridges and a dimple grid — invisible at 1200px, obvious full size.
  A mesh baked FROM a surface already conforms; offset along normals instead.
- **Screenshot at the size the defect lives at.** The quilting above survived a
  1200px capture and Ryan caught it in his own window. `--max-size 1600`.
