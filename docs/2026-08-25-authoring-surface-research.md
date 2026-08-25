# An authoring surface for cutout rigs — research

*2026-08-25. Report before build, per the working agreement. Nothing here is
built yet.*

## The problem, named as a practitioner would

Ryan: *"my eyes can easily define these bushels… I could tell you exactly what
trees and where the pivot points are, what parts of the bushel. That would fix
everything and it would take five minutes."*

He is describing **cutout rigging** — the Toon Boom / Moho / After Effects
Puppet-Pin workflow. An artist cuts a drawing into pieces and says where each
piece hinges. It has been done by hand for a century because "this spray of
leaves is one piece, and it swings from *here*" is a judgement, not a
measurement.

This project's own store reached the same conclusion from the other direction:
`no-whole-tree-to-segment` concluded a tree mask here "can only be AUTHORED."
Two more attempts on 2026-08-25 (a chroma classifier at 73.6%, a hue-displacement
classifier at 54.2% — worse than guessing) confirmed it a third time.

## Findings

| # | finding | status |
|---|---|---|
| 1 | The SAM on this disk is `facebook/sam-vit-huge` — **SAM 1, 2023**. Two generations behind. | VERIFIED (read from `tools/refine-mask-sam.py`, weights in `~/.cache/huggingface`) |
| 2 | **SAM 3** has shipped and beats SAM 2 on interactive image-segmentation mIoU. Adds **exemplar prompts**: mark two or three examples, it finds the rest that look like them. | REPORTED (Ultralytics docs, Meta AI blog) |
| 3 | SAM 3 weights are ~3.5GB at `facebook/sam3` on HuggingFace and are **gated** — Meta must approve the account. | REPORTED — needs a real download attempt to confirm |
| 4 | The base SAM 3 repo has a **Triton dependency that fails on M-series Macs**. Three workarounds exist: `mlx-community/sam3-image` (native Apple Silicon MLX port), `benreichman/sam3-mac` (shim), `MaximeLglr/sam3-apple-silicon`. | REPORTED — the MLX port is the one to try first and is UNTESTED here |
| 5 | SAM 3.1 Object Multiplex released 2026-03-27 (multi-object tracking; relevant later for video, not for this) | REPORTED |
| 6 | **Spine**'s JSON export is a public, documented, stable format: bones, slots, skins, mesh attachments with per-vertex weights. That is exactly "bushel bound to a hinge." | REPORTED (esotericsoftware.com/spine-json-format) |
| 7 | **Rive** exports a proprietary binary `.riv` and has **no JSON export**. Worse for a custom pipeline despite being the more modern editor. | REPORTED |
| 8 | Apple Pencil reaches a web page in iPad Safari through **Pointer Events**, pressure and tilt included. Known quirk: `pointermove` sampling can be coarser than `touchmove` on Safari, which matters for freehand strokes and not for taps. | REPORTED (Apple developer forums) |
| 9 | Browser SAM annotation is solved and shipping — Roboflow Smart Polygon, V7, Dataloop, Label Studio, PixLab. **None has a concept of a pivot**, and all are cloud dataset labellers. | VERIFIED by reading their docs |

## What nothing off the shelf does

A surface that, in one gesture loop: **taps a bushel → SAM lifts it → drops a
pivot on it → writes the result where the render pipeline reads it.**

The segmentation half is solved by SAM 3. The rigging half is solved by Spine's
schema. Neither half talks to the other, and neither runs on a pen surface
against a 105-megapixel painting sitting on this Mac.

## Proposed shape (NOT built, not approved)

- **Surface** — a web page served off this Mac. Trackpad works today; opening
  the same URL in iPad Safari upgrades the input to Apple Pencil for free. The
  software does not fork on hardware.
- **Engine** — SAM 3 via the MLX port, local. The image encoder runs once per
  tile; each tap decodes in milliseconds, which is what makes it feel like the
  iPhone lift-subject gesture.
- **Data model** — adopt **Spine's JSON skeleton schema** rather than inventing
  one. It is public, battle-tested, and means a rig authored here could later be
  opened in a real animation tool.
- **Consumer** — `hinge-foliage` stops cutting its own cards and reads the
  authored rig. That is the whole point: it currently shreds 147 cards out of a
  tree that should have ~19, and no parameter fixes a judgement.

## Open questions for Ryan

1. What pen surface exists today? (iPad + Pencil / iPad only / Mac only / none yet)
2. Is a gated HuggingFace approval acceptable, or should the fallback be SAM 2
   (ungated) with the option to upgrade?
