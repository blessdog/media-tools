// media-tools — LTX API adapter (api.ltx.io). Vendor plumbing only, no policy.
//
// Why this exists as a route beside the ComfyUI one: LTX 2.5 is 42GB of
// transformer plus a 26GB text encoder, so a box costs ~30 minutes and ~$2 of
// download before its first frame — and that download truncated on us
// 2026-08-12. The hosted API is the SAME first-party model at $0.09/s for 720p,
// so a 6s test clip is $0.54 with no setup. Rent a box for volume, not for tests.
//
// NOT the slop path: `ltx-2-5-pro` is the full model. The `-fast` variants are
// the distilled tier and are deliberately not exposed here (CLAUDE.md).
//
// The one field that matters for the ink-wash work is `last_frame_uri`: given a
// start AND an end frame the model interpolates between them, which is how a
// wet blot becomes a finished painting on screen.

import { readFileSync } from 'node:fs';
import { basename, extname } from 'node:path';
import { envKey } from './_env.mjs';

const BASE = 'https://api.ltx.io';

export const LTX_MODELS = ['ltx-2-5-pro', 'ltx-2-3-pro', 'ltx-2-pro'];

// Resolutions the API accepts, keyed by the shorthand people actually type.
export const LTX_RESOLUTIONS = {
  '720p': '1280x720',
  '1080p': '1920x1080',
  '1440p': '2560x1440',
  '4k': '3840x2160',
};

// $ per second of OUTPUT video. Rates differ PER MODEL, not just per
// resolution — docs.ltx.io/pricing, read 2026-08-12.
//
// The marketing page (ltx.io/model/api) advertises "720p — $0.09 per second"
// with no model qualifier. That is the FAST tier. Pro is $0.12. Quoting the
// headline number for a pro render understates the bill by a third; the tell
// was that fal.ai lists $0.12/s for the same pro model and I did not chase the
// discrepancy. Read the docs table, never the pricing hero.
//
// ltx-2-5-pro publishes no 1440p/4K rate, so those are null rather than guessed.
export const LTX_RATES = {
  'ltx-2-5-pro':  { '1280x720': 0.12, '1920x1080': 0.17, '2560x1440': null, '3840x2160': null },
  'ltx-2-5-fast': { '1280x720': 0.09, '1920x1080': 0.13, '2560x1440': 0.19, '3840x2160': 0.30 },
  'ltx-2-3-pro':  { '1280x720': 0.04, '1920x1080': 0.08, '2560x1440': 0.16, '3840x2160': 0.32 },
  'ltx-2-3-fast': { '1280x720': 0.03, '1920x1080': 0.06, '2560x1440': 0.12, '3840x2160': 0.24 },
};

function auth() {
  return { Authorization: `Bearer ${envKey('LTX_API_KEY')}` };
}

async function ltxJson(path, init = {}) {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...auth(), 'Content-Type': 'application/json', ...(init.headers || {}) },
    signal: AbortSignal.timeout(60000),
  });
  const text = await r.text();
  let body;
  try { body = JSON.parse(text); } catch { body = text; }
  if (!r.ok) throw new Error(`LTX ${path} ${r.status}: ${String(text).slice(0, 300)}`);
  return body;
}

// Three steps, per the docs: ask for a signed slot, PUT the bytes, keep the
// storage_uri. The signed URL must NOT carry our bearer token — it is
// pre-authorised and Google rejects the extra header.
export async function uploadImage(path) {
  const slot = await ltxJson('/v1/upload', { method: 'POST' });
  const bytes = readFileSync(path);
  const type = extname(path).toLowerCase() === '.png' ? 'image/png' : 'image/jpeg';
  const put = await fetch(slot.upload_url, {
    method: 'PUT',
    headers: { 'Content-Type': type, ...(slot.required_headers || {}) },
    body: bytes,
    signal: AbortSignal.timeout(180000),
  });
  if (!put.ok) throw new Error(`upload PUT ${put.status} for ${basename(path)}: ${(await put.text()).slice(0, 200)}`);
  return slot.storage_uri;
}

// Submit + poll. Returns the finished job object; the file lives at
// result.video_url.
export async function imageToVideo(input, { interval = 5000, maxPolls = 240, onTick } = {}) {
  const job = await ltxJson('/v2/image-to-video', { method: 'POST', body: JSON.stringify(input) });
  const id = job.id;
  if (!id) throw new Error(`no job id in submit response: ${JSON.stringify(job).slice(0, 200)}`);
  for (let i = 0; i < maxPolls; i++) {
    await new Promise((r) => setTimeout(r, interval));
    const s = await ltxJson(`/v2/image-to-video/${id}`);
    const status = s.status || s.state;
    onTick?.(status, i);
    if (status === 'completed' || s.result?.video_url) return { ...s, id };
    if (['failed', 'canceled', 'cancelled', 'error'].includes(status)) {
      throw new Error(`LTX job ${id} ${status}: ${JSON.stringify(s.error || s).slice(0, 300)}`);
    }
  }
  throw new Error(`LTX job ${id} still running after ${(interval * maxPolls) / 1000}s`);
}

export async function fetchVideo(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(300000) });
  if (!r.ok) throw new Error(`video fetch ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
}

// Returns null when the rate is not published rather than a confident zero —
// an unknown price must not render as "free".
export function estimateCost(model, resolution, seconds) {
  const rate = LTX_RATES[model]?.[resolution];
  return rate == null ? null : +(rate * seconds).toFixed(2);
}
