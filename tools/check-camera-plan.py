#!/usr/bin/env python3
"""media-tools — check-camera-plan: read camera paths, say what will be on
screen BEFORE anything renders. One job.

It renders nothing, opens nothing and fixes nothing. It reads the authored
path keys plus the source dimensions and answers questions you cannot answer by
watching the output.

WHY THIS EXISTS (2026-08-22, and it is a measured failure, not a precaution).
Eleven days of wang-meng renders were judged the only way anyone thought to
judge them — by watching them. Every shot looked defensible. Ryan then said, from
memory: "there isn't even a full shot of the picture that zooms in", "it's always
the same distance away from the painting", and "they were planned once and never
changed." All three were true, and all three were invisible in the footage:

  · fov 1.0 = native pixels, so the camera saw 1920px of a 6586px-wide painting
    = 29% of the width, and THE-RISE only ever narrowed, to 18%. Across all 35
    authored paths the widest view ever was 32.4%. A whole-painting shot needs
    fov 0.292 and was NEVER ONCE AUTHORED.
  · all five shipped legs had rx = ry = 0.000.
  · z1, z3w and z4w had byte-identical envelopes: z 0..0.180, fov 1.0..1.613.
    Five legs, one camera move.
  · the camera dollied 0.18 through a plane stack 3.3 deep — 5% of the space it
    was standing in.

THE MECHANISM, which is the transferable part: **an absence is invisible in the
output.** A shot that never shows the whole subject looks completely fine on its
own; the omission only exists in the aggregate over every path in the plan. No
amount of looking at frames finds it. Reading the parameters finds it in one
second, which is why this is a tool and not a review habit.

WHAT THIS IS NOT FOR, AND WHAT IS:

  probe-parallax.py   what a parallax move DOES to pixels, by rendering probes.
                      This tool never renders; it only reads intent.
  probe-zoom.py       whether a specific zoom holds up at a specific scale.
  contact-sheet.py    judging rendered loops by eye, N at once. The verdict
                      layer. This is the layer BEFORE the render exists.

usage:
  check-camera-plan.py --paths DIR [--source IMG] [--layers DIR]
                       [--z-step F] [--width N] [--min-coverage F] [--strict]

  --paths DIR      directory of camera-path JSONs (or a single .json file)
  --source IMG     THE IMAGE THE RENDERER IS ACTUALLY POINTED AT -- the plate
                   or stack source, not the master it was cut from. Getting
                   this wrong misreports coverage by the downsample factor;
                   it did on 2026-08-22, by 2.34x.
  --plate-json P   the crop-region sidecar (masterBox + masterPxPerRegionPx).
                   With it, coverage is ALSO reported against the true master,
                   which is the number that answers "is the whole subject ever
                   on screen".
  --layers DIR     a plane stack (layers.json) so dolly can be reported as a
                   FRACTION OF SCENE DEPTH, which is the number that says
                   whether the camera is really moving.
  --z-step F       must match what the renderer is called with (default 0.30)
  --width N        output width in px, to read fov as coverage (default 1920)
  --min-coverage F flag the plan if no shot ever frames this fraction of the
                   source width (default 0.90 — i.e. an establishing shot)
  --strict         exit 1 when any check fails. Default is exit 0 and REPORT;
                   see knowledge/checks-start-in-observation.md.

JSON on stdout. The readable report on stderr.

example:
  check-camera-plan.py --paths jobs/wang-meng/film/paths \
      --source corpus/grabs/wang-meng.png --layers jobs/wang-meng/journey/z1/layers-filled
"""
import argparse, glob, json, sys
from pathlib import Path

AXES = ("x", "y", "z", "fov", "rx", "ry", "rz")


def load_keys(path):
    d = json.loads(Path(path).read_text())
    keys = d.get("keys") or d.get("path")
    return (keys if isinstance(keys, list) else None), d


def envelope(keys):
    out = {}
    for a in AXES:
        v = [float(k.get(a, 1.0 if a == "fov" else 0.0) or 0.0) for k in keys if isinstance(k, dict)]
        out[a] = (min(v), max(v)) if v else (0.0, 0.0)
    return out


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--paths", required=True)
    ap.add_argument("--source")
    ap.add_argument("--plate-json")
    ap.add_argument("--layers")
    ap.add_argument("--z-step", type=float, default=0.30)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--min-coverage", type=float, default=0.90)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    p = Path(args.paths)
    files = sorted(glob.glob(str(p / "*.json"))) if p.is_dir() else [str(p)]
    files = [f for f in files if not Path(f).name.startswith("_")]
    if not files:
        print(f"no path files under {args.paths}", file=sys.stderr)
        return 2

    W_SRC = H_SRC = None
    if args.source:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        W_SRC, H_SRC = Image.open(args.source).size

    # The renderer is pointed at a PLATE; the subject is the master it was cut
    # from. Coverage against the wrong one is off by the downsample factor.
    k_master, W_MAST, H_MAST = None, None, None
    if args.plate_json:
        pj = json.loads(Path(args.plate_json).read_text())
        k_master = float(pj.get("masterPxPerRegionPx") or 1.0)
        box = pj.get("masterBox")
        if box:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = None
            try:
                W_MAST, H_MAST = Image.open(pj["master"]).size
            except Exception:
                W_MAST, H_MAST = box[2], box[3]

    depth_span = None
    if args.layers:
        lj = Path(args.layers)
        lj = lj / "layers.json" if lj.is_dir() else lj
        try:
            pl = json.loads(lj.read_text()).get("planeList") or []
            if len(pl) > 1:
                depth_span = (len(pl) - 1) * args.z_step
        except Exception as e:
            print(f"could not read plane stack: {e}", file=sys.stderr)

    plans, failures = [], []
    for f in files:
        keys, raw = load_keys(f)
        if not keys:
            continue
        env = envelope(keys)
        rec = {"file": Path(f).name, "keys": len(keys), "envelope": {a: list(v) for a, v in env.items()}}
        if W_SRC and env["fov"][0] > 0:
            vis_w = args.width / env["fov"][0]          # source px across at the WIDEST
            rec["widestFractionOfSource"] = min(1.0, vis_w / W_SRC)
            rec["narrowestFractionOfSource"] = min(1.0, (args.width / env["fov"][1]) / W_SRC)
            if k_master and W_MAST:
                rec["widestFractionOfMasterWidth"] = min(1.0, vis_w * k_master / W_MAST)
        if depth_span:
            rec["dollyFractionOfSceneDepth"] = (env["z"][1] - env["z"][0]) / depth_span
        plans.append(rec)

    # ---- checks over the WHOLE plan, which is where absences live ----
    report = {"paths": len(plans), "source": [W_SRC, H_SRC], "sceneDepthSpan": depth_span, "checks": []}

    def add(name, ok, detail):
        report["checks"].append({"check": name, "ok": ok, "detail": detail})
        if not ok:
            failures.append(name)

    if W_SRC:
        key = "widestFractionOfMasterWidth" if (k_master and W_MAST) else "widestFractionOfSource"
        against = f"master width ({W_MAST}px)" if key.endswith("MasterWidth") else f"source width ({W_SRC}px)"
        widest = max((r.get(key) or 0) for r in plans)
        who = max(plans, key=lambda r: r.get(key) or 0)["file"]
        denom = (W_MAST / k_master) if key.endswith("MasterWidth") else W_SRC
        add("establishing-shot-exists", widest >= args.min_coverage,
            f"widest view in the entire plan is {widest*100:.1f}% of the {against} "
            f"({who}); an establishing shot needs >= {args.min_coverage*100:.0f}%. "
            f"fov {args.width/(denom*args.min_coverage):.3f} would frame it.")

    dead = [a for a in AXES if all(abs(r["envelope"][a][1] - r["envelope"][a][0]) < 1e-9 for r in plans)]
    add("no-dead-axes", not dead, f"axes that NEVER vary in any path: {dead or 'none'}")

    seen = {}
    for r in plans:
        sig = tuple(round(x, 4) for a in ("z", "fov", "rx", "ry") for x in r["envelope"][a])
        seen.setdefault(sig, []).append(r["file"])
    dupes = {str(k): v for k, v in seen.items() if len(v) > 1}
    add("shots-are-distinct", not dupes,
        f"{len(dupes)} envelope(s) reused across paths: "
        + "; ".join(", ".join(v) for v in dupes.values()) if dupes else "every path has a distinct envelope")

    if depth_span:
        best = max((r.get("dollyFractionOfSceneDepth") or 0) for r in plans)
        add("camera-travels-the-scene", best >= 0.25,
            f"deepest dolly in the plan covers {best*100:.1f}% of a scene {depth_span:.2f} deep; "
            f"below ~25% the camera is at a fixed distance and the result reads as a zoom")

    report["plans"] = plans
    report["failed"] = failures
    print(json.dumps(report, indent=1))

    print(f"\n  CAMERA PLAN — {len(plans)} paths, source "
          f"{W_SRC}x{H_SRC}" + (f", scene depth {depth_span:.2f}" if depth_span else ""), file=sys.stderr)
    print("  " + "-" * 76, file=sys.stderr)
    for c in report["checks"]:
        print(f"  {'PASS' if c['ok'] else 'FAIL'}  {c['check']}\n        {c['detail']}", file=sys.stderr)
    print("  " + "-" * 76, file=sys.stderr)
    print(f"  {len(failures)} failed. Reporting only; --strict to make it an error.\n", file=sys.stderr)

    return 1 if (failures and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
