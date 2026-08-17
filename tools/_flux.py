"""media-tools — Flux Fill adapter. Vendor plumbing only, no policy.

Python twin of the `_`-prefixed JS adapters. Extracted from inpaint-planes.py
2026-08-17 when extend-planes needed the same call.

stdlib only, deliberately: cv2 and httpx live in DIFFERENT interpreters on this
machine, so any third-party HTTP client makes a tool that imports cv2
unrunnable. urllib is the only thing guaranteed present in both.
"""
import io
import json as _json
import sys
import time
import urllib.error
import urllib.request as _u
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

MODEL = "black-forest-labs/flux-fill-pro"

# Names the technique the painting actually uses. NOT the `inkwash` style
# string, which specifies cold-press rag, blooms, backruns and granulation —
# Western watercolour, and the wrong picture (Ryan, 2026-08-17, distinguishing
# 山水 / 水墨 / 工笔).
SHANSHUI_PROMPT = (
    "A Yuan dynasty Chinese shan shui landscape painting on aged xuan paper. "
    "Dense dry-brush texture strokes build the rock and earth: fine repeated "
    "hair-like linear strokes layered over pale grey ink wash. Continue the "
    "surrounding brushwork and the tone of the aged paper exactly.")


def repo_key(name: str) -> str:
    """Read one key out of the repo's .env.

    Resolved from __file__, never cwd — tools here are invoked by absolute path
    from arbitrary directories (CLAUDE.md, the foreign-cwd rule).
    """
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        raise SystemExit(f"no {env}")
    for line in env.read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"{name} not in {env}")


def _req(url: str, tok: str, data=None, headers=None):
    """POST/GET with backoff. Backoff is the NORMAL path here, not an edge
    case: a plane stack fires a dozen predictions and twice as many uploads
    back to back, and the API 429s on the first run every time."""
    delay = 2.0
    for attempt in range(8):
        r = _u.Request(url, data=data,
                       headers={"Authorization": f"Bearer {tok}", **(headers or {})})
        try:
            with _u.urlopen(r, timeout=600) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504) or attempt == 7:
                raise SystemExit(f"replicate {e.code} on {url.split('/')[-1]}: "
                                 f"{e.read()[:200].decode(errors='replace')}")
            wait = float(e.headers.get("retry-after") or delay)
            print(f"    {e.code}, retrying in {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
            delay = min(delay * 2, 60)
    raise SystemExit("unreachable")


def fill(rgb: np.ndarray, band: np.ndarray, prompt: str = SHANSHUI_PROMPT,
         seed: int = 42, guidance: int = 30, steps: int = 50) -> np.ndarray:
    """Paint `band` into `rgb` with flux-fill-pro. Returns RGB, same shape.

    The model sees the real surrounding painting as context and a mask of the
    band. Restricting its context to one plane's own texture (as SHIFTMAP's
    `known` does) was considered and rejected: SHIFTMAP needs that because it
    COPIES patches, and a generative model continues texture semantically
    instead, so starving it of context buys invention rather than preventing it.

    IT INVENTS. Measured on wang-meng: a second red flower beside a real one.
    The caller is responsible for keeping only `band` — that bounds WHERE it
    acts, never WHAT it does there.
    """
    tok = repo_key("REPLICATE_API_TOKEN")

    def upload(arr: np.ndarray, name: str) -> str:
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, format="PNG")
        b = uuid.uuid4().hex
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"content\"; "
                f"filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n"
                ).encode() + buf.getvalue() + f"\r\n--{b}--\r\n".encode()
        return _json.loads(_req("https://api.replicate.com/v1/files", tok, body,
                                {"Content-Type": f"multipart/form-data; boundary={b}"})
                           )["urls"]["get"]

    body = _json.dumps({"input": {
        "image": upload(rgb, "plate.png"),
        "mask": upload((band * 255).astype(np.uint8), "band.png"),
        "prompt": prompt, "steps": steps, "guidance": guidance, "seed": seed,
        "output_format": "png"}}).encode()
    j = _json.loads(_req(f"https://api.replicate.com/v1/models/{MODEL}/predictions",
                         tok, body, {"Content-Type": "application/json",
                                     "Prefer": "wait"}))
    for _ in range(120):
        if j.get("status") in ("succeeded", "failed", "canceled"):
            break
        time.sleep(3)
        j = _json.loads(_req(j["urls"]["get"], tok))
    if j.get("status") != "succeeded":
        raise SystemExit(f"flux-fill {j.get('status')}: {str(j.get('error'))[:200]}")
    out = j["output"]
    with _u.urlopen(out[0] if isinstance(out, list) else out, timeout=300) as resp:
        png = resp.read()
    got = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
    if got.shape != rgb.shape:                       # the API pads to its grid
        got = np.asarray(Image.fromarray(got).resize(
            (rgb.shape[1], rgb.shape[0]), Image.Resampling.LANCZOS))
    return got
