#!/usr/bin/env python3
"""Decide WHICH INK IS FOLIAGE with vision models instead of colour thresholds.

    segment-foliage.py --image plate.png --out foliage.png [--evidence sheet.png]

One job: produce a per-pixel FOLIAGE mask for a painting. It does not cut cards,
swing them, or judge motion -- hinge-foliage.py takes this via --leaf-mask and
decides WHICH pixels inside are painted mark.

WHY IT EXISTS. The colour gate (leaf-is-colour-rock-is-graphite) asks a SEMANTIC
question with a threshold, and at whole-plate scale it fails: run over all of
z1, 1,243 cards were cut and the rock swayed. Ryan, 2026-08-24: "unfortunately
the rock moves... we need a better way to id the foliage. there are ai models
that do this. you yourself know the dif. this is a solved problem." He is right,
and the architecture was already written down in refine-mask-sam.py -- a model
says WHAT, a boundary model says WHERE, signal work runs inside. Only the WHAT
was still a threshold.

TWO MODELS, BECAUSE THEY FAIL IN OPPOSITE DIRECTIONS. Measured on four z1 crops,
2026-08-24:

    crop                    Mask2Former/ADE   Grounding DINO
    trestle-bridge-ge       59.4% plant  OK   whole-crop box, useless
    gorge-wall-right        92.2% plant  OK   whole-crop box, useless
    foreground-rock-mass     0.0% plant  OK   tight box on the one fern  OK
    great-trees-knoll        0.0% plant  MISS box on the leafy half     OK

The dense model reads a MASS of canopy and is blind to sparse pale foliage; the
detector needs an object to box and cannot say anything useful when the crop is
90% leaves. Their union covers all four. The dense model's misses are
false NEGATIVES, which is the safe direction: less moves, rather than rock
moving.

NOT A REPLACEMENT FOR THE INK CUT. This says "there is foliage here", not "this
pixel is a painted mark". Both are needed -- the model's mask includes the bare
silk between the leaves.

Models: facebook/mask2former-swin-large-ade-semantic, IDEA-Research/grounding-dino-base.
Local, free, no API. Needs the torch venv -- see knowledge/sam-environment.md.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
import cv2
import torch
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

PLANT_WORDS = ("tree", "plant", "flower", "palm", "grass", "bush")
# 'streetlight' and 'kitchen island' contain 'light'/'island' and match naive
# substring lists; the words above are chosen so no ADE class is caught wrongly.
DINO_TEXT = "tree leaves. foliage. bushes. bare rock. cliff face. water. wooden bridge."
LEAFY = ("leaf", "leaves", "foliage", "bush", "tree")


def dense_plant(model, proc, dev, im, up):
    big = im.resize((im.width * up, im.height * up), Image.Resampling.LANCZOS)
    inp = proc(images=big, return_tensors="pt").to(dev)
    with torch.no_grad():
        out = model(**inp)
    seg = proc.post_process_semantic_segmentation(
        out, target_sizes=[(im.height, im.width)])[0].cpu().numpy()
    plant = {i for i, n in model.config.id2label.items()
             if any(w in n.lower() for w in PLANT_WORDS)}
    return np.isin(seg, list(plant))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tile", type=int, default=380, help="px of source per decode")
    ap.add_argument("--overlap", type=float, default=0.34)
    ap.add_argument("--up", type=int, default=2, help="upscale before the dense model")
    ap.add_argument("--dino-threshold", type=float, default=0.30)
    ap.add_argument("--no-dino", action="store_true")
    ap.add_argument("--device", default=None)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    dev = a.device or ("mps" if torch.backends.mps.is_available() else "cpu")
    from transformers import (AutoImageProcessor, Mask2FormerForUniversalSegmentation,
                              AutoProcessor, AutoModelForZeroShotObjectDetection)
    M = "facebook/mask2former-swin-large-ade-semantic"
    dproc = AutoImageProcessor.from_pretrained(M)
    dmodel = Mask2FormerForUniversalSegmentation.from_pretrained(M).to(dev).eval()
    gproc = gmodel = None
    if not a.no_dino:
        G = "IDEA-Research/grounding-dino-base"
        gproc = AutoProcessor.from_pretrained(G)
        gmodel = AutoModelForZeroShotObjectDetection.from_pretrained(G).to(dev).eval()

    src = Image.open(a.image).convert("RGB")
    W, H = src.size
    dense = np.zeros((H, W), np.uint16)
    seen = np.zeros((H, W), np.uint16)
    boxes = np.zeros((H, W), bool)
    step = max(1, int(a.tile * (1 - a.overlap)))
    xs = list(range(0, max(1, W - a.tile + 1), step)) + ([W - a.tile] if W > a.tile else [])
    ys = list(range(0, max(1, H - a.tile + 1), step)) + ([H - a.tile] if H > a.tile else [])
    xs, ys = sorted(set(max(0, x) for x in xs)), sorted(set(max(0, y) for y in ys))
    n = 0
    for y in ys:
        for x in xs:
            im = src.crop((x, y, min(W, x + a.tile), min(H, y + a.tile)))
            p = dense_plant(dmodel, dproc, dev, im, a.up)
            dense[y:y + p.shape[0], x:x + p.shape[1]] += p.astype(np.uint16)
            seen[y:y + p.shape[0], x:x + p.shape[1]] += 1
            if gmodel is not None:
                gi = gproc(images=im, text=DINO_TEXT, return_tensors="pt").to(dev)
                with torch.no_grad():
                    go = gmodel(**gi)
                res = gproc.post_process_grounded_object_detection(
                    go, gi.input_ids, threshold=a.dino_threshold,
                    text_threshold=a.dino_threshold,
                    target_sizes=[(im.height, im.width)])[0]
                for b, lbl in zip(res["boxes"], res["text_labels"]):
                    if not any(w in lbl for w in LEAFY):
                        continue
                    bx = [int(v) for v in b]
                    # A BOX COVERING ALMOST THE WHOLE TILE SAYS NOTHING. Measured
                    # 2026-08-24: on a crop that is 90% canopy the detector
                    # returns one tile-sized box, which would mark everything.
                    if (bx[2] - bx[0]) * (bx[3] - bx[1]) > 0.7 * im.width * im.height:
                        continue
                    boxes[y + max(0, bx[1]):y + bx[3], x + max(0, bx[0]):x + bx[2]] = True
            n += 1
            print(f"  tile {n}/{len(xs)*len(ys)}", file=sys.stderr, end="\r")
    print(file=sys.stderr)

    # A pixel is dense-plant if a MAJORITY of the tiles that saw it said so --
    # overlap is the vote, so one bad tile cannot paint a region.
    dense_mask = (dense.astype(np.float32) / np.maximum(seen, 1)) >= 0.5
    foliage = dense_mask | boxes
    foliage = cv2.morphologyEx(foliage.astype(np.uint8), cv2.MORPH_CLOSE,
                               cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
    Image.fromarray((foliage * 255).astype(np.uint8)).save(a.out)

    rep = {"tool": "segment-foliage", "image": a.image, "out": a.out,
           "size": [W, H], "tiles": n, "device": dev,
           "densePct": round(100.0 * dense_mask.mean(), 2),
           "dinoPct": round(100.0 * boxes.mean(), 2),
           "foliagePct": round(100.0 * foliage.mean(), 2),
           "dinoAddedPct": round(100.0 * (boxes & ~dense_mask).mean(), 2)}
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
