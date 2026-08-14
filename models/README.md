# models/ — the renderer catalog

One JSON per renderer. `shard-models` reads these; **no model recipe ever lives
in tool code** (CLAUDE.md rule 5, the same reason styles live in `styles/`).

Adding a model is dropping a file in here. No code change.

## Fields

| field | meaning |
|---|---|
| `id` | the key; must match the filename |
| `engine` | `comfy` today. The only engine `shard-models` drives. |
| `builder` | `uso` — graph built in code by `_uso.mjs`. Mutually exclusive with `graph`. |
| `graph` | repo-relative path to an API-format ComfyUI workflow JSON. |
| `inputs` | for `graph` models: where to inject image / prompt / seed. See below. |
| `vramGB` | **measured** peak VRAM. Drives card selection — get this wrong and the box offloads and crawls. |
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
