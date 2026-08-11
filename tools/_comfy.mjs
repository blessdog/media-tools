// Bongpot — ComfyUI API client. Drives a running ComfyUI server (the LTX-2 rig on
// the Vast box, port-forwarded to a local baseUrl) the same poll-to-completion way
// tools/_replicate.mjs drives Replicate.
//
// ComfyUI's HTTP API (default http://127.0.0.1:8188):
//   POST /prompt            { prompt: <API-format graph>, client_id }  -> { prompt_id, node_errors }
//   GET  /history/{id}      -> {} while running, then { [id]: { outputs, status } }
//   GET  /view?filename=&subfolder=&type=output  -> the output bytes (image / video)
//
// Export the API-format graph from ComfyUI via "Save (API Format)". Inject per-shot
// inputs with setInput() before runWorkflow().

const j = (r) => r.json();

// ─── inject an input into an API-format workflow ───────────────────────────
// graph is { "<nodeId>": { class_type, inputs: {...} }, ... }. setInput mutates a
// single node field (e.g. the LoadImage filename, the prompt text, the audio path).
export function setInput(graph, nodeId, field, value) {
  const node = graph[String(nodeId)];
  if (!node) throw new Error(`_comfy.setInput: node ${nodeId} not in graph`);
  if (!node.inputs) node.inputs = {};
  node.inputs[field] = value;
  return graph;
}

// Find the first node of a given class_type (helper for locating the prompt /
// image / audio / save nodes without hardcoding ids across workflow revisions).
export function findNode(graph, classType) {
  const hit = Object.entries(graph).find(([, n]) => n.class_type === classType);
  return hit ? hit[0] : null;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ─── upload a file into ComfyUI's input/ dir (so LoadImage / LoadAudio can read it) ──
// ComfyUI's /upload/image saves any posted file into its input folder and returns the
// stored {name, subfolder, type}; use that name as the LoadImage/LoadAudio value.
export async function uploadInput(baseUrl, bytes, filename, { subfolder = '', overwrite = true } = {}) {
  const base = baseUrl.replace(/\/$/, '');
  const fd = new FormData();
  fd.append('image', new Blob([bytes]), filename);
  fd.append('type', 'input');
  if (subfolder) fd.append('subfolder', subfolder);
  if (overwrite) fd.append('overwrite', 'true');
  const r = await fetch(`${base}/upload/image`, { method: 'POST', body: fd });
  if (!r.ok) throw new Error(`comfy /upload/image ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const j = await r.json();
  return j.subfolder ? `${j.subfolder}/${j.name}` : j.name;
}

// ─── submit a graph, poll to completion, return output file refs ───────────
export async function runWorkflow(baseUrl, graph, { clientId = 'bongpot', interval = 2500, maxPolls = 600, onStatus } = {}) {
  const base = baseUrl.replace(/\/$/, '');

  const sub = await fetch(`${base}/prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: graph, client_id: clientId }),
  });
  if (!sub.ok) throw new Error(`comfy /prompt ${sub.status}: ${(await sub.text()).slice(0, 400)}`);
  const subRes = await j(sub);
  if (subRes.node_errors && Object.keys(subRes.node_errors).length) {
    throw new Error(`comfy graph rejected: ${JSON.stringify(subRes.node_errors).slice(0, 500)}`);
  }
  const promptId = subRes.prompt_id;
  if (!promptId) throw new Error(`comfy /prompt returned no prompt_id: ${JSON.stringify(subRes).slice(0, 300)}`);

  // poll /history/{id} — empty object until the run finishes
  for (let i = 0; i < maxPolls; i++) {
    await sleep(interval);
    const h = await fetch(`${base}/history/${promptId}`);
    if (!h.ok) continue; // transient; keep polling
    const hist = await j(h);
    const entry = hist[promptId];
    if (!entry) { onStatus?.('running'); continue; }
    const statusStr = entry.status?.status_str;
    if (statusStr === 'error' || entry.status?.completed === false && entry.status?.messages?.some?.((m) => m[0] === 'execution_error')) {
      throw new Error(`comfy run errored: ${JSON.stringify(entry.status).slice(0, 500)}`);
    }
    // done — collect outputs (video nodes emit gifs/videos; image nodes emit images)
    const refs = [];
    for (const out of Object.values(entry.outputs || {})) {
      for (const key of ['videos', 'gifs', 'images']) {
        for (const f of out[key] || []) refs.push({ ...f, kind: key });
      }
    }
    onStatus?.('done');
    if (!refs.length) throw new Error(`comfy run finished but produced no output files (prompt ${promptId})`);
    return { promptId, outputs: refs };
  }
  throw new Error(`comfy run timed out after ~${Math.round((maxPolls * interval) / 1000)}s (prompt ${promptId})`);
}

// ─── fetch one output file's bytes ─────────────────────────────────────────
export async function fetchOutput(baseUrl, ref) {
  const base = baseUrl.replace(/\/$/, '');
  const q = new URLSearchParams({ filename: ref.filename, subfolder: ref.subfolder || '', type: ref.type || 'output' });
  const r = await fetch(`${base}/view?${q}`);
  if (!r.ok) throw new Error(`comfy /view ${r.status} for ${ref.filename}`);
  return new Uint8Array(await r.arrayBuffer());
}

// ─── one-call convenience: run a graph, write the first output to disk ──────
export async function runToFile(baseUrl, graph, outPath, opts = {}) {
  const { outputs, promptId } = await runWorkflow(baseUrl, graph, opts);
  const bytes = await fetchOutput(baseUrl, outputs[0]);
  const { writeFileSync } = await import('node:fs');
  writeFileSync(outPath, bytes);
  return { outPath, promptId, ref: outputs[0], count: outputs.length };
}
