---
id: naming-a-substance-requests-footage
kind: law
conflict-key: how-should-a-motion-prompt-be-written
status: live
supersedes: []
verified-on: 2026-08-14
asked-as:
  - the video model made it photographic
  - i2v prompt for a painting
  - the style collapsed in the video
  - how do I prompt a motion model
---

**Naming a physical substance in a motion prompt requests FOOTAGE of it.** Write
"water" and the model's prior for that word is photographic video of water, so
it renders photographic water over your painting and the style collapses.

The working recipe: **camera-only positive**, cfg 2–3, 73 frames. A masked crop
MAY name the substance, because the mask confines the damage to a region that is
already that substance. Full recipe in `jobs/wang-meng/NEXT-SESSION.md`.

This is a statement about the model's PRIOR, not about prompt wording, which is
why it transfers: any word whose training distribution is dominated by
photography will drag a stylised frame toward photography.

Migrated from `STATE.md` LAW 5.
