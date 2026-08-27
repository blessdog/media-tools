# Blender MCP survey: which of these treat VISUAL FEEDBACK as architecture

**Date:** 2026-08-26 · **Asked by:** Ryan, who went looking specifically for
*"MCPs where visual feedback is an actual part of the architecture, rather than
just 'it can technically take a screenshot'"* — which is the right question and
is not the question I asked when I picked our bridge this morning.

## Verification status — read this column before believing any row

| repo | license | scale | Blender | status |
|---|---|---|---|---|
| **ahujasid/blender-mcp** (= `MCPBlender/blender-mcp`) | MIT | 26.3k★, 187 commits | claims 3.0+ | **ADOPTED · VERIFIED on 5.2.1** — registers clean, driven live all session |
| RFingAdam/mcp-blender | AGPL-3.0 | 13★, 39 commits | claims 4.2/5.0 | **VERIFIED registers · VERIFIED BROKEN**: annotations handler calls `scene.grease_pencil`, absent in 5.2.1 |
| mohit-mathur/cad-mcp-blender | MIT | 3★, 1 commit | 3.2–4.2+ | **UNVERIFIED** — README claims only |
| minihellboy/claude-blender | MIT | 4★, 10 commits | 4.0+, tested 4.3 | **UNVERIFIED** — README claims only |
| sandraschi/blender-mcp | MIT | 48+ tools | claims 3.0+ | **UNVERIFIED** — README claims only |
| owenpkent/blendmcp | MIT | fork of ahujasid | — | fork, "telemetry-free". Ours is already localhost-only (measured) |
| PatrykIti/blender-ai-mcp · 3DSceneAgent/blender-mcp-vision · ChrisWilliamson11/blender-assistant-mcp · naab007/blender_mcp | — | — | — | **NOT EXAMINED** |

**The star counts are the finding on the two most interesting repos.** 3 stars
/ 1 commit and 4 stars / 10 commits is not battle-tested code. Their VALUE IS
THE DESIGN, not the implementation — and a design is free to adopt.

## The four ideas worth taking

Ryan's framing is the load-bearing part: the difference between *"the agent CAN
screenshot"* and *"the agent CANNOT ACT WITHOUT SEEING"*. Ours is currently the
first. Every `shot` today is a thing I have to REMEMBER, and
`~/.claude/knowledge/store/a-manual-offer-is-a-missing-mechanism.md` says
exactly what that means: a discipline I have to remember is a mechanism I have
not built yet. Measured this session — the icing quilting survived my own
1200px capture and Ryan caught it in his window.

1. **Auto-capture on every mutation** (cad-mcp-blender: *"every modifying tool
   returns a viewport screenshot in the response, so Claude actually sees what
   it built"*). Take the choice away from me.
2. **Scene diff** (cad-mcp-blender: added / removed / modified objects after
   `execute_code`). A screenshot shows the camera's view; a diff catches what
   changed OFF camera. They fail in opposite directions, which is why both.
3. **Checkpoint before every exec** (both repos; cad saves a `.blend` first,
   claude-blender pushes an undo step). Our `_guard.py` refuses to wipe a scene
   that looks like work — a checkpoint is the same protection for the case the
   guard cannot see coming.
4. **Selection awareness** (cad-mcp-blender `cad_get_selection`: active object,
   selected objects, edit-mode vert/edge/face counts). **This is the biggest one
   and it is not really about CAD.** It is the pointing channel: Ryan selects a
   thing and I know which thing he means, with no sentence in between and no
   interpretation step to get wrong. That is the same problem
   `knowledge/marks-are-authored-in-blender.md` solves for regions with drawn
   strokes, reached from the other side.

## What is NOT worth taking

- **200+ tool wrappers.** Measured today: the whole donut — bmesh surgery,
  depsgraph baking, a seven-node geometry-nodes graph with a stored attribute —
  went through plain `execute_code`, first run, no socket-name misses. The
  wrappers are convenience, and the donut says we do not need the convenience.
- **A separate vision LLM** (ChrisWilliamson11). Splitting reasoning from
  perception adds a hop and a second model to keep in sync; I can already see
  the image in the same context that writes the next line of bpy.
- **Headless fallback** (sandraschi). We have that already and it is a different
  lane: `tools/blender-multiplane.py`, `tools/blender-mark-scene.py`.

## Decision

Implement all four in `tools/blender-live.py` — our own code, MIT-clean, no
AGPL entanglement, no swap of a working 26.3k-star addon for a 3-star one. The
addon we run already exposes everything needed: `get_scene_info`,
`get_viewport_screenshot`, `execute_code`, `drain_human_activity`. Points 1–4
are client-side discipline, which is precisely why they are cheap and precisely
why they were missing.
