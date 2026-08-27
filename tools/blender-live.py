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

    o = sub.add_parser('object', help='full detail on one object')
    o.add_argument('--name', required=True)

    e = sub.add_parser('exec', help='run python inside the live Blender')
    g = e.add_mutually_exclusive_group(required=True)
    g.add_argument('--code', help='python source, inline')
    g.add_argument('--file', help='python source, from a file')

    sh = sub.add_parser('shot', help='viewport screenshot to a PNG in the repo')
    sh.add_argument('--out', required=True)
    sh.add_argument('--max-size', type=int, default=1400)

    a = p.parse_args()
    net = dict(host=a.host, port=a.port, timeout=a.timeout)

    if a.cmd == 'ping':
        try:
            unwrap(send('ping', **net))
        except (ConnectionRefusedError, OSError) as exc:
            print(f'no live Blender on {a.host}:{a.port} -- {exc}', file=sys.stderr)
            raise SystemExit(1)
        print('pong')
        return

    if a.cmd == 'info':
        print(json.dumps(unwrap(send('get_scene_info', **net)), indent=2))
        return

    if a.cmd == 'activity':
        print(json.dumps(unwrap(send('drain_human_activity', **net)), indent=2))
        return

    if a.cmd == 'object':
        print(json.dumps(unwrap(send('get_object_info', {'name': a.name}, **net)), indent=2))
        return

    if a.cmd == 'exec':
        code = Path(a.file).read_text() if a.file else a.code
        print(json.dumps(unwrap(send('execute_code', {'code': code}, **net)), indent=2))
        return

    if a.cmd == 'shot':
        out = Path(a.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        res = unwrap(send('get_viewport_screenshot',
                          {'max_size': a.max_size, 'filepath': str(out), 'format': 'png'}, **net))
        # The addon writes the file itself and may also return it inline; prefer
        # the file it wrote, and only decode base64 if no file landed. A silent
        # "success" with nothing on disk is the failure this guards.
        if not out.exists():
            blob = res.get('image') or res.get('data') if isinstance(res, dict) else None
            if not blob:
                print(f'no file at {out} and no inline image in {res}', file=sys.stderr)
                raise SystemExit(1)
            out.write_bytes(base64.b64decode(blob))
        print(json.dumps({'path': str(out), 'bytes': out.stat().st_size, 'addon': res}, indent=2))
        return


if __name__ == '__main__':
    main()
