---
id: sam-environment
kind: procedure
conflict-key: how-to-run-a-torch-tool-in-this-repo
status: live
supersedes: []
sibling: no-whole-tree-to-segment
applies-when: >
  any tool in this repo that imports torch -- segment-points.py,
  estimate-depth.py, stylize-frames.py, restyle-image on a local model. Run it
  with ~/.venvs/media-tools/bin/python, never bare python3.
not-when: >
  tools that are pure numpy/opencv/PIL. Those run on the system python3 and do
  not need the venv, and putting them in it costs nothing but confuses the
  reader about what actually has a dependency.
route: >
  ~/.venvs/media-tools/bin/python tools/<tool>.py ...
  Recreate with: python3 -m venv ~/.venvs/media-tools && ~/.venvs/media-tools/bin/pip
  install torch transformers numpy opencv-python-headless pillow
  Pins in requirements-sam.txt. Models are already in ~/.cache/huggingface
  (facebook/sam-vit-huge, depth-anything V2 Large) -- 4.1GB, nothing to download.
verified-on: 2026-08-20
evidence:
  - requirements-sam.txt
---

## Why this claim exists at all

Ryan, 2026-08-20: *"I thought we were already using SAM. Didn't we test that?
Exactly why I wanted to really update the back end. More work we've and
discoveries we've made that we keep having to rediscover over and over."*

He was right. SAM ran on this machine on 2026-08-13 and cut forty objects in
sixteen seconds, and `segment-points.py`'s docstring still records that finding
in detail. What had evaporated was not the knowledge — it was the ENVIRONMENT.
Python was upgraded to 3.14 and torch did not come with it, so a tool with a
working, documented, measured history reported `ModuleNotFoundError` and looked
like something that had never existed.

**A finding and its runtime are two different memories, and only one of them was
being written down.** See [[feedback_memory_is_not_capability]]: a memory of
running something once is not the same as it being wired.

## The one trap

`--system-site-packages` is WRONG here. Homebrew's numpy/opencv link against
Homebrew's `libomp` while torch ships its own, and two OpenMP runtimes in one
process abort with `OMP: Error #15` — which macOS surfaces as a "Python quit
unexpectedly" crash dialog, so it does not even read as a dependency problem.
Import order does not help. The venv must be ISOLATED and carry its own numpy,
opencv-python-headless and pillow.

Verified: torch 2.13.0, MPS available, cv2 5.0.0, numpy 2.5.2, SAM inference
9.7s on a 467x566 crop.
