#!/usr/bin/env python3
"""media-tools — range-planes: painted figure sizes → plane distances. One job.

THE PAINTER IS THE RANGEFINDER. Wang Meng (and the tradition generally) paints
people and trees at near-constant real size, so painted height IS distance:
h ∝ 1/z. Measure a figure's pixel height on each plane and the planes' relative
depths fall out — photogrammetry read off the painting itself, no depth model.
The 14th century did the measuring.

TWO SCALES AT ONCE (measured on 葛稚川移居圖, 2026-08-17). Yuan painting sizes
protagonists by STATUS, not distance: Ge Hong measures 1.48x a servant standing
NEARER than him. So ratios only count WITHIN a class — servant vs servant,
tree vs tree. A mark with class "protagonist" is recorded but never calibrates.
First reading of the scroll (servant class, Z1 bank ≡ 1): cliff path z=2.02,
compound z=3.03 — the journey is spaced in clean multiples.

RESOLUTION LIMIT. Within one zone, figures are too close in depth for the
instrument: class height spread (~±10%) plus posture correction exceeds the
z separation. Use it ACROSS zones for the journey's global scale; author
within-zone spacing by eye.

Marks are authored by a human or an assistant LOOKING at gridded crops, never
by a model guessing. Heights in the px of the image the marks name.

usage:
  range-planes.py --marks marks.json --out scale.json

marks.json:
  { "image": "<path the heights were measured in>",
    "reference": "<mark name whose z becomes 1.0>",
    "marks": [ { "name": "...", "class": "servant|tree|protagonist|...",
                 "plane": "<plane or zone label>", "top": px, "bottom": px,
                 "factor": 1.0,   # posture: seated ≈ 0.53 of standing
                 "note": "..." } ] }

Output: per-plane z relative to the reference (median where several marks share
a plane), classes cross-linked only through planes they both mark. Classes with
no link to the reference class are reported unscaled, not silently merged.
"""
import argparse, json, statistics, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--marks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("-h", "--help", action="store_true")
    a = ap.parse_args()
    if a.help:
        print(__doc__)
        return 0

    M = json.loads(Path(a.marks).read_text())
    marks = M["marks"]
    ref_name = M["reference"]
    ref = next((m for m in marks if m["name"] == ref_name), None)
    if ref is None:
        print(f"reference mark '{ref_name}' not in marks", file=sys.stderr)
        return 1
    if ref["class"] == "protagonist":
        print("the reference cannot be a protagonist: hierarchical scale is "
              "status, not distance", file=sys.stderr)
        return 1

    def height(m):
        h = (m["bottom"] - m["top"]) / m.get("factor", 1.0)
        if h <= 0:
            raise ValueError(f"mark {m['name']}: bottom must be below top")
        return h

    h_ref = height(ref)
    calibrated, excluded = {}, []
    for m in marks:
        if m["class"] == "protagonist" or m["class"] != ref["class"]:
            excluded.append({"name": m["name"], "class": m["class"],
                             "heightPx": round(height(m), 1),
                             "why": "protagonist: status scale, not distance"
                             if m["class"] == "protagonist" else
                             f"class '{m['class']}' shares no plane with "
                             f"reference class '{ref['class']}'"})
            continue
        calibrated.setdefault(m["plane"], []).append(h_ref / height(m))

    planes = [{"plane": pl, "z": round(statistics.median(zs), 3),
               "marks": len(zs)} for pl, zs in calibrated.items()]
    planes.sort(key=lambda p: p["z"])

    out = {"tool": "range-planes", "image": M["image"],
           "reference": ref_name, "referenceClass": ref["class"],
           "referenceHeightPx": round(h_ref, 1),
           "planes": planes, "excluded": excluded,
           "law": "h ∝ 1/z within one class; protagonists are status-scaled "
                  "(Ge = 1.48x servant on this scroll) and never calibrate"}
    Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
