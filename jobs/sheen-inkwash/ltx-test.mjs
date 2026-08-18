// LTX-2.3 image→video test, WITHOUT rewiring the lipdub graph.
//
// tools/workflows/ltx23-ia2v-flat.json is an image+AUDIO→video graph (bongpot's
// lipdub rig). Rather than cut the audio branch out of 55 interdependent nodes,
// feed it SILENCE: the audio path runs, drives nothing, and the motion comes
// from the still plus the text prompt. Ten minutes instead of an hour of surgery.
//
// usage: node ltx-test.mjs <still.png> <motion prompt> <out.mp4>
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { basename } from 'node:path';
import { uploadInput, runWorkflow, fetchOutput } from '../../tools/_comfy.mjs';

const HOST = process.env.COMFY_HOST || 'http://127.0.0.1:8189';
const [still, prompt, out] = process.argv.slice(2);
if (!still || !prompt || !out) { console.error('usage: node ltx-test.mjs <still.png> <prompt> <out.mp4>'); process.exit(2); }

// 5s of digital silence at 48k stereo — the shape LoadAudio expects.
const silence = '/tmp/ltx-silence.wav';
execFileSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
  '-i', 'anullsrc=r=48000:cl=stereo', '-t', '5', silence]);

const graph = JSON.parse(readFileSync(new URL('../../tools/workflows/ltx23-ia2v-flat.json', import.meta.url)));

console.error(`ltx-test: uploading inputs to ${HOST}`);
const imgName = await uploadInput(HOST, readFileSync(still), basename(still));
const audName = await uploadInput(HOST, readFileSync(silence), basename(silence));

graph['269'].inputs.image = imgName;                 // the still
graph['276'].inputs.audio = audName;                 // silence
delete graph['276'].inputs.audioUI;                  // UI-only field, not an API input
graph['340:319'].inputs.value = prompt;              // the plain prompt...
graph['340:349'].inputs.value = false;               // ...and bypass the Gemma rewriter
// gemma_3_12B_it_fp4_mixed.safetensors on the box is TRUNCATED (3.6GB; safetensors
// load fails with a shape/size mismatch). The full 13.2GB copy pulled by
// provision-ltx.sh loads fine.
graph['340:318'].inputs.text_encoder = 'comfy_gemma_3_12B_it.safetensors';
// Fresh noise each run so a bad result is not mistaken for a fixed seed.
graph['340:285'].inputs.noise_seed = Math.floor(Math.random() * 1e9);
graph['340:286'].inputs.noise_seed = Math.floor(Math.random() * 1e9);

console.error(`ltx-test: ltx-2.3-22b-dev-fp8 · 1280x720 · 5s @24fps`);
console.error(`prompt: ${prompt}`);
const { outputs, promptId } = await runWorkflow(HOST, graph, {
  clientId: 'media-tools', interval: 5000, maxPolls: 720,
  onStatus: (s) => s === 'running' && process.stderr.write('.'),
});
process.stderr.write('\n');
const bytes = await fetchOutput(HOST, outputs[0]);
writeFileSync(out, bytes);
console.log(JSON.stringify({ out, bytes: bytes.length, renderer: 'ltx-2.3-22b-dev-fp8', promptId }));
