#!/usr/bin/env python3
"""Segment an image BY WHAT THINGS ARE, from words. Open-vocabulary, no thresholds.

    segment-semantic.py --image plate.png --prompts "tree foliage,bare rock cliff" --out DIR

Writes DIR/<slug>.png (one 0-255 confidence map per prompt), DIR/label.png (argmax
false-colour) and DIR/segment.json. A pixel belongs to the prompt with the highest
score, so the prompt LIST is the class set -- always give the classes you want to
EXCLUDE as well, or everything is weakly the one class you asked for.

WHAT THIS IS FOR: "which pixels are leaves and which are the rock behind them",
"where is the water", "which marks are a building". Questions about MEANING.

WHAT THIS IS NOT FOR:
  * exact object boundaries -- CLIPSeg decodes at 352px and is deliberately
    coarse. Pair it with SAM (tools/segment-points.py) when an edge must be
    pixel-exact, using this to CHOOSE which SAM masks to keep.
  * separating two things of the same kind (which tree a leaf spray belongs to).
    See knowledge/no-whole-tree-to-segment.md -- that is not a semantic question.
  * counting or locating small sparse marks; it is a dense classifier.

Model: CIDAS/clipseg-rd64-refined (150M). Runs on MPS/CPU, no GPU rental.
Needs the torch venv -- see knowledge/sam-environment.md.
"""
import argparse, json, re
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from transformers import CLIPSegProcessor, CLIPSegForImageSegmentation

p = argparse.ArgumentParser()
p.add_argument('--image', required=True)
p.add_argument('--prompts', required=True, help='comma-separated class names; include the ones to EXCLUDE')
p.add_argument('--out', required=True)
p.add_argument('--tile', type=int, default=352, help='px of the source covered by one decode; smaller = finer')
p.add_argument('--overlap', type=float, default=0.5)
p.add_argument('--model', default='CIDAS/clipseg-rd64-refined')
p.add_argument('--device', default='mps')
a = p.parse_args()

prompts = [s.strip() for s in a.prompts.split(',') if s.strip()]
img = Image.open(a.image).convert('RGB')
W, H = img.size
dev = a.device if (a.device != 'mps' or torch.backends.mps.is_available()) else 'cpu'
proc = CLIPSegProcessor.from_pretrained(a.model)
mod = CLIPSegForImageSegmentation.from_pretrained(a.model).to(dev).eval()

step = max(1, int(a.tile * (1 - a.overlap)))
acc = np.zeros((len(prompts), H, W), np.float32)
wgt = np.zeros((H, W), np.float32) + 1e-6
# a cosine window so tile seams do not print into the mask
wy = np.hanning(a.tile + 2)[1:-1]; win = np.outer(wy, wy).astype(np.float32)
xs = list(range(0, max(W - a.tile, 0) + 1, step)) or [0]
ys = list(range(0, max(H - a.tile, 0) + 1, step)) or [0]
if xs[-1] + a.tile < W: xs.append(W - a.tile)
if ys[-1] + a.tile < H: ys.append(H - a.tile)
with torch.no_grad():
    for y in ys:
        for x in xs:
            crop = img.crop((x, y, min(x + a.tile, W), min(y + a.tile, H)))
            cw, ch = crop.size
            inp = proc(text=prompts, images=[crop] * len(prompts), padding=True, return_tensors='pt').to(dev)
            logits = mod(**inp).logits
            if logits.ndim == 2: logits = logits[None]
            m = torch.sigmoid(logits).float().cpu().numpy()
            m = np.stack([np.array(Image.fromarray((c * 255).astype(np.uint8)).resize((cw, ch), Image.BILINEAR), np.float32) / 255 for c in m])
            w = win[:ch, :cw]
            acc[:, y:y + ch, x:x + cw] += m * w
            wgt[y:y + ch, x:x + cw] += w
prob = acc / wgt
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
slugs = [re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') for s in prompts]
for s, pr in zip(slugs, prob):
    Image.fromarray((pr * 255).astype(np.uint8)).save(out / f'{s}.png')
lab = prob.argmax(0)
palette = np.array([[40, 200, 60], [220, 60, 50], [60, 120, 230], [230, 200, 40], [200, 60, 220]], np.uint8)
Image.fromarray(palette[lab % len(palette)]).save(out / 'label.png')
meta = {'tool': 'segment-semantic', 'model': a.model, 'device': dev, 'image': a.image,
        'size': [W, H], 'tile': a.tile, 'overlap': a.overlap, 'tiles': len(xs) * len(ys),
        'classes': [{'prompt': pr, 'slug': s, 'winnerFraction': round(float((lab == i).mean()), 4),
                     'meanScore': round(float(prob[i].mean()), 4)} for i, (pr, s) in enumerate(zip(prompts, slugs))]}
(out / 'segment.json').write_text(json.dumps(meta, indent=1))
print(json.dumps(meta, indent=1))
