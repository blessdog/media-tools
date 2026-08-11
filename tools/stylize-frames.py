#!/usr/bin/env python3
"""media-tools — stylize-frames: deterministic ink-wash (shuimo) treatment, built as a Blender
compositor node group from bpy and run headless. This is the FINISHING layer for
everything: it styles real A-roll footage AND launders generated 3D b-roll into
the same painted look, frame-perfect and temporally stable (every frame gets the
identical node graph — no diffusion lottery, no boil).

Built for Blender 5.x, whose compositor is a node GROUP assigned to
scene.compositing_node_group, with node settings exposed as input SOCKETS
(menu/float) rather than node properties. The graph maps onto the wash recipe:
  MovieClip ─┬─ Blur ─ Glare(BLOOM) ─ Curves(tonal) ─ HueSat(desat) ─┐
             └─ Filter(SOBEL) ─ Invert ──────────────────────────────Mix(MULTIPLY ink) ─[paper Mix]─ GroupOut

Video-only out (H.264). Source audio is muxed back with ffmpeg afterward (Blender
drops it) — consistent with the project's audio law.

Usage (capital -P = run script; args after `--` go to this script):
  blender -b -P tools/stylize-frames.py -- INPUT.mov OUT.mp4
  blender -b -P tools/stylize-frames.py -- INPUT.mov OUT.mp4 --paper assets/paper.png
  blender -b -P tools/stylize-frames.py -- INPUT.mov OUT.mp4 --frames 150   # slice test
  blender -b -P tools/stylize-frames.py -- INPUT.mov OUT.mp4 --check        # build only
Mux audio back:
  ffmpeg -i OUT.mp4 -i INPUT.mov -c:v copy -map 0:v:0 -map 1:a:0 -shortest OUT_av.mp4
"""
import sys
import os

import bpy  # provided by Blender's embedded Python


def parse():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(a) < 2:
        print("usage: blender -b -P tools/stylize-frames.py -- INPUT OUTPUT [--paper P] "
              "[--no-paper] [--frames N] [--fps F] [--check] [--allow-degraded]",
              file=sys.stderr)
        sys.exit(2)

    def flag(name):
        # Value = the token after `name`, unless that token is itself a flag
        # (so `--frames --check` doesn't swallow `--check` as the frame count).
        if name in a:
            i = a.index(name) + 1
            if i < len(a) and not a[i].startswith("--"):
                return a[i]
        return None

    frames, fps = flag("--frames"), flag("--fps")
    return {
        "input": os.path.abspath(a[0]),
        "output": os.path.abspath(a[1]),
        "paper": flag("--paper"),
        "no_paper": "--no-paper" in a,
        "frames": int(frames) if frames else None,
        "fps": int(fps) if fps else None,
        "check": "--check" in a,
        # Render anyway when a knob won't apply. Off by default: a degraded
        # graph renders happily and looks wrong, which is the expensive failure.
        "allow_degraded": "--allow-degraded" in a,
        # Look knobs (2026-07-02, from the washed-out verdict): defaults = the
        # graph's original hardcoded values, so bare runs are unchanged.
        "ink": float(flag("--ink") or 0.7),        # contour-multiply mix factor
        "shadow": float(flag("--shadow") or 0.14), # shadow-crush target at input 0.30 (lower = blacker floor)
        "edge": float(flag("--edge") or 0.8),      # Sobel strength
    }


# Every knob this run failed to apply. A skipped knob is a SILENT LOOK CHANGE —
# the graph still builds, the render still succeeds, and the result is quietly
# not the treatment you designed. Two of these (Kuwahara 'Uniformity' as a float,
# Scale 'Type' as a 4.x enum identifier) hid here for a full session and cost the
# ink pass its painterly step. main() now refuses to render with any outstanding.
SKIPPED = []


def set_socket(node, name, value):
    """Set an input socket's default_value if that socket exists (5.x moved
    node options onto sockets; names/types occasionally shift between builds).

    Non-fatal here so the whole graph gets probed in one pass and you see EVERY
    break at once rather than one per re-run — but recorded in SKIPPED, which
    main() treats as a hard stop unless --allow-degraded is passed.
    """
    def fail(why):
        SKIPPED.append(f"{node.bl_idname}.{name} = {value!r}  —  {why}")

    s = node.inputs.get(name)
    if s is None:
        have = ", ".join(i.name for i in node.inputs)
        fail(f"no such socket (has: {have})")
        return
    try:
        s.default_value = value
        return
    except Exception as e:
        first = e
    # 5.x put many knobs on vector sockets; broadcast a scalar across the
    # socket's components (Blur 'Size' is a vector, etc.).
    try:
        cur = s.default_value
        n = len(cur)  # raises if scalar socket → falls through to the report
        s.default_value = tuple([value] * n) if isinstance(value, (int, float)) \
            else tuple(list(value)[:n] + [0.0] * (n - len(value)))
        return
    except Exception:
        pass
    # Blender's enum error names the legal values; keep the whole message.
    fail(f"socket type {s.type} rejected it — {type(first).__name__}: {first}")


def make_paper(w, h):
    """Generate a static cream rice-paper grain image (numpy, bundled with
    Blender). Same plate every frame → temporally stable. No external asset."""
    import numpy as np
    img = bpy.data.images.new("InkWashPaper", width=w, height=h, alpha=False)
    base = np.array([0.94, 0.90, 0.80])            # warm cream
    grain = (np.random.rand(h * w, 1) - 0.5) * 0.08
    fiber = (np.random.rand(h * w, 1) - 0.5) * 0.03
    rgb = np.clip(np.tile(base, (h * w, 1)) + grain + fiber, 0.0, 1.0)
    rgba = np.concatenate([rgb, np.ones((h * w, 1))], axis=1)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.pack()
    return img


def build_group(clip, paper_image, look=None):
    look = look or {}
    """Build the ink-wash compositor node group and return it."""
    ng = bpy.data.node_groups.new("InkWash", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    n = ng.nodes.new
    link = ng.links.new

    src = n("CompositorNodeMovieClip")
    src.clip = clip
    src.location = (-980, 0)

    # Kuwahara (anisotropic) = the painterly step: collapses photo detail into
    # flat brushstroke-like regions following local structure — the thing that
    # makes it read as PAINTED, not a graded photo.
    kuwa = n("CompositorNodeKuwahara")
    set_socket(kuwa, "Type", "Anisotropic")
    set_socket(kuwa, "Size", 9)
    set_socket(kuwa, "Sharpness", 0.4)
    set_socket(kuwa, "Uniformity", 6)     # INT socket in 5.x — 6.0 raises TypeError
    kuwa.location = (-820, 0)
    link(src.outputs["Image"], kuwa.inputs["Image"])

    # --- tonal / paint path ----------------------------------------------
    blur = n("CompositorNodeBlur")
    set_socket(blur, "Size", 2.0)          # light soften — keep the ink crisp (vector socket)
    blur.location = (-680, 140)
    link(kuwa.outputs["Image"], blur.inputs["Image"])

    glare = n("CompositorNodeGlare")
    set_socket(glare, "Type", "Bloom")     # 5.x menu sockets take title-case labels
    set_socket(glare, "Threshold", 0.85)   # only the brightest blooms — subtle wet glow
    set_socket(glare, "Strength", 0.15)
    glare.location = (-460, 140)
    link(blur.outputs["Image"], glare.inputs["Image"])

    hsv = n("CompositorNodeHueSat")        # full monochrome (one color accent comes later)
    set_socket(hsv, "Saturation", 0.0)
    hsv.location = (-240, 140)
    link(glare.outputs["Image"], hsv.inputs["Image"])

    curves = n("CompositorNodeCurveRGB")   # hard contrast: blow mids→paper-white, hold ink dark
    curves.location = (-20, 140)
    try:
        c = curves.mapping.curves[3]       # [3] = combined 'C' channel
        c.points[0].location = (0.0, 0.0)  # true black ink
        c.points[1].location = (1.0, 1.0)
        c.points.new(0.30, look.get("shadow", 0.14))  # crush shadows (--shadow)
        c.points.new(0.62, 0.92)           # push upper-mids toward bare paper
        curves.mapping.update()
    except Exception as e:                 # mapping API drift
        SKIPPED.append(f"CompositorNodeCurveRGB (tonal) — {type(e).__name__}: {e}")
    link(hsv.outputs["Image"], curves.inputs["Image"])

    # --- ink-line path: bold dark contour lines --------------------------
    edges = n("CompositorNodeFilter")
    set_socket(edges, "Type", "Sobel")
    set_socket(edges, "Factor", look.get("edge", 0.8))
    edges.location = (-460, -240)
    link(hsv.outputs["Image"], edges.inputs["Image"])   # edges off the MONO signal → no color fringe

    ecurve = n("CompositorNodeCurveRGB")   # threshold the edges so faint ones vanish, real ones go solid
    ecurve.location = (-240, -240)
    try:
        ec = ecurve.mapping.curves[3]
        ec.points[0].location = (0.0, 0.0)
        ec.points[1].location = (1.0, 1.0)
        ec.points.new(0.22, 0.0)           # kill noise floor (speckle on skin/tattoos)
        ec.points.new(0.50, 0.85)          # softer snap than before
        ecurve.mapping.update()
    except Exception as e:
        SKIPPED.append(f"CompositorNodeCurveRGB (edge) — {type(e).__name__}: {e}")
    link(edges.outputs["Image"], ecurve.inputs["Image"])

    eblur = n("CompositorNodeBlur")        # soften the contour so it bleeds like wet ink, not a hard trace
    set_socket(eblur, "Size", 1.5)
    eblur.location = (-100, -240)
    link(ecurve.outputs["Image"], eblur.inputs["Image"])

    inv = n("CompositorNodeInvert")        # bright edges on black → dark ink on light
    inv.location = (60, -240)
    link(eblur.outputs["Image"], inv.inputs["Color"])

    # ShaderNodeMix(RGBA): Factor=inputs[0], A=inputs[6], B=inputs[7], Result=outputs[2]
    ink = n("ShaderNodeMix")
    ink.data_type = "RGBA"
    ink.blend_type = "MULTIPLY"
    ink.inputs[0].default_value = look.get("ink", 0.7)  # ink mix (--ink)
    ink.location = (240, 20)
    link(curves.outputs["Image"], ink.inputs[6])
    link(inv.outputs["Color"], ink.inputs[7])
    tail = ink.outputs[2]

    # --- paper-grain overlay (generated or supplied) ---------------------
    if paper_image is not None:
        pn = n("CompositorNodeImage"); pn.image = paper_image; pn.location = (240, -260)
        # 5.x menu socket takes the LABEL, not the 4.x enum identifier:
        # ('Relative', 'Absolute', 'Scene Size', 'Render Size'). "RENDER_SIZE"
        # silently fell through set_socket's except and the paper never scaled.
        sc = n("CompositorNodeScale"); set_socket(sc, "Type", "Render Size"); sc.location = (440, -260)
        link(pn.outputs["Image"], sc.inputs["Image"])
        pm = n("ShaderNodeMix"); pm.data_type = "RGBA"; pm.blend_type = "MULTIPLY"
        pm.inputs[0].default_value = 0.5; pm.location = (560, 20)
        link(tail, pm.inputs[6]); link(sc.outputs["Image"], pm.inputs[7])
        tail = pm.outputs[2]

    out = n("NodeGroupOutput")
    out.location = (820, 20)
    link(tail, out.inputs["Image"])
    return ng


def main():
    cfg = parse()
    if not os.path.exists(cfg["input"]):
        print(f"✗ input not found: {cfg['input']}", file=sys.stderr)
        sys.exit(1)

    scene = bpy.context.scene
    clip = bpy.data.movieclips.load(cfg["input"])
    w, h = clip.size
    fps = cfg["fps"] or int(round(getattr(clip, "fps", 0) or 30))
    n_frames = cfg["frames"] or clip.frame_duration

    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = n_frames

    if cfg["paper"]:
        paper_path = os.path.abspath(cfg["paper"])
        if not os.path.exists(paper_path):
            print(f"✗ paper not found: {paper_path}", file=sys.stderr)
            sys.exit(1)
        paper = bpy.data.images.load(paper_path)
    elif cfg["no_paper"]:
        paper = None
    else:
        paper = make_paper(w, h)           # generated cream paper by default
    scene.compositing_node_group = build_group(clip, paper, cfg)

    print(f"clip   : {cfg['input']}")
    print(f"size   : {w}x{h} @ {fps}fps")
    print(f"frames : {n_frames} (of {clip.frame_duration})")
    print(f"paper  : {cfg['paper'] or '(none)'}")
    ng = scene.compositing_node_group
    print(f"nodes  : {len(ng.nodes)}  links: {len(ng.links)}")

    if SKIPPED:
        print(f"\n✗ {len(SKIPPED)} knob(s) did not apply — this graph is NOT the "
              f"designed treatment:", file=sys.stderr)
        for s in SKIPPED:
            print(f"    · {s}", file=sys.stderr)
        if not cfg["allow_degraded"]:
            print("\nRefusing to render a degraded look. Fix the knob, or pass "
                  "--allow-degraded if you meant it.", file=sys.stderr)
            sys.exit(3)
        print("  (--allow-degraded: rendering anyway)", file=sys.stderr)
    else:
        print("knobs  : all applied ✓")

    if cfg["check"]:
        for nd in ng.nodes:
            print(f"   · {nd.bl_idname}")
        print("✓ graph built (dry run — no render).")
        return

    # This Blender build writes image sequences only (no FFMPEG container), so we
    # render PNG frames then encode + remux the original audio with system ffmpeg.
    frames_dir = cfg["output"] + ".frames"
    os.makedirs(frames_dir, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(frames_dir, "f_")
    print(f"rendering {n_frames} frame(s) → {frames_dir}")
    bpy.ops.render.render(animation=True)
    encode(frames_dir, cfg["input"], cfg["output"], fps, scene.frame_start)
    # Encode succeeded (it sys.exits otherwise, keeping frames for debug) — the
    # PNG sequence is large (hundreds of GB at 4K); don't let it accumulate.
    import shutil
    shutil.rmtree(frames_dir, ignore_errors=True)


def encode(frames_dir, src, out, fps, start):
    """PNG sequence → H.264 mp4, muxing the source's original audio back in."""
    import shutil
    import subprocess
    ff = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    cmd = [
        ff, "-y",
        "-framerate", str(fps),
        "-start_number", str(start),
        "-i", os.path.join(frames_dir, "f_%04d.png"),
        "-i", src,                              # original, for its audio track
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-map", "0:v:0", "-map", "1:a:0?",      # ? = audio optional (don't fail if silent)
        "-shortest", out,
    ]
    print("encoding:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-800:], file=sys.stderr)
        print(f"✗ ffmpeg failed ({r.returncode}); PNG frames kept in {frames_dir}", file=sys.stderr)
        sys.exit(1)
    print(f"✓ wrote {out}")


if __name__ == "__main__":
    main()
