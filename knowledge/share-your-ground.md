---
id: share-your-ground
kind: law
conflict-key: what-depth-does-a-figure-get
status: live
supersedes: []
verified-on: 2026-08-16
asked-as:
  - what depth for a figure
  - the figure floats
  - people standing on a bridge depth
  - object at the wrong depth
---

**Every figure rides the depth of the surface that supports it.** The party on
the bridge sits one rung in front of the deck, not at its own estimated depth;
a deer on a path takes the path's depth; a boat takes the water's.

This is checkable as CODE, not as taste: for each figure, find the plane its
feet touch and assert its depth is that plane's depth plus one rung. A figure
that fails the assertion will float or shear when the camera moves — which is
exactly what `pin-objects.py` was written to fix, 18 shears to 0.

Migrated from `STATE.md` LAW 8. Related: [[depth-is-authored]].
