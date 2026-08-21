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
  - what camera moves do we have
  - ken burns push in
  - parallax peek around the tree
  - handheld float or breathing on a hold
---

## Ryan's list, and what each one is HERE

`render-parallax` keys carry x, y (master-normalised), z, fov, rx, ry per
time; anything in the "status" column marked PATH is authored purely in
those keys today. POST = done in ffmpeg/the edit, not the renderer. GAP =
not buildable yet; say so rather than fake it.

### Basic zoom / pan

| move | what it is | status | use here |
|---|---|---|---|
| **push in** | slow zoom toward the picture -- the classic Ken Burns | PATH: fov up | ARRIVALS only (the bridge, the hall). Ryan's complaint was this as identity |
| **pull out** | slow zoom away, revealing more | PATH: fov down | leaving a station; the reveal of how big the scroll is |
| **pan left/right** | slide sideways | PATH: x | a wide subject read edge to edge: the knoll, the gorge wall |
| **tilt up/down** | slide vertically | PATH: y | THIS PAINTING'S OWN MOVE -- a hanging scroll is read by tilting. Between stations |
| **diagonal drift** | slide on an angle | PATH: x+y | following a stream or a path that runs on a diagonal |
| **anchored zoom** | zoom locked on one point (a face) | PATH: fov up, x/y fixed on the subject | Ge Hong, the deer, a figure |
| **drifting anchor** | start centred, zoom while drifting to a point | PATH: fov up with x/y moving | the arrival at a detail inside a wide |
| **opposition move** | zoom one way, pan slightly the other -- a subtle dolly feel | PATH: fov up, x opposite | what LEG-LIGHT does by accident; use deliberately |

### How the motion feels

| move | what it is | status |
|---|---|---|
| **ease in/out (smoothstep)** | gentle start and end | BUILT IN: render-parallax samples piecewise smoothstep between keys (tools/render-parallax.py:125). Consequence: every key is a rest point -- a 3-key move slows at the middle key, so a continuous sweep wants 2 keys and a hold-move-hold wants 4 |
| **hold-move-hold** | sit, move, sit | PATH: repeat a key, then move, then repeat |
| **speed ramp** | accelerate or decelerate through the shot | PATH: uneven key spacing |

### Advanced / expressive

| move | what it is | status | note |
|---|---|---|---|
| **slow roll (dutch drift)** | tiny rotation of the frame over time | GAP: no roll axis in the keys (rx/ry tilt planes, they do not roll the frame) | a hanging scroll has a strong vertical; roll would read as the painting slipping. Probably never |
| **corner pin / perspective creep** | fake 3D by shifting corners | PATH: rx/ry do the real thing | we have real planes -- use parallax, not the fake |
| **parallax (2.5D)** | foreground and background at different speeds | PATH: z > 0 with x or ry -- the multiplane reveal | at most twice in the film. Spent more often it is the screensaver again |
| **handheld float** | small irregular wobble, off the rails | GAP: no noise source in the path | Disney's multiplane was on rails and so are we; the living layer is the life. Revisit if holds feel dead |
| **breathing** | tiny in-out zoom pulse, no travel | PATH: fov +1% and back | the only motion on a LONG hold |

### Optical effects layered on top

| effect | status | note |
|---|---|---|
| **rack focus** | GAP: renderer has no depth blur | the planes know their depth, so it is buildable; the 1930s look has none |
| **vignette pulse** | POST | ffmpeg vignette with a slow sine |
| **light sweep** | POST or GAP | a gradient drifting over silk -- try in post first |
| **grain / gate weave** | POST | an archival look; this film is a painting, not a print -- Ryan's call |

### Transitions between stations

| transition | status |
|---|---|
| **fade / dissolve / to black / to white** | POST (concat with xfade) |
| **smooth wipe left/right** | POST |
| **circle open** | POST |
| **reveal wipe** | POST -- uncovering a still gradually rather than cutting |

## Why a vocabulary and not a taste

Every path authored before 2026-08-21 was push / hold / pull-back, differing
only in speed and amplitude. Gentleness is not variety. Naming the moves is
what makes "the camera is repetitive" checkable: count the distinct entries
in the last five paths. The Old Mill (1937) and 2.5D documentary practice
both say the same thing: the hold is the default, parallax is for moments.
