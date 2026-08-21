#!/usr/bin/env python3
"""Turn a COARSE proposal into an EXACT mask with SAM.

    refine-mask-sam.py --image plate.png --proposal semantic/green-and-orange-tree-leaves.png \
                       --out refined.png [--min-area 400] [--multimask]
    refine-mask-sam.py --image plate.png --boxes catalogue.json --out refined.png

The middle link of the perception chain (knowledge/perception-is-a-model-not-a-threshold.md):

    a model says WHAT and roughly where   segment-semantic.py / a VLM catalogue
    SAM says exactly WHERE                <- this tool
    signal work runs inside that region   hinge-foliage --from-ink, animate-strokes

WHAT THIS IS NOT FOR: deciding what a thing IS. SAM has no vocabulary -- it
returns the mask under a prompt and cannot tell a tree from the rock behind it.
Give it a proposal that is already labelled, or it will happily hand back the
cliff. See knowledge/no-whole-tree-to-segment.md for the failure of SAM POINTS
on this painting; boxes are a different prompt and are what this uses.

Model: facebook/sam-vit-huge, local. Needs the torch venv (knowledge/sam-environment.md).
"""
import argparse, json
from pathlib import Path
import numpy as np
import cv2
import torch
from PIL import Image
from transformers import SamModel, SamProcessor

p = argparse.ArgumentParser()
p.add_argument('--image', required=True)
p.add_argument('--proposal', help='grayscale confidence PNG; connected components above --thresh become boxes')
p.add_argument('--boxes', help='JSON with objects[].box normalised to the image, as written by a catalogue')
p.add_argument('--kinds', default='tree', help='comma-separated kinds to keep when reading --boxes')
p.add_argument('--out', required=True)
p.add_argument('--overlay', help='write a check picture: proposal vs refined')
p.add_argument('--thresh', type=int, default=128)
p.add_argument('--min-area', type=int, default=400, help='ignore proposal blobs smaller than this')
p.add_argument('--pad', type=int, default=6, help='px added to each box before prompting')
p.add_argument('--multimask', action='store_true', help='keep SAM\'s highest-scoring of three, not the single mask')
p.add_argument('--device', default='mps')
a = p.parse_args()

img = Image.open(a.image).convert('RGB')
W, H = img.size
boxes = []
if a.boxes:
    cat = json.loads(Path(a.boxes).read_text())
    want = {k.strip() for k in a.kinds.split(',')}
    for o in cat['objects']:
        if o.get('kind') in want:
            x0, y0, x1, y1 = o['box']
            boxes.append([x0 * W, y0 * H, x1 * W, y1 * H])
elif a.proposal:
    pr = np.array(Image.open(a.proposal).convert('L'))
    n, lab, st, _ = cv2.connectedComponentsWithStats((pr > a.thresh).astype(np.uint8), 8)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < a.min_area:
            continue
        x, y, w, h = st[i, :4]
        boxes.append([x, y, x + w, y + h])
else:
    raise SystemExit('need --proposal or --boxes')
boxes = [[max(0, b[0] - a.pad), max(0, b[1] - a.pad), min(W, b[2] + a.pad), min(H, b[3] + a.pad)] for b in boxes]
if not boxes:
    raise SystemExit('no boxes to refine')

dev = a.device if (a.device != 'mps' or torch.backends.mps.is_available()) else 'cpu'
proc = SamProcessor.from_pretrained('facebook/sam-vit-huge')
mod = SamModel.from_pretrained('facebook/sam-vit-huge').to(dev).eval()
union = np.zeros((H, W), bool)
per = []
with torch.no_grad():
    for b in boxes:
        inp = proc(img, input_boxes=[[b]], return_tensors='pt')
        # MPS has no float64. The processor emits box coords as double, so cast
        # on the way to the device rather than shipping the whole batch blindly.
        inp = inp.__class__({k: (v.to(dev, torch.float32) if v.dtype == torch.float64 else v.to(dev))
                             if hasattr(v, 'dtype') else v for k, v in inp.items()})
        out = mod(**inp, multimask_output=bool(a.multimask))
        masks = proc.image_processor.post_process_masks(
            out.pred_masks.cpu(), inp['original_sizes'].cpu(), inp['reshaped_input_sizes'].cpu())[0][0].numpy()
        scores = out.iou_scores.cpu().numpy().reshape(-1)
        k = int(scores.argmax()) if masks.ndim == 3 and masks.shape[0] > 1 else 0
        m = masks[k] if masks.ndim == 3 else masks
        # SAM asked with a box around a canopy sometimes answers with the CLIFF the
        # canopy sits on. A mask that fills its own prompt box is that failure, so
        # record the fill and let the caller drop it.
        area = float(m.sum()); boxarea = max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
        per.append({'box': [round(v) for v in b], 'area': int(area),
                    'fillOfBox': round(area / boxarea, 3), 'iou': round(float(scores[k]), 3)})
        union |= m
Image.fromarray((union * 255).astype(np.uint8)).save(a.out)
if a.overlay:
    src = np.array(img).astype(np.float32)
    o = src.copy()
    if a.proposal:
        pr = np.array(Image.open(a.proposal).convert('L')) > a.thresh
        o[pr] = o[pr] * 0.6 + np.array([255, 210, 40]) * 0.4
    o[union] = o[union] * 0.35 + np.array([40, 200, 60]) * 0.65
    d = np.concatenate([src, o], axis=1).astype(np.uint8)
    Path(a.overlay).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(d).save(a.overlay)
print(json.dumps({'tool': 'refine-mask-sam', 'image': a.image, 'boxes': len(boxes),
                  'unionPx': int(union.sum()), 'coverage': round(float(union.mean()), 4),
                  'device': dev, 'out': a.out, 'perBox': per[:20]}, indent=1))
