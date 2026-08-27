---
id: rendering-belongs-headless-not-in-the-live-session
kind: procedure
conflict-key: how-do-i-render-a-video-out-of-blender
status: live
supersedes: []
sibling: registering-is-not-working
verified-on: 2026-08-26
applies-when: >
  turning a Blender scene into an actual image or video file, whether the scene
  was authored live over the socket or built headless.
route: >
  Save the scene from the live session --
  bpy.ops.wm.save_as_mainfile(filepath=..., copy=True) -- then render in a
  SEPARATE process: /Applications/Blender.app/Contents/MacOS/Blender -b
  <file>.blend -a   (or -f N for one frame). Verify with ffprobe before
  believing it; a failed render still writes a 305-byte mp4.
route-also: >
  Before saving, set sc.render.use_sequencer = False. For video output on 5.x,
  set image_settings.media_type = 'VIDEO' BEFORE file_format = 'FFMPEG' --
  FFMPEG is not in the format enum until then.
not-when: >
  viewport screenshots. Those work fine live via
  tools/blender-live.py shot (GPUOffScreen) and are the right tool for checking
  work in progress. This claim is about FINISHED FILES.
evidence:
  - kits/blender-live/recipes/04-donut-motion.py
  - jobs/blender-live/evidence/donut-bounce.mp4
asked-as:
  - how do I render a video from blender
  - my blender render produced an empty file
  - blender says done but there is no output
  - render frame 15 executing compositor and nothing happens
  - why is my mp4 305 bytes
  - can I render from the live session
---

## Three silent failures in a row, each of which reported success

Measured 2026-08-26 while rendering the donut bounce.

1. **`bpy.ops.render.render(animation=True)` from the live socket returned
   instantly and rendered nothing.** The addon executes submitted code inside a
   `bpy.app.timers` callback, and render operators are inert there. It printed
   `done ->` over a 305-byte file. `write_still=True` for a single frame fails
   the same way — verified, the PNG never appeared.
2. **`-E CYCLES` on the command line did not take.** Setting the engine inside
   the .blend instead changed nothing, which was the clue that the engine was
   never the variable.
3. **The real cause: `scene.render.use_sequencer = True` with a sequence editor
   present.** Blender then renders the SEQUENCER's output — empty — instead of
   the 3D scene. 96 frames "rendered" in 1.2 seconds.

**The tell is a line that is ABSENT.** A working render logs
`Start rendering: Scene, ViewLayer`. The broken one went straight from
`Rendering frame N` to `Executing compositor`. Nothing in the output says
"error"; you have to notice a missing line, which is why
[[an-absence-is-invisible-in-the-output]] keeps being the expensive shape.

**The control is what actually solved it.** `Blender -b --factory-startup -f 1`
rendered a real 1.1MB PNG in 2.2s, which killed the mid-diagnosis theory that
EEVEE cannot render headless — it can — and narrowed the fault to the file in
one command. See [[null-before-the-metric]]: three guesses cost more than the
one control that ended the argument.

**Never accept a render's exit code as proof.** `ffprobe -v error
-show_entries stream=nb_frames` on the output, every time. A failed FFMPEG
render writes a valid, playable, empty 305-byte container.
