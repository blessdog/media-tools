#!/usr/bin/env python3
"""Interpret an image as an equirectangular panorama and render a forward view.

This is exactly what HY-World's split_panorama_image does: spherical UV -> pixel,
with u spanning 360 deg of longitude and v spanning 180 deg of latitude, over
whatever image it is handed. No aspect check anywhere in the path.

Run it on a real 2:1 panorama and on our 1:2.1 vertical scroll and compare. The
question is not "does it crash" (it does not) but "is the result meaningful".
"""
import sys
import numpy as np
from PIL import Image

def forward_view(pano, out_w=900, out_h=900, fov_deg=90.0, yaw_deg=0.0, pitch_deg=0.0):
    H, W = pano.shape[:2]
    f = (out_w / 2.0) / np.tan(np.radians(fov_deg) / 2.0)

    # pixel grid -> camera rays
    xs, ys = np.meshgrid(np.arange(out_w), np.arange(out_h))
    x = (xs - out_w / 2.0) / f
    y = (ys - out_h / 2.0) / f
    z = np.ones_like(x)
    d = np.stack([x, y, z], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)

    # yaw then pitch
    cy, sy = np.cos(np.radians(yaw_deg)), np.sin(np.radians(yaw_deg))
    cp, sp = np.cos(np.radians(pitch_deg)), np.sin(np.radians(pitch_deg))
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    d = d @ (Ry @ Rx).T

    # direction -> spherical uv -> source pixel
    lon = np.arctan2(d[..., 0], d[..., 2])          # -pi..pi
    lat = np.arcsin(np.clip(d[..., 1], -1, 1))      # -pi/2..pi/2
    u = (lon / (2 * np.pi) + 0.5) * W
    v = (lat / np.pi + 0.5) * H

    ui = np.clip(u.astype(int), 0, W - 1)
    vi = np.clip(v.astype(int), 0, H - 1)
    return pano[vi, ui]

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    pano = np.asarray(Image.open(src).convert("RGB"))
    h, w = pano.shape[:2]
    print(f"{src}: {w}x{h}  ratio {w/h:.3f}  (a valid equirect is exactly 2.000)")
    Image.fromarray(forward_view(pano)).save(dst)
    print(f"wrote {dst}")
