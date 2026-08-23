#!/bin/zsh
# The zone chain, exactly as proven on Z1 (STATE.md 2026-08-17 night):
# segment-points -> invariant check -> complete-planes -> segment-regions
# -> pin-objects -> inpaint-planes --flux -> frame-zero control -> build-relief.
#
# RELIEF ADDED 2026-08-22, and the reason is the point: relief won its A/B on
# 2026-08-19 and the verdict commit (02f025d) changed STATE.md and nothing else.
# Six zones were built through THIS FILE hours later and none of them got it --
# 3 of 74 planes, 4% of the film. Tilt, proven the same night, WAS scripted
# (gen-geometry.py) and reached every zone. See
# knowledge/a-verdict-is-not-landed-until-the-builder-changes.md.
# usage: build-zone.sh z2
set -e
Z=$1
cd "$(dirname "$0")/../../.."   # repo root
D=jobs/wang-meng/journey/$Z
LONG=$(python3 -c "import json;print(max(json.load(open('$D/plate.json'))['size']))")

echo "=== $Z segment-points" >&2
.venv/bin/python tools/segment-points.py --image $D/plate.png --points $D/points.json \
  --out $D/layers-cut >/dev/null

echo "=== $Z invariant + self-heal (z1 lesson: re-cut off-point masks --max-grow 0)" >&2
for attempt in 1 2; do
  BAD=$(python3 - "$D" <<'PY'
import json, sys
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
d = sys.argv[1]
meta = json.loads(open(f"{d}/layers-cut/layers.json").read())
W, H = meta["size"]
pts = {p["name"]: p for p in json.load(open(f"{d}/points.json"))["points"]}
bad = []
for p in meta["planeList"]:
    if not p.get("layer"):
        continue
    pt = pts.get(p["name"])
    if pt is None:
        continue
    x, y = int(pt["x"] * W), int(pt["y"] * H)
    im = Image.open(f"{d}/layers-cut/{p['layer']}")
    ox, oy = p["offset"]
    lx, ly = x - ox, y - oy
    a = np.asarray(im.split()[3]) if 0 <= ly < im.height and 0 <= lx < im.width else None
    if a is None or a[ly, lx] < 128:
        bad.append(p["name"])
print(" ".join(bad))
PY
)
  if [[ -z "$BAD" ]]; then echo "    invariant clean" >&2; break; fi
  if [[ $attempt == 2 ]]; then
    echo "INVARIANT STILL FAILING after heal: $BAD" >&2
    # A plane whose mask does not contain its own prompt point is NOT that
    # plane, so it must never be composited. But halting the whole zone over
    # one of thirteen is the wrong trade when the survivor is a distant canopy
    # carrying no animation. DROP_BAD=1 removes the failing planes and says so;
    # the default still refuses, because dropping silently is how a stack
    # quietly loses depth nobody notices.
    # Measured 2026-08-21 on right-bluff-crown-pines: with the auto-grow SAM
    # returns 575,615px (the entire right side of the plate); with --max-grow 0
    # it returns a 226x35 sliver 160px ABOVE the point. Neither is a pine
    # cluster -- see knowledge/no-whole-tree-to-segment.md, there is no
    # whole-tree SHAPE in this painting to find.
    [[ -z $DROP_BAD ]] && exit 3
    echo "    DROP_BAD=1: removing $BAD from the stack" >&2
    python3 - "$D" ${=BAD} <<'PYDROP'
import json, sys
d, bad = sys.argv[1], sys.argv[2:]
f = f"{d}/layers-cut/layers.json"
m = json.loads(open(f).read())
kept = [p for p in m["planeList"] if p["name"] not in bad]
m["droppedForInvariant"] = bad
m["planeList"] = kept
m["planes"] = len(kept)
open(f, "w").write(json.dumps(m, indent=1))
print(f"    stack is now {len(kept)} planes (was {len(kept)+len(bad)})", file=sys.stderr)
PYDROP
    break
  fi
  echo "    healing off-point masks: $BAD" >&2
  python3 - "$D" ${=BAD} <<'PY'
import json, sys
d, bad = sys.argv[1], sys.argv[2:]
full = json.load(open(f"{d}/points.json"))
sub = dict(full)
sub["points"] = [p for p in full["points"] if p["name"] in bad]
json.dump(sub, open(f"{d}/points-heal.json", "w"))
PY
  .venv/bin/python tools/segment-points.py --image $D/plate.png \
    --points $D/points-heal.json --out $D/layers-heal --max-grow 0 >/dev/null
  python3 - "$D" <<'PY'
import json, shutil
d = sys.argv[1] if False else __import__("sys").argv[1]
main = json.loads(open(f"{d}/layers-cut/layers.json").read())
heal = json.loads(open(f"{d}/layers-heal/layers.json").read())
byname = {p["name"]: p for p in main["planeList"]}
for hp in heal["planeList"]:
    if not hp.get("layer"):
        continue
    shutil.copy(f"{d}/layers-heal/{hp['layer']}", f"{d}/layers-cut/{hp['layer']}")
    tgt = byname[hp["name"]]
    # the z1 swap gotcha: offset AND bbox must both follow the layer file
    tgt.update({k: hp[k] for k in ("layer", "offset", "bbox") if k in hp})
json.dump(main, open(f"{d}/layers-cut/layers.json", "w"), indent=1)
print("healed:", [p["name"] for p in heal["planeList"] if p.get("layer")])
PY
done

echo "=== $Z complete-planes" >&2
python3 tools/complete-planes.py --layers $D/layers-cut --out $D/layers-sealed >/dev/null
echo "=== $Z segment-regions (native)" >&2
.venv/bin/python tools/segment-regions.py --image $D/plate.png --out $D/objects --max-side $LONG >/dev/null
echo "=== $Z pin-objects" >&2
python3 tools/pin-objects.py --layers $D/layers-sealed --objects $D/objects \
  --out $D/layers-pinned --min-majority 0.4 >/dev/null
echo "=== $Z inpaint-planes --flux" >&2
python3 tools/inpaint-planes.py --layers $D/layers-pinned --out $D/layers-filled \
  --behind 100 --method flux >/dev/null

echo "=== $Z frame-zero control" >&2
python3 - "$D" <<'PY'
import json, sys
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
d = sys.argv[1]
meta = json.loads(open(f"{d}/layers-filled/layers.json").read())
W, H = meta["size"]
canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
planes = [p for p in meta["planeList"] if p.get("layer")]
planes.sort(key=lambda p: p["depth"])
for p in planes:
    im = Image.open(f"{d}/layers-filled/{p['layer']}").convert("RGBA")
    canvas.alpha_composite(im, tuple(p["offset"]))
plate = np.asarray(Image.open(f"{d}/plate.png").convert("RGB")).astype(int)
comp = np.asarray(canvas.convert("RGB")).astype(int)
alpha = np.asarray(canvas.split()[3]) > 0
diff = (np.abs(comp - plate).max(axis=2) > 2) & alpha
print(json.dumps({"changedPx": int(diff.sum()), "claimed": round(float(alpha.mean()), 4)}))
if diff.sum() > 0:
    print(f"FRAME-ZERO FAIL: {diff.sum()} px changed at rest", file=sys.stderr)
    sys.exit(4)
PY
echo "=== $Z relief (within-plane surface shape; --relief for render-parallax)" >&2
~/.venvs/media-tools/bin/python tools/build-relief.py \
  --layers $D/layers-filled --out $D \
  --sheet jobs/wang-meng/evidence/relief-$Z.png >/dev/null

echo "=== $Z DONE" >&2
