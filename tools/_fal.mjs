// media-tools — fal.ai adapter. Vendor plumbing only, no policy.
//
// Why this route exists: fal is the ONLY cheap way to reach Wan 2.2's control
// conditioning. Established by probe on 2026-08-12 —
//   * CivitAI's orchestrator has no Wan under any of 12 engine names tried
//   * CivitAI's LTX 2.5 accepts exactly ONE operation, firstLastFrameToVideo
// So buzz buys keyframe interpolation and nothing else. Depth/pose/flow
// conditioning — the answer to content drift, which is the only failure mode
// we have actually measured — lives here or on a rented box, nowhere else.
//
// The control endpoints take a VIDEO and extract depth/pose internally, which
// deletes an entire local preprocessing stage. You hand it choreography; it
// paints over it.
//
// NOT the slop path: turbo/fast/distilled variants are rejected upstream
// (CLAUDE.md). These are the full A14B weights.

import { readFileSync, statSync } from 'node:fs';
import { basename, extname } from 'node:path';
import { envKey } from './_env.mjs';

const QUEUE = 'https://queue.fal.run';
const REST = 'https://rest.alpha.fal.ai';

const auth = () => ({ Authorization: `Key ${envKey('FAL_KEY')}` });

// $ per second of OUTPUT video, read off the fal model pages 2026-08-12.
// Treat as an ESTIMATE and say so — fal bills on its own accounting, and the
// LTX lesson was that a headline rate and the real charge differ by a third.
export const FAL_RATES = {
  'fal-ai/wan/v2.2-a14b/image-to-video':   { '480p': 0.04, '580p': 0.06, '720p': 0.08 },
  'fal-ai/wan-22-vace-fun-a14b/depth':     { '480p': 0.04, '580p': 0.06, '720p': 0.08 },
  'fal-ai/wan-22-vace-fun-a14b/pose':      { '480p': 0.04, '580p': 0.06, '720p': 0.08 },
  'fal-ai/wan-fun-control':                { '480p': 0.04, '580p': 0.06, '720p': 0.08 },
  'fal-ai/wan-vace-14b':                   { '480p': 0.04, '580p': 0.06, '720p': 0.08 },
};

export function estimateCost(model, resolution, seconds) {
  const rate = FAL_RATES[model]?.[resolution];
  return rate == null ? null : +(rate * seconds).toFixed(3);   // null, never a confident zero
}

export function dataUri(path) {
  const ext = extname(path).toLowerCase();
  const type = ext === '.png' ? 'image/png' : ext === '.webp' ? 'image/webp'
    : ext === '.mp4' ? 'video/mp4' : 'image/jpeg';
  return `data:${type};base64,${readFileSync(path).toString('base64')}`;
}

// Videos are too big to inline as a data URI without choking the request.
// fal's storage handshake: initiate -> PUT bytes -> use the returned file_url.
export async function uploadFile(path) {
  const ext = extname(path).toLowerCase();
  const contentType = ext === '.mp4' ? 'video/mp4' : ext === '.png' ? 'image/png' : 'image/jpeg';
  const init = await fetch(`${REST}/storage/upload/initiate?storage_type=fal-cdn-v3`, {
    method: 'POST', headers: { ...auth(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ content_type: contentType, file_name: basename(path) }),
    signal: AbortSignal.timeout(60000),
  });
  if (!init.ok) throw new Error(`upload initiate ${init.status}: ${(await init.text()).slice(0, 200)}`);
  const { upload_url, file_url } = await init.json();
  const put = await fetch(upload_url, {
    method: 'PUT', headers: { 'Content-Type': contentType },
    body: readFileSync(path), signal: AbortSignal.timeout(600000),
  });
  if (!put.ok) throw new Error(`upload PUT ${put.status}`);
  return file_url;
}

// One place that decides how a local file gets in: inline small, upload large.
export async function toUrl(path, { inlineLimit = 4_000_000 } = {}) {
  return statSync(path).size <= inlineLimit ? dataUri(path) : uploadFile(path);
}

export async function balance() {
  const r = await fetch(`${REST}/billing/user_balance`, { headers: auth(), signal: AbortSignal.timeout(20000) });
  if (!r.ok) throw new Error(`balance ${r.status}`);
  return parseFloat(await r.text());
}

// Submit returns immediately with an id. Print it BEFORE waiting, so a crash
// mid-poll never orphans a paid job — the same discipline the CivitAI route
// learned the hard way.
export async function submit(model, input) {
  const r = await fetch(`${QUEUE}/${model}`, {
    method: 'POST', headers: { ...auth(), 'Content-Type': 'application/json' },
    body: JSON.stringify(input), signal: AbortSignal.timeout(180000),
  });
  const t = await r.text();
  if (!r.ok) throw new Error(`submit ${r.status}: ${t.slice(0, 400)}`);
  const j = JSON.parse(t);
  if (!j.request_id) throw new Error(`no request_id: ${t.slice(0, 300)}`);
  return j.request_id;
}

// The status path drops the sub-route: fal-ai/wan-22-vace-fun-a14b/depth is
// queued under fal-ai/wan-22-vace-fun-a14b. Getting this wrong 404s on a job
// that is running fine.
const statusBase = (model) => model.split('/').slice(0, 2).join('/');

export async function awaitResult(model, id, { interval = 5000, maxPolls = 240, onTick } = {}) {
  const base = statusBase(model);
  for (let i = 0; i < maxPolls; i++) {
    const r = await fetch(`${QUEUE}/${base}/requests/${id}/status`, { headers: auth(), signal: AbortSignal.timeout(60000) });
    if (!r.ok) throw new Error(`status ${id} ${r.status}`);
    const s = await r.json();
    onTick?.(s.status, s.queue_position, i);
    if (s.status === 'COMPLETED') {
      const rr = await fetch(`${QUEUE}/${base}/requests/${id}`, { headers: auth(), signal: AbortSignal.timeout(120000) });
      if (!rr.ok) throw new Error(`result ${id} ${rr.status}`);
      return await rr.json();
    }
    if (['FAILED', 'CANCELLED', 'ERROR'].includes(s.status)) {
      throw new Error(`request ${id} ${s.status}: ${JSON.stringify(s).slice(0, 400)}`);
    }
    await new Promise((res) => setTimeout(res, interval));
  }
  throw new Error(`request ${id} still running after ${(interval * maxPolls) / 1000}s`);
}

export async function submitAndWait(model, input, opts = {}) {
  const id = await submit(model, input);
  console.error(`  fal request ${id}`);
  return { id, result: await awaitResult(model, id, opts) };
}

export function findVideoUrl(node) {
  if (!node || typeof node !== 'object') return null;
  if (Array.isArray(node)) { for (const v of node) { const hit = findVideoUrl(v); if (hit) return hit; } return null; }
  if (typeof node.url === 'string' && /\.(mp4|webm|mov)(\?|$)/i.test(node.url)) return node.url;
  for (const v of Object.values(node)) { if (v && typeof v === 'object') { const hit = findVideoUrl(v); if (hit) return hit; } }
  return null;
}

export async function fetchVideo(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(300000) });
  if (!r.ok) throw new Error(`video fetch ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
}
