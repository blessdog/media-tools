---
id: registering-is-not-working
kind: law
conflict-key: how-do-i-know-a-blender-addon-actually-works-here
status: live
supersedes: []
verified-on: 2026-08-26
evidence:
  - tools/blender-live.py
asked-as:
  - does this blender addon work on our version
  - the addon installed fine but nothing happens
  - how do I evaluate a blender addon before adopting it
  - is this MCP server compatible
  - the addon registered so it should work right
---

## An addon that REGISTERS has proven only that its class definitions parse

Blender's `register()` binds operator and panel classes. It does not call a
single one of them, so every API break INSIDE a handler is invisible to it.
Measured twice in this repo, on two different add-ons:

- **Frame By Plane, 2026-08-25:** 63 of 353 operators registered headless and
  **zero importers** did — the importers were the only reason to want it.
- **RFingAdam/mcp-blender, 2026-08-26:** imports, registers and unregisters
  clean on 5.2.1. Its annotations handler then calls `scene.grease_pencil`,
  which **does not exist in 5.2.1** — an `AttributeError` on the first real use.

**The test that actually decides is: call the handler you came for.** Not the
one in the README's example. Pick the single capability that made the add-on
interesting and invoke it against real data. If that costs more than ten
minutes, the add-on is not cheap to adopt and that is itself the finding.

**And check the attribute, not the module.** The near-miss here: `bpy.data.
grease_pencils` and `bpy.data.materials.create_gpencil_data` DO still exist in
5.2, so a grep for "legacy GPv2 API" would have cleared this handler. The dead
attribute was `scene.grease_pencil`. Version notes describe releases; only
`hasattr` on this machine describes this machine.

Related: [[blender-5x-broke-actions-and-eevee]] (what broke),
[[frame-by-plane-importers-are-gui-only]] (the first time this was paid for),
[[the-environment-is-a-separate-memory]].
