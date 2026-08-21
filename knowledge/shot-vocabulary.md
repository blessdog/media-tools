---
id: shot-vocabulary
kind: procedure
conflict-key: which-camera-move-for-a-station
status: live
supersedes:
  - the-camera-has-one-move-and-repeats-it
sibling: camera-light-parallax
applies-when: >
  authoring ANY camera path over the living layer, or hearing Ryan describe
  one. The names below are RYAN'S LIST (2026-08-21, given in full) and are
  the canonical vocabulary; he also said he will not remember them -- "they
  should be locked into your vocabulary. So if I describe something similar,
  you will understand" -- so the job is to hear his description, name the
  move from this table, and author THAT move.
not-when: >
  the zone has no living layer -- then there is nothing for the camera to
  reveal and MOTION BEFORE CAMERA applies (compile-flight's LIVING GATE).
  And never as a menu read back to him; the names are for the paths.
route: >
  One move per station, written into jobs/wang-meng/film/station-moves.json
  (the SSOT), turned into paths/st-<zone>-<station>.json by
  film/author-stations.py, rendered by film/render-leg.sh. Consecutive
  stations never share a move. The HOLD is the default; push-in is for
  arrivals, never identity; parallax is spent at most twice in the film.
verified-on: 2026-08-21
evidence:
  - jobs/wang-meng/film/TECHNIQUES.md
  - jobs/wang-meng/film/station-moves.json
asked-as:
  - just hold still and let it breathe
  - pan left or right across the cliff
  - tilt up the scroll like you are reading it
  - creep in slowly
  - same zigzag camera shot over and over
  - list the named camera moves
  - what is this kind of shot called
  - ken burns push in
  - parallax peek around the tree
  - handheld float or breathing on a hold
---

## The rules, and where the table lives

**The complete list of camera moves is `jobs/wang-meng/film/MOVES.md`** — every
move Ryan named, with whether it is authored in the path (PATH), done in the
edit (POST), or not buildable yet (GAP). It is a reference table, deliberately
kept out of this claim so the claim stays findable.

**The job this claim describes.** Ryan gave the names and then said he will not
remember them: *"they should be locked into your vocabulary. So if I describe
something similar, you will understand."* So the work is: hear his description,
name the move from MOVES.md, and author THAT move. Never read the list back to
him as a menu.

**The rules that govern which move goes where:**

- ONE move per station, written into `film/station-moves.json` (the SSOT).
- Consecutive stations never share a move.
- The HOLD is the default. Push-in is for ARRIVALS, never as an identity.
- Parallax is spent at most twice in the whole film.
- A wide is not wasted time — backing out is what makes a push mean anything.

**What a move is pointed AT is a different question**, answered by
[[the-camera-moves-toward-motion]]: establish wide, then approach the thing that
moves.

## Why a vocabulary and not a taste

Every path authored before 2026-08-21 was push / hold / pull-back, differing
only in speed and amplitude. Gentleness is not variety. Naming the moves is
what makes "the camera is repetitive" checkable: count the distinct entries
in the last five paths. The Old Mill (1937) and 2.5D documentary practice
both say the same thing: the hold is the default, parallax is for moments.
