#!/usr/bin/env python3
"""Talk to a RUNNING Blender from the shell. The live half of the Blender lane.

    tools/blender-live.py ping
    tools/blender-live.py info
    tools/blender-live.py object --name Cube
    tools/blender-live.py exec --code "bpy.data.objects['Cube'].location.x += 2"
    tools/blender-live.py exec --file tools/scratch/move.py
    tools/blender-live.py shot --out jobs/<job>/evidence/<name>.png
    tools/blender-live.py activity

Blender must be OPEN with the blender-mcp addon enabled and its server started:

    /Applications/Blender.app/Contents/MacOS/Blender \
        --python-expr "import bpy; bpy.ops.preferences.addon_enable(module='blender_mcp_addon'); bpy.ops.blendermcp.start_server()"

PRIOR ART (searched 2026-08-26, per LAW #0 -- do not delete this block):

  · blender-mcp -- github.com/ahujasid/blender-mcp, MIT, 187 commits, active.
    ADOPTED. Its addon.py IS the server this file talks to; nothing about the
    in-Blender side is hand-rolled here. Claims "Blender 3.0+" and does NOT
    claim 5.x; MEASURED 2026-08-26 on 5.2.1 LTS: import, register and unregister
    all clean. Exposes get_scene_info, get_object_info, get_viewport_screenshot,
    execute_code and drain_human_activity over JSON-on-TCP at localhost:9876.
  · sandraschi/blender-mcp -- MIT, 48+ tools, VRM/Gaussian-splat/VSE breadth.
    Rejected for now: the extra 40 tools are for domains this repo does not
    have (avatars, splats), and breadth is surface area to break on 5.2.
    Revisit if the VSE tools would replace an ffmpeg assembly step.
  · RFingAdam/mcp-blender -- AGPL-3.0 (relicensed from MIT at v0.4.0), 218 tools,
    13,193 lines of handlers, 39 commits, last touched 2026-08-22. Brought by Ryan
    2026-08-26. MEASURED on 5.2.1: imports, registers and unregisters clean, and
    its compat.py independently handles the same slotted-action break found here
    -- so the 5.x work is real, not claimed. Genuinely deeper than the adopted
    addon where bpy is hardest to drive blind: mesh_editing 2632 lines, armature
    1253, measurement 966, baking 949, geonodes 807, sculpt 712, physics 490.
    NOT ADOPTED, for three measured reasons: (a) it has NO human-edit tracking,
    which is the whole point of the live lane -- reading back what Ryan did with
    the pen; (b) its annotations handler calls scene.grease_pencil, which does
    not exist in 5.2.1 (AttributeError), the register-but-do-not-work trap this
    repo already paid for once with Frame By Plane; (c) AGPL means its code
    cannot be copied into this repo without relicensing the repo. Same default
    port 9876 AND the same module name, so it is a SWAP, never an addition.
    Revisit as a second bridge on another port if rigging, physics or geometry
    nodes ever become the bottleneck.
  · djeada/blender-mcp-server -- MIT, 22 tools / 6 namespaces. Same shape,
    smaller, less active. No reason to prefer it over the one above.
  · Writing our own socket addon -- rejected. It is the same 3,651 lines and
    none of them would be ours to be good at. See bible 5.6.

WHY A CLI AND NOT THE MCP SERVER: the addon's transport is plain JSON over TCP,
so an MCP wrapper is optional. A CLI composes in scripts, needs no client
restart to change, and can be called by a human, by a Makefile, or by an agent
identically -- which is what SKILL.md 5.7 asks of every tool here. Wire the
MCP server too if a chat client ever needs it; both speak to the same socket.

WHAT THIS IS NOT FOR: headless batch work. Building a scene from a JSON spec
with no human watching is tools/blender-multiplane.py and
tools/blender-mark-scene.py, which run under `Blender -b --python` and need no
socket. THIS file exists only for the case where Ryan is LOOKING at the
viewport and the change has to land in the scene he is looking at.
"""
import argparse, base64, json, socket, sys
from pathlib import Path

DEFAULT_HOST, DEFAULT_PORT, TIMEOUT = 'localhost', 9876, 60.0


def send(cmd_type, params=None, host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=TIMEOUT):
    """One command, one response. The addon closes nothing, so read until the
    accumulated bytes parse as JSON -- a length prefix does not exist in this
    protocol and a single recv() truncates any screenshot."""
    s = socket.create_connection((host, port), timeout=timeout)
    s.settimeout(timeout)
    try:
        s.sendall(json.dumps({'type': cmd_type, 'params': params or {}}).encode())
        buf = b''
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode())
            except json.JSONDecodeError:
                continue
        raise SystemExit(f'connection closed with {len(buf)} bytes and no complete JSON')
    finally:
        s.close()


def unwrap(resp):
    """The addon answers {status, result} or {status, message}. Exit non-zero on
    error so this composes in `set -e` scripts instead of printing a failure
    that reads like a success."""
    if resp.get('status') != 'success':
        print(f"blender error: {resp.get('message', resp)}", file=sys.stderr)
        raise SystemExit(1)
    return resp.get('result')

# --- where things land ------------------------------------------------------
# jobs/** is gitignored except evidence dirs, so `shots/` and `checkpoints/`
# stay out of git by construction while `evidence/` is tracked. That is the
# split CLAUDE.md asks for: probes are scaffolding, cited visuals are memory.
REPO = Path(__file__).resolve().parent.parent
SHOT_DIR = REPO / 'jobs' / 'blender-live' / 'shots'
CKPT_DIR = REPO / 'jobs' / 'blender-live' / 'checkpoints'
KEEP_SHOTS = 24

SNAPSHOT_SRC = r"""
import bpy, json
dg = bpy.context.evaluated_depsgraph_get()
out = {}
for o in bpy.data.objects:
    try:
        verts = len(o.evaluated_get(dg).data.vertices)
    except Exception:
        verts = None
    md = o.data
    out[o.name] = {
        'type': o.type,
        'loc': [round(v, 5) for v in o.location],
        'rot': [round(v, 5) for v in o.rotation_euler],
        'scale': [round(v, 5) for v in o.scale],
        'mods': [m.name for m in o.modifiers],
        'mats': [m.name for m in md.materials] if getattr(md, 'materials', None) else [],
        'verts': verts,
        'parent': o.parent.name if o.parent else None,
    }
    # Lights and cameras carry their whole look in DATA, not in the transform.
    # Found the hard way 2026-08-26: a diff over transforms/modifiers/materials
    # reported "nothing changed" for a run that halved the key light and
    # repainted the glaze. A diff with a silent blind spot is worse than none,
    # because it reads as a clean bill of health.
    if o.type == 'LIGHT':
        out[o.name]['light'] = {'kind': md.type, 'energy': round(md.energy, 3),
                                'color': [round(c, 4) for c in md.color]}
    if o.type == 'CAMERA':
        out[o.name]['camera'] = {'lens': round(md.lens, 3)}

mats = {}
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if not bsdf:
        continue
    grab = {}
    for key in ('Base Color', 'Roughness', 'Metallic', 'Emission Strength'):
        if key in bsdf.inputs:
            v = bsdf.inputs[key].default_value
            grab[key] = round(v, 4) if isinstance(v, float) else [round(x, 4) for x in v]
    mats[m.name] = grab
out['__materials__'] = mats
print(json.dumps(out))
"""

SELECTION_SRC = r"""
import bpy, json
act = bpy.context.active_object
out = {
    'mode': bpy.context.mode,
    'active': act.name if act else None,
    'selected': [o.name for o in bpy.context.selected_objects],
}
if act and act.mode == 'EDIT' and act.type == 'MESH':
    import bmesh
    bm = bmesh.from_edit_mesh(act.data)
    sv = [v.index for v in bm.verts if v.select]
    sf = [f.index for f in bm.faces if f.select]
    se = [e.index for e in bm.edges if e.select]
    out['edit'] = {
        'verts_selected': len(sv), 'edges_selected': len(se), 'faces_selected': len(sf),
        'verts_total': len(bm.verts), 'faces_total': len(bm.faces),
        # capped: the point is WHICH THING Ryan means, not a mesh dump
        'vert_indices': sv[:256], 'face_indices': sf[:256],
    }
print(json.dumps(out))
"""


def run_code(code, **net):
    """execute_code returns whatever the script PRINTED, as a string."""
    return unwrap(send('execute_code', {'code': code}, **net))


def snapshot(**net):
    res = run_code(SNAPSHOT_SRC, **net)
    return json.loads(res['result'] if isinstance(res, dict) else res)


def diff_scenes(before, after):
    """What changed, including OFF CAMERA. A screenshot and a diff fail in
    opposite directions -- the screenshot misses what is out of frame, the diff
    misses how it looks -- which is the whole reason to have both."""
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = {}
    for name in sorted(set(before) & set(after)):
        b, a = before[name], after[name]
        fields = {k: [b[k], a[k]] for k in b if b[k] != a[k]}
        if fields:
            changed[name] = fields
    return {'added': added, 'removed': removed, 'changed': changed}


def checkpoint(label, **net):
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    path = CKPT_DIR / f'{label}.blend'
    # copy=True is load-bearing: without it Blender re-points the OPEN session at
    # the checkpoint file, so the next manual Save silently overwrites a snapshot
    # instead of the file the human thinks they are editing.
    run_code(f'import bpy; bpy.ops.wm.save_as_mainfile('
             f'filepath={str(path)!r}, copy=True, check_existing=False)', **net)
    return path


def auto_shot(tag, max_size, **net):
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SHOT_DIR / f'{tag}.png'
    unwrap(send('get_viewport_screenshot',
                {'max_size': max_size, 'filepath': str(out), 'format': 'png'}, **net))
    shots = sorted(SHOT_DIR.glob('*.png'))
    for stale in shots[:-KEEP_SHOTS]:
        stale.unlink(missing_ok=True)
    return out


def main():
    p = argparse.ArgumentParser(prog='blender-live.py', description=__doc__.split('\n')[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--host', default=DEFAULT_HOST)
    p.add_argument('--port', type=int, default=DEFAULT_PORT)
    p.add_argument('--timeout', type=float, default=TIMEOUT)
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('ping', help='is a live Blender listening')
    sub.add_parser('info', help='scene name, object list, counts')
    sub.add_parser('activity', help='what the HUMAN changed since last drained')
    sub.add_parser('selection', help='what the human has SELECTED right now')
    sub.add_parser('checkpoints', help='list saved checkpoints')

    o = sub.add_parser('object', help='full detail on one object')
    o.add_argument('--name', required=True)

    e = sub.add_parser('exec', help='run python inside the live Blender')
    g = e.add_mutually_exclusive_group(required=True)
    g.add_argument('--code', help='python source, inline')
    g.add_argument('--file', help='python source, from a file')
    e.add_argument('--no-shot', action='store_true', help='skip the automatic screenshot')
    e.add_argument('--no-checkpoint', action='store_true', help='skip the automatic .blend snapshot')
    e.add_argument('--no-diff', action='store_true', help='skip the scene diff')
    e.add_argument('--max-size', type=int, default=1600)

    sh = sub.add_parser('shot', help='viewport screenshot to a PNG you name')
    sh.add_argument('--out', required=True)
    sh.add_argument('--max-size', type=int, default=1600)

    r = sub.add_parser('restore', help='reopen a checkpoint (CLOSES the current file)')
    r.add_argument('--name', required=True)

    a = p.parse_args()
    net = dict(host=a.host, port=a.port, timeout=a.timeout)

    if a.cmd == 'ping':
        try:
            unwrap(send('ping', **net))
        except (ConnectionRefusedError, OSError) as exc:
            print(f'no live Blender on {a.host}:{a.port} -- {exc}', file=sys.stderr)
            raise SystemExit(1)
        print('pong')

    elif a.cmd == 'info':
        print(json.dumps(unwrap(send('get_scene_info', **net)), indent=2))

    elif a.cmd == 'activity':
        print(json.dumps(unwrap(send('drain_human_activity', **net)), indent=2))

    elif a.cmd == 'selection':
        print(json.dumps(json.loads(run_code(SELECTION_SRC, **net)['result']), indent=2))

    elif a.cmd == 'object':
        print(json.dumps(unwrap(send('get_object_info', {'name': a.name}, **net)), indent=2))

    elif a.cmd == 'checkpoints':
        CKPT_DIR.mkdir(parents=True, exist_ok=True)
        rows = [{'name': f.stem, 'mb': round(f.stat().st_size / 1e6, 1),
                 'when': __import__('time').strftime('%H:%M:%S', __import__('time').localtime(f.stat().st_mtime))}
                for f in sorted(CKPT_DIR.glob('*.blend'), key=lambda f: f.stat().st_mtime)]
        print(json.dumps(rows, indent=2))

    elif a.cmd == 'restore':
        path = CKPT_DIR / f'{a.name}.blend'
        if not path.exists():
            print(f'no checkpoint named {a.name!r} in {CKPT_DIR}', file=sys.stderr)
            raise SystemExit(1)
        run_code(f'import bpy; bpy.ops.wm.open_mainfile(filepath={str(path)!r})', **net)
        print(json.dumps({'restored': str(path),
                          'note': 'opening a file can drop the socket; run ping'}, indent=2))

    elif a.cmd == 'shot':
        out = Path(a.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        res = unwrap(send('get_viewport_screenshot',
                          {'max_size': a.max_size, 'filepath': str(out), 'format': 'png'}, **net))
        if not out.exists():
            blob = res.get('image') or res.get('data') if isinstance(res, dict) else None
            if not blob:
                print(f'no file at {out} and no inline image in {res}', file=sys.stderr)
                raise SystemExit(1)
            out.write_bytes(base64.b64decode(blob))
        print(json.dumps({'path': str(out), 'bytes': out.stat().st_size}, indent=2))

    elif a.cmd == 'exec':
        import time
        tag = time.strftime('%H%M%S')
        code = Path(a.file).read_text() if a.file else a.code
        report = {}

        if not a.no_checkpoint:
            report['checkpoint'] = str(checkpoint(f'before-{tag}', **net))
        before = None if a.no_diff else snapshot(**net)

        report['result'] = run_code(code, **net)

        if before is not None:
            report['diff'] = diff_scenes(before, snapshot(**net))
        if not a.no_shot:
            report['shot'] = str(auto_shot(f'exec-{tag}', a.max_size, **net))

        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
