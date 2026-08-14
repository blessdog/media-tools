#!/usr/bin/env python3
"""media-tools — estimate-depth: image → depth map. One job.

It produces a depth map and nothing else. It does not displace, warp, render a
camera move, or cut layers — those are separate tools, and a depth estimator
that starts moving cameras is a pipeline.

WHY THIS EXISTS (2026-08-13). The lane wants a camera moving through an ink
world without a video model re-deriving the medium 24 times a second. Under a
depth-driven parallax the medium CANNOT boil: every output frame is the same
painting resampled from a new angle, so the diffusion model runs once and the
ink is fixed texels from then on.

The open question this answers is narrow and real: monocular depth models are
trained on PHOTOGRAPHS, and a Yuan hanging scroll separates its planes by
convention and mist bands rather than by geometric perspective. So it may read
the space correctly, or it may flatten the washes into mush. One forward pass
settles it, and costs nothing.

MODEL SIZES AND THEIR LICENCES — read before shipping anything commercial:
  Small  24M   Apache-2.0        fine for anything
  Base   97M   CC-BY-NC-4.0      non-commercial
  Large  335M  CC-BY-NC-4.0      non-commercial
Large is the default because the first question is "can this be read at all",
and answering that with the weakest model would prove nothing. Ryan's own films
are fine under NC; a paid product is not.

Depth is RELATIVE and inverted: the model returns inverse depth, so bright =
near and dark = far. There is no metric scale and no absolute distance — for a
parallax displacement that is all you need, because only the ratios matter.

usage:
  estimate-depth.py --image IN [--out OUT.png] [--model large|base|small]
                    [--max-side N] [--raw OUT.npy] [--preview OUT.png]

  --image PATH     the picture
  --out PATH       depth map, 16-bit grayscale PNG (default: <image>-depth.png)
  --model NAME     large (default) | base | small, or any HF id
  --max-side N     downscale the long edge before inference (default 1536).
                   The model works at 518px internally regardless; this caps
                   the OUTPUT resolution and the memory a 105MP scan would
                   otherwise want.
  --raw PATH       also write the float32 array as .npy, for a displacement
                   step that should not re-quantise through 16-bit
  --preview PATH   also write a side-by-side image + depth, for the eyes
  --device NAME    mps (default on Apple Silicon) | cpu

JSON on stdout. Progress on stderr.

example:
  .venv/bin/python tools/estimate-depth.py \\
    --image corpus/grabs/wang-meng.png --preview /tmp/depth-check.png
"""

import argparse
import json
import sys
import time
from pathlib import Path

MODELS = {
    "small": ("depth-anything/Depth-Anything-V2-Small-hf", "Apache-2.0"),
    "base": ("depth-anything/Depth-Anything-V2-Base-hf", "CC-BY-NC-4.0"),
    "large": ("depth-anything/Depth-Anything-V2-Large-hf", "CC-BY-NC-4.0"),
}


def main() -> int:
    # --help is the contract and must exit 0 with no other arguments, so it is
    # answered before argparse gets a say about what is required.
    if "-h" in sys.argv[1:] or "--help" in sys.argv[1:] or len(sys.argv) == 1:
        print(__doc__)
        return 0

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--image", required=True)
    ap.add_argument("--out")
    ap.add_argument("--model", default="large")
    ap.add_argument("--max-side", type=int, default=1536)
    ap.add_argument("--raw")
    ap.add_argument("--preview")
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    src = Path(args.image)
    if not src.exists():
        print(f"no such image: {src}", file=sys.stderr)
        return 1

    import numpy as np
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    Image.MAX_IMAGE_PIXELS = None          # a 105MP museum scan is not a decompression bomb

    model_id, licence = MODELS.get(args.model, (args.model, "unknown"))
    device = args.device or ("mps" if torch.backends.mps.is_available() else "cpu")

    img = Image.open(src).convert("RGB")
    w0, h0 = img.size
    if max(img.size) > args.max_side:
        scale = args.max_side / max(img.size)
        img = img.resize((max(1, round(w0 * scale)), max(1, round(h0 * scale))), Image.Resampling.LANCZOS)
    w, h = img.size
    print(f"  {src.name}  {w0}x{h0} → {w}x{h}  model={args.model} ({licence})  device={device}",
          file=sys.stderr)

    t0 = time.time()
    processor = AutoImageProcessor.from_pretrained(model_id)
    model = AutoModelForDepthEstimation.from_pretrained(model_id).to(device).eval()
    t_load = time.time() - t0

    t0 = time.time()
    with torch.inference_mode():
        inputs = processor(images=img, return_tensors="pt").to(device)
        predicted = model(**inputs).predicted_depth
        # Back to the image's own size: the model works at its internal
        # resolution and a depth map that does not line up with the pixels it
        # describes is useless for displacement.
        depth = torch.nn.functional.interpolate(
            predicted.unsqueeze(1), size=(h, w), mode="bicubic", align_corners=False
        ).squeeze().float().cpu().numpy()
    t_infer = time.time() - t0

    lo, hi = float(depth.min()), float(depth.max())
    norm = (depth - lo) / (hi - lo) if hi > lo else np.zeros_like(depth)

    out = Path(args.out) if args.out else src.with_name(src.stem + "-depth.png")
    Image.fromarray((norm * 65535).astype(np.uint16), mode="I;16").save(out)
    if args.raw:
        np.save(args.raw, depth.astype(np.float32))
    if args.preview:
        vis = Image.fromarray((norm * 255).astype(np.uint8), mode="L").convert("RGB")
        pair = Image.new("RGB", (w * 2 + 24, h), (18, 18, 18))
        pair.paste(img, (0, 0))
        pair.paste(vis, (w + 24, 0))
        pair.save(args.preview)

    # A depth map that is nearly flat is the failure this whole test is looking
    # for, and it is not obvious by eye on a pale painting. Say it in numbers:
    # spread is how much of the range is actually used, and a low standard
    # deviation on a normalised map means the model found almost no relief.
    print(json.dumps({
        "tool": "estimate-depth",
        "image": str(src), "out": str(out), "raw": args.raw, "preview": args.preview,
        "model": model_id, "licence": licence, "device": device,
        "sourceSize": [w0, h0], "depthSize": [w, h],
        "range": [round(lo, 4), round(hi, 4)],
        "std": round(float(norm.std()), 4),
        "p05": round(float(np.percentile(norm, 5)), 4),
        "p95": round(float(np.percentile(norm, 95)), 4),
        "note": "inverse depth, relative: BRIGHT = near, DARK = far. No metric scale.",
        "loadSeconds": round(t_load, 1), "inferSeconds": round(t_infer, 1),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
