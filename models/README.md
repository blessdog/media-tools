# models/ — the renderer catalog

One JSON per renderer. `shard-models` reads these; **no model recipe ever lives
in tool code** (CLAUDE.md rule 5, the same reason styles live in `styles/`).

Adding a model is dropping a file in here. No code change.

## MOST OF THIS CATALOG CANNOT RUN. Check before you plan around one.

A file in here is a **manifest** — weights, VRAM, card, params. It is not a
renderer. A renderer needs `builder` (a graph built in code) or a `graph` file
that actually exists in `tools/workflows/`. As of 2026-08-16 exactly **one of
eight** entries can render: `uso-inkwash`. The other seven carry
`"graphStatus": "NOT WRITTEN YET"` in their own file.

Run this before citing any model in a plan, and quote what it prints:

```sh
python3 - <<'PY'
import json, pathlib
wf = {p.name for p in pathlib.Path('tools/workflows').glob('*.json')}
for f in sorted(pathlib.Path('models').glob('*.json')):
    d = json.loads(f.read_text()); g = d.get('graph')
    ok = bool(d.get('builder')) or (g and pathlib.Path(g).name in wf)
    print(f"{d['id']:26} {'RUNNABLE' if ok else 'MANIFEST ONLY'}")
PY
```

**Why this section exists.** On 2026-08-16 a report recommended reaching for
Qwen-Image-Edit as "the ink-wash editor we already have, already proven." It is
not wired, the version cited was superseded, and the LoRA credited for the ink
look is a *panorama* adapter. The claim came from a memory of a session that had
rented a box and run it once — through `pipeline_with_qwen_image.py`, which
generates 360° panoramas and cannot be pointed at a masked hole. Acting on that
would have meant renting a box and pulling 28GB before discovering it.
**A memory is a claim about the past; only a file read is a claim about now.**

## Fields

| field | meaning |
|---|---|
| `id` | the key; must match the filename |
| `engine` | `comfy` today. The only engine `shard-models` drives. |
| `builder` | `uso` — graph built in code by `_uso.mjs`. Mutually exclusive with `graph`. |
| `graph` | repo-relative path to an API-format ComfyUI workflow JSON. |
| `inputs` | for `graph` models: where to inject image / prompt / seed. See below. |
| `graphStatus` | **required when `graph` names a file that does not exist yet.** Say `NOT WRITTEN YET` plainly. An entry without a runnable graph is a wish, and must read as one. |
| `vramGB` | **measured** peak VRAM. Drives card selection — get this wrong and the box offloads and crawls. If it is an estimate, say so in `vramNote` — several here are. |
| `gpu` | preferred Vast card name, passed to `gpu-box up --gpu`. |
| `weightsGB` | download size. Why `gpu-box` filters `inet_down>=500`. |
| `params` | renderer defaults (lora strength, guidance, steps, dims). |

## `inputs` for graph-based models

`shard-models` locates nodes by `class_type` rather than by id, so a workflow
re-export that renumbers nodes doesn't break the catalog:

```json
"inputs": {
  "image":  { "class": "LoadImage",      "field": "image" },
  "prompt": { "class": "CLIPTextEncode", "field": "text"  },
  "seed":   { "class": "KSampler",       "field": "seed"  }
}
```

Omit any key the model doesn't take.

## Getting `vramGB` right

Don't guess it. Render once, watch `nvidia-smi`, record the peak. A wrong
number here is the difference between a 40-second still and a five-minute one,
and it is silent — the render succeeds, it's just slow.

Same discipline as `tools/benchmarks.json`: measured numbers only.
