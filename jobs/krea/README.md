# krea — a new lane, started 2026-08-12

**Nothing in here is inherited.** No bongpot swatch, no bongpot keyframes, no
`styles/inkwash/style.json`, no prompt strings from another project. That
pollution is what derailed the first half of today: a single approval from
June 2026, on a different project, got carried forward as canon and quietly
became the foundation for this one.

## The rule

**Approved means Ryan looked at it, in this lane, and said so.** Past approvals
belong to the project they were given for. Nothing else counts. Any asset that
arrives from elsewhere is labelled as a candidate from elsewhere, never as a
default.

No tool call in this lane passes `--style inkwash`. That flag silently loads
bongpot's swatch and prompt strings, and it is the mechanism that made
inheritance the path of least resistance.

## The architecture (Ryan, 2026-08-12)

Appearance and motion are separated. They are different models with different
jobs, and the style never has to survive a video model — it enters at the
keyframe and the video model follows it.

```
        APPEARANCE                        MOTION
             │                               │
      Krea 2 + ink LoRA                  Wan 2.2
             │                               │
             ▼                               ▼
      keyframe A ─────────────────────► I2V ──► clip
      keyframe B ─────► FLF2V ─────────────────► clip
                        (WanFirstLastFrameToVideo)
```

> **Krea = art director. Wan = cinematographer.**
> Krea decides what the world looks like. Wan decides how it moves through time.

First/last-frame conditioning is the stronger version: rather than asking a
video model to hold a style for five seconds, it is told exactly what the world
looks like at both ends and asked only to construct the trajectory between them.

## Migration path

Krea is the fast front end, not a dependency. The back half is already in the
inventory, so the same pipeline can go fully self-hosted without redesign:

```
TODAY   Krea 2 + LoRA        →  keyframes  →  Wan 2.2
LATER   USO / Qwen-Edit /    →  keyframes  →  Wan 2.2
        a LoRA trained on
        THIS lane's approvals
```

Krea 2 **raw** is the substrate for that last step — it is the control and
LoRA-training base, not a quality tier (Ryan, 2026-08-12). Turbo is what
generates; raw is what you fine-tune against and what control conditioning
targets.

## Experiments to compare

| | route | question it answers |
|---|---|---|
| A | Krea frame → Wan I2V | does a still hold its look once it moves? |
| B | real performance → Wan Animate → ink character | does motion transfer beat invented motion? |
| C | Krea frame A + frame B → Wan FLF2V | does bracketing both ends stop the drift? |
| D | ordinary video → restyle | is per-frame restyle ever competitive? |

## Layout

```
jobs/krea/
  README.md    this file — the lane definition
  prompts.md   drafted prompts, pending approval
  frames/      source frames Ryan provides
  renders/     output, each with its manifest
  approved/    EMPTY until Ryan puts something in it
```

`approved/` starts empty on purpose. It is the only place in this lane where
the word means anything.
