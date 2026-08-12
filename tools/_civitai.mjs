// media-tools — CivitAI orchestrator adapter. Vendor plumbing only, no policy.
//
// Why this route exists: it is the compute Ryan already owns. The LTX and fal
// balances are both exhausted; the CivitAI account holds thousands of Green
// Buzz, and the orchestrator runs LTX 2.3 `22b-dev` with a
// `firstLastFrameToVideo` operation — the same first-and-last-frame mechanism
// proven on LTX 2.5, on weights we do not pay per clip for.
//
// `22b-dev` is the full model. `22b-distilled` is the fast tier and is rejected
// upstream (CLAUDE.md: never ship slop).
//
// Two things the docs do not tell you, both established by free `whatif=true`
// probes on 2026-08-12:
//   1. INPUT IMAGES CAN BE data: URIs. The orchestrator ingests them and
//      rewrites them to its own signed blob URLs. There is an upload endpoint
//      (civitai.com/api/v1/image-upload, returns a presigned Backblaze URL) but
//      it is unnecessary.
//   2. The published "~133 Buzz" figure did not match. The API's own whatif for
//      a 720p/5s/24fps FLF job returned 27 blue + 12 green. Always quote the
//      whatif number, never the docs.

import { readFileSync } from 'node:fs';
import { extname } from 'node:path';
import { envKey } from './_env.mjs';

const ORCH = 'https://orchestration.civitai.com/v2/consumer/workflows';
const ACCOUNT_ID = 12293736;   // civitai.com/api/v1/me -> bongpot

const auth = () => ({ Authorization: `Bearer ${envKey('CIVITAI_API_TOKEN')}` });

export function dataUri(path) {
  const ext = extname(path).toLowerCase();
  const type = ext === '.png' ? 'image/png' : ext === '.webp' ? 'image/webp' : 'image/jpeg';
  return `data:${type};base64,${readFileSync(path).toString('base64')}`;
}

// The documented /api/v1/buzz* paths all 404; this trpc route is what the site
// itself uses and it is the only readable ground truth for balance.
export async function buzzBalance(accountId = ACCOUNT_ID) {
  const input = encodeURIComponent(JSON.stringify({ json: { accountId, accountType: 'user' } }));
  const r = await fetch(`https://civitai.com/api/trpc/buzz.getBuzzAccount?input=${input}`, {
    headers: auth(), signal: AbortSignal.timeout(30000),
  });
  if (!r.ok) throw new Error(`buzz balance ${r.status}`);
  return (await r.json())?.result?.data?.json ?? null;
}

export function buildLtxFlfJob({ prompt, firstFrame, lastFrame, frameGuideStrength = 0.8,
  duration = 5, width = 1280, height = 720, fps = 24, model = 'ltx2.3:22b-dev' }) {
  const [engine, weight] = model.split(':');
  return { steps: [{ $type: 'videoGen', input: {
    engine, operation: 'firstLastFrameToVideo', model: weight,
    prompt, firstFrame, ...(lastFrame ? { lastFrame } : {}),
    frameGuideStrength, duration, width, height, fps,
  } }] };
}

// whatif=true returns the exact charge and spends NOTHING. Probe every new
// payload shape with it before letting it cost anything.
export async function priceJob(job) {
  const r = await fetch(`${ORCH}?whatif=true`, {
    method: 'POST', headers: { ...auth(), 'Content-Type': 'application/json' },
    body: JSON.stringify(job), signal: AbortSignal.timeout(180000),
  });
  const t = await r.text();
  if (!r.ok) throw new Error(`whatif ${r.status}: ${t.slice(0, 300)}`);
  const j = JSON.parse(t);
  const list = j?.transactions?.list || [];
  return {
    cost: Object.fromEntries(list.map((x) => [x.accountType, x.amount])),
    insufficientBuzz: Boolean(j?.transactions?.insufficientBuzz),
  };
}

// The orchestrator publishes the output URL the INSTANT the job is queued, with
// `available: false` beside it, and fetching that URL 404s until the render is
// done. So the URL is not the signal — `available` is. Matching on the URL
// alone cost us a clip's wait and a confusing 404.
export function findVideoUrl(node) {
  if (!node || typeof node !== 'object') return null;
  if (Array.isArray(node)) {
    for (const v of node) { const hit = findVideoUrl(v); if (hit) return hit; }
    return null;
  }
  if (node.available === true && typeof node.url === 'string') return node.url;
  for (const v of Object.values(node)) {
    if (v && typeof v === 'object') { const hit = findVideoUrl(v); if (hit) return hit; }
  }
  return null;
}

// Poll a workflow that is already running (submitted, paid for) and return it
// once its output is actually available.
export async function awaitWorkflow(id, { interval = 6000, maxPolls = 200, onTick } = {}) {
  for (let i = 0; i < maxPolls; i++) {
    const r = await fetch(`${ORCH}/${id}`, { headers: auth(), signal: AbortSignal.timeout(60000) });
    if (!r.ok) throw new Error(`poll ${id} ${r.status}`);
    const body = await r.json();
    const pct = body.steps?.[0]?.jobs?.[0]?.estimatedProgressRate;
    onTick?.(body.status, pct, i);
    const url = findVideoUrl(body);
    if (url) return { id, status: body.status, url, body };
    if (['failed', 'expired', 'canceled'].includes(body.status)) {
      throw new Error(`workflow ${id} ${body.status}: ${JSON.stringify(body).slice(0, 400)}`);
    }
    await new Promise((res) => setTimeout(res, interval));
  }
  throw new Error(`workflow ${id} still running after ${(interval * maxPolls) / 1000}s`);
}

export async function submitAndWait(job, { interval = 6000, maxPolls = 200, onTick } = {}) {
  const r = await fetch(`${ORCH}?whatif=false&wait=0`, {
    method: 'POST', headers: { ...auth(), 'Content-Type': 'application/json' },
    body: JSON.stringify(job), signal: AbortSignal.timeout(180000),
  });
  const t = await r.text();
  if (!r.ok) throw new Error(`submit ${r.status}: ${t.slice(0, 400)}`);
  const created = JSON.parse(t);
  const id = created.id;
  if (!id) throw new Error(`no workflow id: ${t.slice(0, 300)}`);
  console.error(`  workflow ${id}`);   // print BEFORE waiting, so a crash mid-poll never orphans a paid job
  return awaitWorkflow(id, { interval, maxPolls, onTick });
}

export async function fetchVideo(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(300000) });
  if (!r.ok) throw new Error(`video fetch ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
}
