---
id: blender-5x-broke-actions-and-eevee
kind: verdict
conflict-key: why-does-a-working-bpy-script-fail-on-blender-5
scope: >
  Blender 5.2.1 LTS on this Mac. Applies to EVERY bpy script in this repo and to
  any recipe copied from a tutorial, blog or model card written before 2026 --
  which is nearly all of them, because 4.x material is what search returns.
status: live
supersedes: []
verified-on: 2026-08-26
evidence:
  - tools/blender-live.py
  - jobs/blender-live/evidence/2026-08-26-first-live-viewport.png
asked-as:
  - action object has no attribute fcurves
  - why did my keyframe script break
  - BLENDER_EEVEE_NEXT not found in enum
  - how do I set the render engine to eevee
  - bpy script works in the tutorial but not here
  - how do I read keyframes out of an object
---

## Two renames in Blender 5.x will break almost any bpy recipe found online

Both hit within four minutes of the first live script on 2026-08-26, and both
produce a hard exception rather than a wrong result — which is the good case.

**1. Actions are SLOTTED. `action.fcurves` no longer exists.** Since 4.4 an
action holds layers, each layer holds strips, and the curves hang off a
*channelbag* keyed by the object's `animation_data.action_slot`. The shim:

```python
def fcurves_of(ob):
    ad = ob.animation_data
    act = ad.action
    if hasattr(act, 'fcurves'):          # <= 4.3
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            bag = strip.channelbag(ad.action_slot)
            if bag:
                out.extend(bag.fcurves)
    return out
```

`keyframe_insert()` is unchanged — only READING BACK and editing interpolation
break. So a script can appear to work (keyframes land, the object animates) and
fail only at the line that tidies the curves.

**2. `BLENDER_EEVEE_NEXT` is gone; the enum is `BLENDER_EEVEE` again.** EEVEE
Next was the 4.2-era transitional name. The live enum is exactly
`('BLENDER_EEVEE', 'BLENDER_WORKBENCH', 'CYCLES')`.

**Why this is a claim and not a footnote:** [[the-environment-is-a-separate-memory]].
The finding "my grid animation works" and the environment that produced it are
two memories, and only the second one transfers. Every future script here runs
on 5.2.1, so both shims are permanent, not incidents.

Related: [[frame-by-plane-importers-are-gui-only]] — the same class of problem
one level up, where an add-on registered but its importers did not.
