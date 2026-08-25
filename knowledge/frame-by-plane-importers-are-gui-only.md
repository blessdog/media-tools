---
id: frame-by-plane-importers-are-gui-only
kind: verdict
conflict-key: can-frame-by-plane-build-a-multiplane-headless
status: live
supersedes: []
verified-on: 2026-08-25
scope: >
  Frame By Plane 7.1.18 (macos_arm64) on Blender 5.2.1 LTS, measured in
  `--background` mode. Says nothing about the add-on in the GUI, where the
  importers are the RIGHT tool and should be used.
evidence:
  - tools/blender-multiplane.py
asked-as:
  - can Frame By Plane import headless
  - does the add-on work in background mode
  - can I script the Procreate import
  - is blender-multiplane.py redundant
  - why is fbp.import_folder_multiplane not found
---

## Frame By Plane registers 63 of its 353 operators headless, and no importers

Measured 2026-08-25 on Blender 5.2.1 LTS, `--background`:

```
FBP operator CLASSES defined in Python : 353
FBP operators registered with RNA      :  63
importers among them                   :   0
```

`fbp.import_folder_multiplane`, `import_procreate`, `import_psd`,
`import_sequence` and `import_folder_hierarchy` all exist as Python classes and
all raise `AttributeError: ... could not be found` when called.
`hasattr(bpy.ops.fbp, name)` returns **True** for them, which is why this reads
as a bug and is not — `bpy.ops` attribute access is lazy and does not prove
registration. The registry check is:

    [n for n in dir(bpy.types) if n.startswith('FBP_OT')]

The add-on gates its file-browser operators on having a UI, which is reasonable:
they are built around a preflight/detect pass whose results are shown to a
person before the import commits.

## What follows — a division of labour, not a winner

| half | tool |
|---|---|
| AUTHORING — a person cutting bushels, arranging depth | **Frame By Plane, in the GUI.** Drag a `.procreate` or `.psd` in; layers and transparency preserved. Do not rebuild it — [[search-before-you-build]]. |
| HEADLESS RENDER — a pipeline building a scene from a manifest | `tools/blender-multiplane.py`. A render pipeline cannot open a window. |

**This is why `blender-multiplane.py` was kept.** It was written expecting to be
deleted the moment the add-on was installed — the honest default under
[[installed-is-a-cost-not-a-reason]] — and it survived a real test rather than
an argument.

## Trap for the next session

A first pass listed 63 operators via `dir(bpy.ops.fbp)` and concluded the add-on
was small. A second pass counted 353 via `bpy.types.Operator.__subclasses__()`
and concluded it was rich and scriptable. **Both counts were real and both
conclusions were wrong**, because they enumerate different things: Python classes
versus RNA registrations. Only the second matters for "can I call it", and only
in the mode you will actually run in.
