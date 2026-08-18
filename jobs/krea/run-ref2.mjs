// The test Ryan actually asked for: HIS reference style, with and without a
// LoRA stacked on top.
//
// The 24-render swath ran the LoRAs bare — trigger phrase and text, no
// reference channel at all. He rejected that, and clarified: "I don't like the
// Lora's raw. Without giving it any reference style of my own." So this is the
// combination, on references HE picked today.
//
// usage: node run-ref.mjs [--host http://127.0.0.1:8189]

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { uploadInput, runWorkflow, fetchOutput } from '../../tools/_comfy.mjs';
import { buildKreaStyleRefGraph } from '../../tools/_krea.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, 'renders-ref2');
mkdirSync(OUT, { recursive: true });
const args = process.argv.slice(2);
const HOST = args.includes('--host') ? args[args.indexOf('--host') + 1] : 'http://127.0.0.1:8189';
const SEED = 20260812;

// Picked by Ryan 2026-08-12, in this lane. Three bongpot frames he chose HERE,
// plus his own portrait from today's bake-off.
const REFS = {
  s02: 'references-clean/s02-SCENE-kontext-pro-v1.png',
  s55: 'references-clean/s55-SCENE-kontext-pro-v1.png',
  r06: 'references-clean/06.png',
  s05: 'references-clean/s05-SCENE-uso-inkwash-v1.png',
  s06: 'references-clean/s06-FORESHADOW-uso-inkwash-v1.png',
  s37: 'references-clean/s37-INSERT-uso-inkwash-v1.png',
  portrait: 'references-clean/seedream-5-pro.png',
};

// Two subjects only — this run is about the STYLE channel, not coverage.
const SUBJECTS = {
  hound: 'A large bloodhound lies on a broad boulder at the edge of a green river, looking off to one side',
  doorway: 'A man in headphones steps through a doorway holding a large kitchen knife at his side, a washing machine behind him in a dim narrow room',
};

// null = the reference mechanism alone. The rest stack a second LoRA on top.
const STACK = {
  'ref-only': null,
  'ref+darkbrush': 'darkbrush.safetensors',


};

console.error('uploading references…');
const uploaded = {};
for (const [k, rel] of Object.entries(REFS)) {
  const p = join(HERE, rel);
  uploaded[k] = await uploadInput(HOST, readFileSync(p), basename(p));
  console.error(`  ${k} → ${uploaded[k]}`);
}

// Ryan's three bongpot picks are one coherent look, so they go in TOGETHER —
// the node takes up to three images and blends them. His portrait is a
// different look and is tested on its own.
const REFSETS = {
  kontext3: [uploaded.s02, uploaded.s55, uploaded.r06],
  bongpot3: [uploaded.s05, uploaded.s06, uploaded.s37],
  portrait: [uploaded.portrait],
};

const t0 = Date.now();
const results = [];

for (const [refKey, refImages] of Object.entries(REFSETS)) {
  for (const [stackKey, styleLora] of Object.entries(STACK)) {
    for (const [subjKey, subject] of Object.entries(SUBJECTS)) {
      const name = `${refKey}--${stackKey}--${subjKey}`;
      // No trigger phrase and no medium words: the look comes from the images.
      const graph = buildKreaStyleRefGraph({
        prompt: subject, refImages, seed: SEED, styleLora, styleLoraStrength: 0.8, prefix: name,
      });
      const started = Date.now();
      try {
        const { outputs, promptId } = await runWorkflow(HOST, graph, { clientId: name, interval: 2000, maxPolls: 300 });
        const bytes = await fetchOutput(HOST, outputs[0]);
        const out = join(OUT, `${name}.png`);
        writeFileSync(out, bytes);
        const secs = ((Date.now() - started) / 1000).toFixed(1);
        writeFileSync(`${out}.json`, JSON.stringify({
          lane: 'krea', approved: false, route: 'style-reference',
          refSet: refKey, references: Object.entries(REFS).filter(([k]) => refKey === 'portrait' ? k === 'portrait' : k !== 'portrait').map(([, v]) => v),
          refLora: 'krea2_style_reference.safetensors', refLoraStrength: 1.0,
          styleLora, styleLoraStrength: styleLora ? 0.8 : null,
          subject, prompt: subject, seed: SEED, steps: 8, cfg: 1.0,
          base: 'krea2_turbo_fp8_scaled.safetensors', promptId, seconds: +secs, out,
        }, null, 2));
        console.error(`✓ ${name}  ${secs}s`);
        results.push({ name, ok: true, seconds: +secs });
      } catch (e) {
        console.error(`✗ ${name}: ${e.message.slice(0, 200)}`);
        results.push({ name, ok: false, error: e.message.slice(0, 240) });
      }
    }
  }
}

const ok = results.filter((r) => r.ok).length;
console.error(`\n${ok}/${results.length} in ${Math.round((Date.now() - t0) / 1000)}s → ${OUT}`);
console.log(JSON.stringify({ out: OUT, seed: SEED, results }, null, 2));
