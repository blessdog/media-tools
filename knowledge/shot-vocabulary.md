---
id: shot-vocabulary
kind: procedure
conflict-key: which-camera-move-for-a-station
status: live
supersedes:
  - the-camera-has-one-move-and-repeats-it
sibling: camera-light-parallax
applies-when: >
  authoring ANY camera path over the living layer. Ryan will not use these
  names -- he said so (2026-08-21: "I might not remember all of these
  vocabulary terms... they should be locked into your vocabulary. So if I
  describe something similar, you will understand"). So the job is to hear
  his description and name the move, then author THAT move and no other.
not-when: >
  the zone has no living layer -- then there is nothing for the camera to
  reveal and MOTION BEFORE CAMERA applies (compile-flight's LIVING GATE).
  And never as a menu to read back to him; the names are for the paths.
route: >
  One move per station, chosen from the table below, written into
  jobs/wang-meng/film/paths/<station>.json with "move" naming the entry.
  Consecutive stations never share a move unless the subject demands it. The
  zoom (push) is ONE entry, used for arrivals, never the default. Default is
  the HOLD. Render with film/render-leg.sh.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/film/TECHNIQUES.md
  - jobs/wang-meng/film/paths/leg-light-z3w.json
asked-as:
  - just hold still and let it breathe
  - move sideways along the cliff
  - go up the scroll like you are reading it
  - creep in slowly
  - same zigzag camera shot over and over
  - what camera moves do we have
  - peek around the tree
---

## The five moves, and how Ryan says them

| name | what the camera does | how he might describe it | use it for |
|---|---|---|---|
| **hold** | dead still. Only water, leaves, robes move. A hair of drift (fov or x ramp under 1%) is allowed to keep it alive, Disney-style | "just hold on it", "let it breathe", "don't move, let the water do it", "sit there" | the DEFAULT. Any station where the subject is the life itself: a fall, a pool, a canopy in a gust |
| **unroll** | a vertical rise (or descent) with NO zoom and NO rotation -- the way a hanging scroll is physically read | "go up the painting", "like reading it", "travel up", "scroll through it" | moving between stations; the whole 105MP set travelled. The move that is this painting's own |
| **track** | sideways at fixed depth along a cliff face or across a canopy; parallax felt laterally, near planes sliding past far ones | "slide across", "pan along the cliff", "go left to right", "move along the ridge" | a wide subject read edge to edge: the great-trees knoll, the gorge wall |
| **push** | a small z push with tiny rotation, one continuous direction (what LEG-LIGHT does). Depth FELT, never announced | "creep in", "drift in slowly", "come closer", "ease into it" | ARRIVALS only: the bridge, the hall. Ryan's complaint was this move as identity -- "same zigzag camera shot over and over" |
| **peek** | a lateral offset that lets a near plane cross in front of a far one, then settles -- the multiplane reveal | "look around it", "peek behind the tree", "show the depth", "3D moment" | once or twice in the whole film, where the narration lingers on a spatial detail. Spent more often it becomes the screensaver again |

## Why a vocabulary and not a taste

Every path authored before 2026-08-21 was push / hold / pull-back, differing
only in speed and amplitude. Gentleness is not variety (leg-light is leg-slow
made quieter). A twenty-minute film built from one gesture reads as a
screensaver however good the living layer is. Naming the moves is what makes
"the camera is repetitive" checkable: count the distinct entries in the last
five paths.

## Prior art this comes from

The Old Mill (Disney 1937): held scenes with effects animation, camera drift
on holds, multiplane for the few moments that earn it. 2.5D documentary
practice since 2002: reserve parallax for moments; most shots are flat with
LIFE, not depth moves. Both say the same thing -- the hold is the default.
