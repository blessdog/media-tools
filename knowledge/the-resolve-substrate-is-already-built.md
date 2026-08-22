---
id: the-resolve-substrate-is-already-built
kind: verdict
conflict-key: what-exists-for-driving-davinci-resolve-from-an-agent
status: live
supersedes: []
scope: >
  Facts read off this machine on 2026-08-22. Applies to any plan that proposes
  building agent control of DaVinci Resolve, or that assumes Fusion cannot be
  scripted. Says nothing about whether Resolve's results are BETTER than the
  local Python tools -- that is untested.
verified-on: 2026-08-22
evidence:
  - /Library/Application Support/Blackmagic Design/DaVinci Resolve/.license/.davinciresolvestudio_14.0.lic
  - /Users/SSDrive/projects/mediaStudio/media-studio/.mcp.json
  - /Users/SSDrive/projects/mediaStudio/media-studio/studio/comp.py
  - /Users/SSDrive/projects/mediaStudio/media-studio/research-raw-claims.md
asked-as:
  - can an agent drive davinci resolve
  - do we have resolve studio
  - is fusion scriptable
  - should we build a resolve mcp
  - can claude build a fusion comp
  - do we need to buy resolve studio
---

## It exists, it is paid for, and it has been dormant since early August

Do not build any of this again. Measured 2026-08-22:

- **Resolve Studio is LICENSED** — `.davinciresolvestudio_14.0.lic`, dated
  11 Jul 2026. Resolve 21.0.4 installed, scripting API module present. This
  matters because **external scripting, and therefore ANY MCP, is Studio-only**;
  the free edition is console-only.
- **The MCP is vendored and wired** — `mediaStudio/media-studio/.mcp.json` points
  at `vendor/davinci-resolve-mcp` (samuelgursky): 34 compound / 341 granular
  tools, 336/336 API methods.
- **Fusion IS scriptable.** The "Fusion can't be automated" folklore is verified
  false: `safe_add_tool`, `safe_set_inputs`, `safe_connect_tools`,
  `probe_fusion_comp`, 18/18 probed operations supported against live Studio.
- **A `.comp` emitter with VERIFICATION already exists** — `studio/comp.py`
  writes the graph and `studio/fusion.py:live_manifest()` proves the graph that
  landed in Resolve is the graph that was meant. Emitting is the easy half;
  that equality check is the hard half and it is built and gated.

**The honest caveats**, from the vendor's own docs: heterogeneous and write-only
inputs, tool availability varies by build, UI refresh lag, renders are not
forced, per-effect semantic parameter coverage is thin.

**What is NOT known** and must be measured before any of it is chosen over the
local tools: whether Resolve's Depth Map and Magic Mask beat `estimate-depth`
and SAM on either a painting or a photo, and whether a Fusion `Camera3D` over
stacked `ImagePlane3D` beats `render-parallax`. Nobody has rendered that
comparison.
