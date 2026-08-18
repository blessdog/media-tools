// Krea-2 on Replicate, against a shot Ryan already has an approved frame for.
//
// The control is s02-SCENE from keyframes-v10 — same subject, rendered by the
// uso-inkwash path he approved. So this is not "does Krea look nice", it is
// "does Krea beat the thing already working, on the same shot".
//
// Krea-2 on Replicate takes NO LoRA. It takes style_reference_images (up to 10)
// — the same mechanism as the USO swatch, with ten slots. So the interesting
// variable is WHAT we put in that channel: nothing, the LOCKED swatch, or
// Ryan's own approved frames.
//
// usage: node run.mjs

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { basename, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = '/Users/SSDrive/projects/media-tools';
const KF = '/Users/SSDrive/projects/mediaStudio/bongpot/outputs/keyframes-v10';

const env = Object.fromEntries(
  readFileSync(`${ROOT}/.env`, 'utf8').split('\n')
    .filter((l) => l.includes('=') && !l.trim().startsWith('#'))
    .map((l) => { const i = l.indexOf('='); return [l.slice(0, i).trim(), l.slice(i + 1).trim().replace(/^["']|["']$/g, '')]; }));
const TOK = env.REPLICATE_API_TOKEN;

// The s02 subject, described as content only — the look comes from the
// reference channel, never from adjectives. Same rule as the USO graph.
const PROMPT = 'A heavy-set warehouse foreman sits at a desk facing the camera, '
  + 'an open ledger under his right hand. A long fluorescent tube runs across the ceiling above him. '
  + 'Through a wide window behind him, two workers push hand trucks loaded with cardboard boxes.';

async function upload(path) {
  const fd = new FormData();
  fd.append('content', new Blob([readFileSync(path)], { type: 'image/png' }), basename(path));
  const r = await fetch('https://api.replicate.com/v1/files', {
    method: 'POST', headers: { Authorization: `Bearer ${TOK}` }, body: fd,
  });
  const j = await r.json();
  if (!r.ok || !j?.urls?.get) throw new Error(`upload ${r.status}: ${JSON.stringify(j).slice(0, 200)}`);
  return j.urls.get;
}

async function run(model, input, out) {
  const started = Date.now();
  const c = await fetch(`https://api.replicate.com/v1/models/${model}/predictions`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOK}`, 'Content-Type': 'application/json', Prefer: 'wait' },
    body: JSON.stringify({ input }),
  });
  let p = await c.json();
  if (!c.ok) throw new Error(`${model}: ${JSON.stringify(p).slice(0, 300)}`);
  while (['starting', 'processing'].includes(p.status)) {
    await new Promise((r) => setTimeout(r, 3000));
    p = await (await fetch(p.urls.get, { headers: { Authorization: `Bearer ${TOK}` } })).json();
  }
  if (p.status !== 'succeeded') throw new Error(`${model} ${p.status}: ${p.error || ''}`);
  const url = Array.isArray(p.output) ? p.output[0] : p.output;
  const bytes = Buffer.from(await (await fetch(url)).arrayBuffer());
  writeFileSync(out, bytes);
  writeFileSync(`${out}.json`, JSON.stringify({ model, input: { ...input, style_reference_images: (input.style_reference_images || []).length + ' image(s)' }, predictionId: p.id, seconds: Math.round((Date.now() - started) / 1000), out }, null, 2));
  console.error(`✓ ${basename(out)}  ${Math.round((Date.now() - started) / 1000)}s`);
}

mkdirSync(HERE, { recursive: true });
console.error('uploading reference images…');
const swatch = await upload(`${ROOT}/styles/inkwash/reference/LOCKED-inkwash-texture-1.png`);
const own = [];
for (const f of ['s07-REACTION-uso-inkwash-v1.png', 's04-SCENE-uso-inkwash-v1.png', 's09-SCENE-uso-inkwash-v1.png']) {
  own.push(await upload(join(KF, f)));
}

const base = { prompt: PROMPT, aspect_ratio: '16:9', seed: 4242, creativity: 'raw' };

const TESTS = [
  ['krea/krea-2-medium', { ...base }, 'medium-no-ref.png'],
  ['krea/krea-2-medium', { ...base, style_reference_images: [swatch], style_reference_strength: 0.7 }, 'medium-swatch.png'],
  ['krea/krea-2-medium', { ...base, style_reference_images: own, style_reference_strength: 0.7 }, 'medium-own-frames.png'],
  ['krea/krea-2-large', { ...base, style_reference_images: own, style_reference_strength: 0.7 }, 'large-own-frames.png'],
];

for (const [model, input, out] of TESTS) {
  try { await run(model, input, join(HERE, out)); }
  catch (e) { console.error(`✗ ${out}: ${e.message}`); }
}
console.error('\ndone');
