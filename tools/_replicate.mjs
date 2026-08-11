// Shared Replicate client for the Node CLI render tools.
//
// Model slugs are passed in by the caller. The version-lookup + create + poll
// boilerplate had been copy-pasted into every render tool and quietly drifted:
// some poll loops were unbounded (a stuck prediction hangs forever), some
// skipped the succeeded-but-empty-output guard. This is the one copy.
//
// Salvaged from cutwork/tools/_replicate.mjs 2026-08-11. Its one config import
// is inlined below — a single constant with a single consumer belongs here; a
// config SSOT returns if a second consumer ever appears (bible §2.3).

const REPLICATE_API_BASE = 'https://api.replicate.com/v1';

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const _verCache = {};

// Resolve a model's latest version id. Accepts slugs with or without the
// config.js `replicate/` routing prefix.
export async function latestVersion(model, token) {
  const path = model.replace(/^replicate\//, '');
  if (_verCache[path]) return _verCache[path];
  const [owner, name] = path.split('/');
  const r = await fetch(`${REPLICATE_API_BASE}/models/${owner}/${name}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const m = await r.json();
  const id = m?.latest_version?.id;
  if (!r.ok || !id) throw new Error(`version lookup ${r.status}: ${JSON.stringify(m).slice(0, 300)}`);
  return (_verCache[path] = id);
}

// Create a version-based prediction and poll to completion. Returns the first
// output URL. Bounded by maxPolls so a stuck prediction fails loudly instead of
// hanging, and guards the succeeded-but-empty-output case centrally.
export async function predict(model, input, { token, label = 'predict', interval = 2500, maxPolls = 240, onStatus } = {}) {
  const version = await latestVersion(model, token);
  const create = await fetch(`${REPLICATE_API_BASE}/predictions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Prefer: 'wait' },
    body: JSON.stringify({ version, input }),
  });
  let pred = await create.json();
  if (!create.ok) throw new Error(`${label} create ${create.status}: ${JSON.stringify(pred).slice(0, 400)}`);
  for (let i = 0; !['succeeded', 'failed', 'canceled'].includes(pred.status); i++) {
    if (i >= maxPolls) throw new Error(`${label} timed out after ~${Math.round((maxPolls * interval) / 1000)}s (status=${pred.status})`);
    await sleep(interval);
    pred = await (await fetch(pred.urls.get, { headers: { Authorization: `Bearer ${token}` } })).json();
    onStatus?.(pred.status);
  }
  if (pred.status !== 'succeeded') throw new Error(`${label} ${pred.status}: ${pred.error || ''}`);
  const out = pred.output;
  const url = Array.isArray(out) ? out[0] : out;
  if (!url) throw new Error(`${label} succeeded but returned no output URL`);
  return url;
}

// Like predict() but skips the version lookup — use when the recipe pins a
// specific version hash (e.g. flux2-ref). Avoids an extra API round-trip.
export async function predictVersioned(version, input, { token, label = 'predict', interval = 2500, maxPolls = 240, onStatus } = {}) {
  const create = await fetch(`${REPLICATE_API_BASE}/predictions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Prefer: 'wait' },
    body: JSON.stringify({ version, input }),
  });
  let pred = await create.json();
  if (!create.ok) throw new Error(`${label} create ${create.status}: ${JSON.stringify(pred).slice(0, 400)}`);
  for (let i = 0; !['succeeded', 'failed', 'canceled'].includes(pred.status); i++) {
    if (i >= maxPolls) throw new Error(`${label} timed out after ~${Math.round((maxPolls * interval) / 1000)}s`);
    await sleep(interval);
    pred = await (await fetch(pred.urls.get, { headers: { Authorization: `Bearer ${token}` } })).json();
    onStatus?.(pred.status);
  }
  if (pred.status !== 'succeeded') throw new Error(`${label} ${pred.status}: ${pred.error || ''}`);
  const url = Array.isArray(pred.output) ? pred.output[0] : pred.output;
  if (!url) throw new Error(`${label} succeeded but returned no output URL`);
  return url;
}

// Model-scoped predictions (no version needed) — for Nano Banana Pro and other
// models that use /models/{owner}/{name}/predictions directly.
export async function predictModel(modelPath, input, { token, label = 'predict', interval = 2500, maxPolls = 240, onStatus } = {}) {
  const create = await fetch(`${REPLICATE_API_BASE}/models/${modelPath}/predictions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Prefer: 'wait' },
    body: JSON.stringify({ input }),
  });
  let pred = await create.json();
  if (!create.ok) throw new Error(`${label} create ${create.status}: ${JSON.stringify(pred).slice(0, 400)}`);
  for (let i = 0; !['succeeded', 'failed', 'canceled'].includes(pred.status); i++) {
    if (i >= maxPolls) throw new Error(`${label} timed out after ~${Math.round((maxPolls * interval) / 1000)}s`);
    await sleep(interval);
    pred = await (await fetch(pred.urls.get, { headers: { Authorization: `Bearer ${token}` } })).json();
    onStatus?.(pred.status);
  }
  if (pred.status !== 'succeeded') throw new Error(`${label} ${pred.status}: ${pred.error || ''}`);
  const url = Array.isArray(pred.output) ? pred.output[0] : pred.output;
  if (!url) throw new Error(`${label} succeeded but returned no output URL`);
  return url;
}

// Download a URL to bytes.
export async function fetchBytes(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetch output ${r.status}`);
  return new Uint8Array(await r.arrayBuffer());
}
