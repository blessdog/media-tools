// The first test swath for the krea lane. Nothing here is approved; it is
// candidates for Ryan's eyes.
//
// Ordered BY BASE, not by prompt: swapping the 13GB checkpoint forces a reload,
// swapping a 300MB LoRA does not. All twelve turbo renders run before raw is
// touched.
//
// usage: node run.mjs [--host http://127.0.0.1:8189]

import { writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runWorkflow, fetchOutput } from '../../tools/_comfy.mjs';
import { buildKreaGraph } from '../../tools/_krea.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, 'renders');
mkdirSync(OUT, { recursive: true });

const args = process.argv.slice(2);
const HOST = args.includes('--host') ? args[args.indexOf('--host') + 1] : 'http://127.0.0.1:8189';
const SEED = 20260812;

const SUBJECTS = {
  s1_car_hound: 'A man with a heavy moustache and round tinted glasses sits in a car passenger seat, a large bloodhound filling the seat beside him, the dog\'s long ears hanging down, grey upholstery behind them',
  s2_snowboard: 'A snowboarder in a white suit stands on a snowy slope holding a board under one arm, pointing up at a range of jagged snow-covered peaks, cloud sitting in the valley below',
  s3_doorway: 'A man in headphones steps through a doorway holding a large kitchen knife at his side, a washing machine and dryer behind him in a dim narrow room',
  s4_hound_rock: 'A large bloodhound lies on a broad boulder at the edge of a green river, looking off to one side, scrub and rocks along the far bank',
  s5_poppy_macro: 'A single pale green poppy seed pod fills the frame, its crown splayed open, beads of sap running down its side, foliage blurred behind',
  s6_poppy_stand: 'A cluster of pale poppy seed pods on tall stems in a front garden, a residential street behind them with a parked car and a low brick house',
};

// Trigger phrases carry the medium. The subject text never mentions ink.
const LORAS = {
  darkbrush: { file: 'darkbrush.safetensors', trigger: 'monochrome ink wash style' },
  linenscroll: { file: 'chinese-ink-linen-scroll-comfy.safetensors', trigger: 'chinese ink linen scroll style' },
};

// Turbo settings are Krea's own. Raw is NOT a quality tier — it is the control
// and LoRA-training substrate — and the official template says nothing about
// running it for inference, so 20 steps is a FIRST GUESS and is labelled as one.
const BASES = {
  turbo: { unet: 'krea2_turbo_fp8_scaled.safetensors', steps: 8, note: 'official template settings' },
  raw: { unet: 'krea2_raw_fp8_scaled.safetensors', steps: 20, note: 'steps GUESSED — no official reference for raw inference' },
};

const t0 = Date.now();
const results = [];

for (const [baseKey, base] of Object.entries(BASES)) {
  for (const [loraKey, lora] of Object.entries(LORAS)) {
    for (const [subjKey, subject] of Object.entries(SUBJECTS)) {
      const name = `${baseKey}--${loraKey}--${subjKey}`;
      const prompt = `${subject}, ${lora.trigger}`;
      const graph = buildKreaGraph({
        prompt, lora: lora.file, loraStrength: 0.8,
        seed: SEED, steps: base.steps, unet: base.unet, prefix: name,
      });
      const started = Date.now();
      try {
        const { outputs, promptId } = await runWorkflow(HOST, graph, { clientId: name, interval: 2000, maxPolls: 300 });
        const bytes = await fetchOutput(HOST, outputs[0]);
        const out = join(OUT, `${name}.png`);
        writeFileSync(out, bytes);
        const secs = ((Date.now() - started) / 1000).toFixed(1);
        writeFileSync(`${out}.json`, JSON.stringify({
          lane: 'krea', approved: false,
          base: baseKey, unet: base.unet, stepsNote: base.note,
          lora: lora.file, loraStrength: 0.8, trigger: lora.trigger,
          subject, prompt, seed: SEED, steps: base.steps, cfg: 1.0,
          sampler: 'euler', scheduler: 'simple', size: '1024x1024',
          promptId, seconds: +secs, out,
        }, null, 2));
        console.error(`✓ ${name}  ${secs}s`);
        results.push({ name, ok: true, seconds: +secs });
      } catch (e) {
        console.error(`✗ ${name}: ${e.message.slice(0, 160)}`);
        results.push({ name, ok: false, error: e.message.slice(0, 200) });
      }
    }
  }
}

const ok = results.filter((r) => r.ok).length;
console.error(`\n${ok}/${results.length} rendered in ${Math.round((Date.now() - t0) / 1000)}s → ${OUT}`);
console.log(JSON.stringify({ out: OUT, seed: SEED, results }, null, 2));
