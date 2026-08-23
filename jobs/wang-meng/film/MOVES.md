# The camera moves — Ryan's list, and what each costs to build

Reference table, extracted from `knowledge/shot-vocabulary.md` on 2026-08-21.
**The claim keeps the RULES; this file keeps the TABLE.** They were one file and
the mixing had a measured cost: at 780 indexed tokens the claim was nearly four
times the length of its neighbours, BM25 normalises by length, and it lost the
query *"what camera moves do we have"* — its own defining question — to two
shorter claims. Same failure as `foliage-motion` the same morning. See the
universal law `three-layers-claim-narrative-status`.

Ryan re-sent this list in full on 2026-08-21. Every move he named is below.

`render-parallax` keys carry x, y (master-normalised), z, fov, rx, ry per time.
**PATH** = authored purely in those keys today. **POST** = done in ffmpeg / the
edit, not the renderer. **GAP** = not buildable yet; say so rather than fake it.

**Run `tools/check-camera-plan.py` on a plan before rendering it** -- a move being
listed here is not evidence it was ever authored. Measured 2026-08-22: rx/ry/rz
were 0.000 in every leg of the shipped film.

**This is the complete set of camera moves available on this film**, in Ryan's
own names. He re-sent the whole list on 2026-08-21; every move he named is
already in the tables below, with what it costs to build here.


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
| **corner pin / perspective creep** | fake 3D by shifting corners | PATH: per-plane `tiltX`/`tiltY` in the geometry file do the real thing | **NOT rx/ry.** Corrected 2026-08-22: render-parallax's own docstring says rotation shares the centre of projection, so it adds NO new parallax -- it is the head turning, not moving. An ORIENTED PLANE is what turns as you pass it |
| **parallax (2.5D)** | foreground and background at different speeds | PATH: **z travel** against tilted planes -- the multiplane reveal | z must be a real fraction of the stack's depth. Measured 2026-08-22: THE-RISE dollied 5.5% of a 3.30-deep stack, which is why it read as a zoom. See `check-camera-plan.py` |
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
