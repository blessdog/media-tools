---
id: an-absence-is-invisible-in-the-output
kind: law
conflict-key: how-to-catch-a-shot-that-was-never-made
status: live
supersedes: []
asked-as:
  - why did nobody notice the missing shot
  - how do I check a camera plan before rendering
  - every render looks the same as the last one
  - is there an establishing shot in this film
  - how do I know the camera is actually moving
  - it feels like a robot looking at a painting
  - the parallax reads as a zoom
---

## You cannot see an absence by looking at the output

Ryan, 2026-08-22, from memory, about eleven days of renders that had all been
reviewed by watching them: *"There isn't even a full shot of the picture that
zooms in… it's always the same distance away from the painting, and you pan
slowly, and then move it pan. It's like if I were to program a robot how to look
at a painting, this would be it."*

Every one of those complaints was true, and every one was **invisible in the
footage**. A shot that never frames the whole subject looks completely fine on
its own. The omission does not exist in any frame — it exists only in the
aggregate over every path in the plan. No amount of looking finds it. Reading
the parameters finds it in one second.

**So: a camera plan is a claim about what will be on screen, and it is checkable
before anything renders.** `tools/check-camera-plan.py` is that check, and it
reproduced all four defects on the shipped film with no human hint:

| check | THE-RISE, measured 2026-08-22 |
|---|---|
| establishing shot exists | **FAIL** — widest view in the whole plan is 29.2% of the source width. A whole-painting shot needs fov 0.324 and was never authored once, in 34 paths |
| no dead axes | **FAIL** — `rx`, `ry`, `rz` are 0.000 in all five shipped legs |
| shots are distinct | **FAIL** — five legs, two envelopes. z1/z3w/z4w byte-identical at z 0..0.180, fov 1.0..1.613 |
| camera travels the scene | **FAIL** — the dolly covers **5.5% of a plane stack 3.30 deep**. The camera moves through a twentieth of the space it is standing in |

That last number is the whole diagnosis. It is not a taste failure and not a
vocabulary failure — `MOVES.md` already held every move Ryan named. **The camera
was at a fixed distance to within 5%, so every move it could make was a pan.**

### The three engines, so this is predictable rather than surprising

1. **A render is reviewed by watching it, and watching only ever shows the
   frame — never what is outside it.** The review method is structurally blind
   to the defect.
2. **Paths are GENERATED from a template.** `author-rise.py` reads
   `station-moves.json` and emits legs. Agreeing that a result is bad and then
   re-running the generator produces the same result, which is the loop Ryan
   named: *"I say to do something and it does the same thing over anyway."*
   The fix for that is structural (bible §8.4), never a promise to do better.
3. **A cap authored for one good reason becomes the rule for everything.**
   `light-parallax-is-011-and-continuous` set rotations under 0.08 because Ryan
   said "lightly and tastefully". That verdict was correct in its scope and then
   silently governed every shot in the film, including the ones that needed to
   move.

### The obligation

**Run `check-camera-plan.py` on the plan before rendering it, and again whenever
a plan is regenerated.** It reports rather than blocks
([[checks-start-in-observation]]); `--strict` makes it an error. A plan whose
widest shot never frames the subject is not a stylistic choice, it is a
missing shot.

The general form, for any medium: **when a defect is an absence, the artefact
cannot show it to you — only the parameters that produced the artefact can.**
