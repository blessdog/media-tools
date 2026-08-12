// media-tools — image-to-video: one still + a motion prompt → one clip. One job.
//
// TWO ROUTES, and the default is the good one:
//   comfy (default)  HunyuanVideo 1.5 I2V, fp16, on the Vast box. The real
//                    renderer. Needs a box + the :8189 tunnel.
//   replicate        seedance/wan hosted models. These produce SLOP — three
//                    hands, impossible motion, painted frames turning
//                    photographic — and slop is worthless (CLAUDE.md, Ryan
//                    2026-08-12). Kept only for plumbing checks nobody looks at.
//                    You must ASK for it: --provider replicate.
//
// Salvaged from cutwork/tools/quick-i2v.mjs 2026-08-11; the Replicate adapter
// table and its hard-won settings (upload-not-data-URI; wan-2.5-i2v-fast fails
// server-side with an opaque E002) are unchanged.

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, basename, join } from 'node:path';
import { envKey, repoRoot } from './_env.mjs';
import { predictModel, fetchBytes } from './_replicate.mjs';
import { buildHunyuanI2VGraph } from './_hunyuan.mjs';
import { uploadInput, runWorkflow, fetchOutput } from './_comfy.mjs';
import { uploadImage as ltxUpload, imageToVideo as ltxI2V, fetchVideo as ltxFetch,
  LTX_RESOLUTIONS, estimateCost } from './_ltx.mjs';
import { dataUri, buzzBalance, buildLtxFlfJob, priceJob, submitAndWait,
  fetchVideo as civitaiFetch } from './_civitai.mjs';

const HELP = `image-to-video — animate one still into one motion clip

usage: node image-to-video.mjs --image still.png --prompt "..." --out clip.mp4 [flags]

The prompt describes what MOVES, not what the frame is — the still already
carries the picture. "smoke rises and drifts left, he blinks" beats a re-run of
the shot description.

flags:
  --image PATH     (required) source still
  --prompt TEXT    (required) motion description ("mist drifts, water ripples")
  --out PATH       (required) output clip
  --provider P     comfy (default, HunyuanVideo 1.5 on the box) | ltx | replicate
                   ltx      LTX 2.5 Pro on api.ltx.io. The full first-party
                            model, no box, ~$0.09/s at 720p. The ONLY route
                            that takes --last-frame.
                   replicate is SLOP — see the header. Ask for it explicitly.
  --last-frame P   ltx only: an END frame. The model interpolates from --image
                   to this. Ink blot in, finished painting out.
  --model M        ltx only: ltx-2-5-pro (default) | ltx-2-3-pro | ltx-2-pro.
                   The '-fast' distilled variants are deliberately unavailable.
  --resolution R   ltx: 720p (default) | 1080p | 1440p | 4k
  --camera M       ltx only: dolly_in | dolly_out | dolly_left | dolly_right
                   | jib_up | jib_down | static | focus_shift
  --audio          ltx only: let the model generate sound (default: silent)
  --host URL       ComfyUI base url (default http://127.0.0.1:8189)
  --duration N     seconds (default 5)
  --fps N          comfy: frames per second (default 24)
  --width N        comfy: default 1280
  --height N       comfy: default 720
  --steps N        comfy: sampler steps (default 20)
  --cfg F          comfy: guidance (default 6)
  --shift F        comfy: ModelSamplingSD3 shift (default 7)
  --seed N         reproducible generation
  --negative TEXT  comfy: negative prompt (default empty — negation summons)
  --resolution R   replicate only: 480p | 720p | 1080p (default 720p)
  --model M        replicate only: bytedance/seedance-1-lite (default)
                   | bytedance/seedance-1-pro
                   | wan-video/wan-2.5-i2v-fast  (BROKEN server-side: E002)
  --moving         replicate only: let the camera move (default: camera holds)
  --explain        print every resolved input as JSON and render NOTHING

Every render writes <out>.json beside the clip: model, sampler settings, seed,
frame count, the motion prompt, and the sha256 of the source still.

example:
  node ~/projects/media-tools/tools/image-to-video.mjs \\
    --image stills/01.png --prompt "slow drift, mist rolls left" --out clips/01.mp4`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const sha = (p) => createHash('sha256').update(readFileSync(p)).digest('hex').slice(0, 16);
const image = flag('--image');
const prompt = flag('--prompt');
const out = flag('--out');
if (!image || !prompt || !out) { console.error(HELP); process.exit(2); }
if (!existsSync(image)) { console.error(`--image not found: ${image}`); process.exit(2); }
const duration = parseInt(flag('--duration', '5'), 10);
const explain = args.includes('--explain');
const seedFlag = flag('--seed');
const seed = seedFlag ? parseInt(seedFlag, 10) : Math.floor(Math.random() * 1e6);

// ─── route ──────────────────────────────────────────────────────────────────
const HOST = flag('--host', 'http://127.0.0.1:8189');
const provider = flag('--provider', 'comfy');
async function comfyUp(url) {
  try {
    const r = await fetch(`${url.replace(/\/$/, '')}/system_stats`, { signal: AbortSignal.timeout(4000) });
    return r.ok;
  } catch { return false; }
}

// ─── civitai (orchestrator, LTX 2.3 22b-dev) ────────────────────────────────
if (provider === 'civitai') {
  const lastFrame = flag('--last-frame');
  if (lastFrame && !existsSync(lastFrame)) { console.error(`--last-frame not found: ${lastFrame}`); process.exit(2); }
  const model = flag('--model', 'ltx2.3:22b-dev');
  if (/distilled/.test(model)) {
    console.error(`'${model}' is the distilled tier. Use 22b-dev (CLAUDE.md).`);
    process.exit(2);
  }
  const width = parseInt(flag('--width', '1280'), 10);
  const height = parseInt(flag('--height', '720'), 10);
  const fps = parseInt(flag('--fps', '24'), 10);
  const frameGuideStrength = parseFloat(flag('--frame-guide', '0.8'));

  const job = buildLtxFlfJob({
    prompt, firstFrame: dataUri(image), lastFrame: lastFrame ? dataUri(lastFrame) : undefined,
    frameGuideStrength, duration, width, height, fps, model,
  });

  // Free: the orchestrator prices the exact payload without spending.
  const { cost, insufficientBuzz } = await priceJob(job);
  const before = await buzzBalance().catch(() => null);

  const manifest = {
    tool: 'image-to-video', provider: 'civitai', renderer: model,
    api: 'https://orchestration.civitai.com/v2/consumer/workflows',
    frame: { width, height, seconds: duration, fps },
    sampler: { frameGuideStrength },
    start: { file: image, sha256: sha(image) },
    ...(lastFrame ? { end: { file: lastFrame, sha256: sha(lastFrame) } } : {}),
    motionPrompt: prompt, interpolates: Boolean(lastFrame),
    buzzQuoted: cost, buzzBefore: before, insufficientBuzz,
    out,
  };
  if (explain) { console.log(JSON.stringify({ ...manifest, wouldRender: true, spent: 'nothing (whatif)' }, null, 2)); process.exit(0); }
  if (insufficientBuzz) { console.error(`insufficient buzz for this job: ${JSON.stringify(cost)}`); process.exit(3); }

  console.error(`image-to-video: civitai ${model} · ${width}x${height} · ${duration}s @ ${fps} · guide ${frameGuideStrength}`);
  console.error(`  cost ${JSON.stringify(cost)}   balance ${JSON.stringify(before)}`);
  console.error(lastFrame ? `  ${basename(image)} → ${basename(lastFrame)}  (interpolating)` : `  ${basename(image)} (single frame)`);
  console.error(`motion: ${prompt}`);

  const done = await submitAndWait(job, { onTick: (s) => process.stderr.write(`\r  ${s}      `) });
  process.stderr.write('\n');
  const bytes = await civitaiFetch(done.url);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, bytes);
  const after = await buzzBalance().catch(() => null);
  writeFileSync(`${out}.json`, JSON.stringify({ ...manifest, workflowId: done.id, videoUrl: done.url,
    bytes: bytes.length, buzzAfter: after,
    buzzActuallySpent: before && after
      ? { blue: before.blue - after.blue, green: before.green - after.green, yellow: before.yellow - after.yellow }
      : null }, null, 2));
  console.log(JSON.stringify({ out, manifest: `${out}.json`, bytes: bytes.length, provider: 'civitai',
    renderer: model, workflowId: done.id, buzzQuoted: cost, buzzAfter: after }));
  process.exit(0);
}

// ─── ltx (api.ltx.io) ───────────────────────────────────────────────────────
if (provider === 'ltx') {
  const lastFrame = flag('--last-frame');
  if (lastFrame && !existsSync(lastFrame)) { console.error(`--last-frame not found: ${lastFrame}`); process.exit(2); }
  const model = flag('--model', 'ltx-2-5-pro');
  if (/-fast$/.test(model)) {
    console.error(`'${model}' is the distilled tier. Not available here — use a -pro model (CLAUDE.md).`);
    process.exit(2);
  }
  const resKey = flag('--resolution', '720p').toLowerCase();
  const resolution = LTX_RESOLUTIONS[resKey] || resKey;
  const camera = flag('--camera');
  const generateAudio = args.includes('--audio');
  // The API takes whole seconds and its floor is 6.
  const seconds = Math.max(6, duration);

  const manifest = {
    tool: 'image-to-video', provider: 'ltx', renderer: model,
    api: 'https://api.ltx.io/v2/image-to-video',
    frame: { resolution, seconds, fps: parseInt(flag('--fps', '24'), 10) },
    start: { file: image, sha256: sha(image) },
    ...(lastFrame ? { end: { file: lastFrame, sha256: sha(lastFrame) } } : {}),
    motionPrompt: prompt, camera: camera || null, generateAudio,
    estimatedCostUSD: estimateCost(model, resolution, seconds),
    costNote: 'estimated from docs.ltx.io/pricing — the API reports no charge and exposes no usage endpoint; the dashboard is the only ground truth',
    interpolates: Boolean(lastFrame),
    out,
  };
  if (explain) { console.log(JSON.stringify({ ...manifest, wouldRender: true, spent: 'nothing' }, null, 2)); process.exit(0); }

  console.error(`image-to-video: ltx ${model} · ${resolution} · ${seconds}s · ~$${manifest.estimatedCostUSD}`);
  console.error(lastFrame ? `  ${basename(image)} → ${basename(lastFrame)}  (interpolating)` : `  ${basename(image)} (single frame)`);
  console.error(`motion: ${prompt}`);

  const imageUri = await ltxUpload(image);
  const lastUri = lastFrame ? await ltxUpload(lastFrame) : undefined;
  const input = {
    image_uri: imageUri, prompt, model, duration: seconds, resolution,
    generate_audio: generateAudio,
    ...(lastUri ? { last_frame_uri: lastUri } : {}),
    ...(camera ? { camera_motion: camera } : {}),
  };
  const job = await ltxI2V(input, { onTick: (s) => process.stderr.write(`\r  ${s}   `) });
  process.stderr.write('\n');
  const url = job.result?.video_url;
  if (!url) throw new Error(`job completed with no video_url: ${JSON.stringify(job).slice(0, 300)}`);
  const bytes = await ltxFetch(url);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, bytes);
  writeFileSync(`${out}.json`, JSON.stringify({ ...manifest, jobId: job.id, bytes: bytes.length, input }, null, 2));
  console.log(JSON.stringify({ out, manifest: `${out}.json`, bytes: bytes.length, provider: 'ltx',
    renderer: model, resolution, seconds, jobId: job.id, costUSD: manifest.estimatedCostUSD }));
  process.exit(0);
}

if (provider === 'comfy') {
  const alive = await comfyUp(HOST);
  if (!alive && !explain) {
    // No silent downgrade. A cheap hosted clip is not a lesser version of this
    // result, it is a different and worthless one.
    console.error(`no ComfyUI at ${HOST} — the real motion renderer is not up.`);
    console.error(`  node ${join(repoRoot(), 'tools/gpu-box.mjs')} start   (then: forward --port 8189)`);
    console.error(`  refusing to fall back to a hosted i2v model; pass --provider replicate if you truly want slop.`);
    process.exit(3);
  }
  const fps = parseInt(flag('--fps', '24'), 10);
  // HunyuanVideo15ImageToVideo takes a FRAME COUNT with step 4; the template
  // ships 121 for ~5s at 24fps. Round to the nearest valid length.
  const raw = duration * fps + 1;
  const length = Math.max(5, Math.round((raw - 1) / 4) * 4 + 1);
  const width = parseInt(flag('--width', '1280'), 10);
  const height = parseInt(flag('--height', '720'), 10);
  const steps = parseInt(flag('--steps', '20'), 10);
  const cfg = parseFloat(flag('--cfg', '6'));
  const shift = parseFloat(flag('--shift', '7'));
  const negative = flag('--negative', '');

  const manifest = {
    tool: 'image-to-video', provider: 'comfy', host: HOST,
    renderer: 'hunyuanvideo-1.5-i2v-720p-fp16',
    model: { unet: 'hunyuanvideo1.5_720p_i2v_fp16.safetensors',
      textEncoders: ['qwen_2.5_vl_7b_fp8_scaled.safetensors', 'byt5_small_glyphxl_fp16.safetensors'],
      vae: 'hunyuanvideo15_vae_fp16.safetensors', clipVision: 'sigclip_vision_patch14_384.safetensors' },
    sampler: { seed, steps, cfg, shift, sampler: 'euler', scheduler: 'simple', denoise: 1, easyCache: false },
    frame: { width, height, length, fps, seconds: Number(((length - 1) / fps).toFixed(2)) },
    start: { file: image, sha256: sha(image) },
    motionPrompt: prompt, negative,
    out,
  };
  if (explain) { console.log(JSON.stringify({ ...manifest, boxUp: alive, wouldRender: true, spent: 'nothing' }, null, 2)); process.exit(0); }

  console.error(`image-to-video: comfy ${HOST} · hunyuan 1.5 i2v fp16 · ${width}x${height} · ${length}f @ ${fps}fps (${manifest.frame.seconds}s)`);
  console.error(`  seed ${seed} · ${steps} steps · cfg ${cfg} · shift ${shift} → ${out}`);
  console.error(`motion: ${prompt}`);

  const startName = await uploadInput(HOST, readFileSync(image), basename(image));
  const graph = buildHunyuanI2VGraph({
    startImage: startName, prompt, negative, seed, width, height, length, fps, steps, cfg, shift,
    prefix: basename(out).replace(/\.[^.]+$/, ''),
  });
  const { outputs, promptId } = await runWorkflow(HOST, graph, {
    clientId: 'media-tools', interval: 5000, maxPolls: 720,
    onStatus: (s) => s === 'running' && process.stderr.write('.'),
  });
  process.stderr.write('\n');
  const bytes = await fetchOutput(HOST, outputs[0]);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, bytes);
  writeFileSync(`${out}.json`, JSON.stringify({ ...manifest, promptId, bytes: bytes.length, graph }, null, 2));
  console.log(JSON.stringify({ out, manifest: `${out}.json`, bytes: bytes.length, provider: 'comfy',
    renderer: manifest.renderer, seed, length, fps, seconds: manifest.frame.seconds, promptId }));
  process.exit(0);
}

// ─── replicate (slop; opt-in only) ──────────────────────────────────────────
const resolution = flag('--resolution', '720p');
const model = flag('--model', 'bytedance/seedance-1-lite');
const fixed = !args.includes('--moving');

const MODELS = {
  'bytedance/seedance-1-lite': ({ url, prompt, duration, resolution, fixed }) => ({
    image: url, prompt, duration, resolution, fps: 24, camera_fixed: fixed,
  }),
  'bytedance/seedance-1-pro': ({ url, prompt, duration, resolution, fixed }) => ({
    image: url, prompt, duration, resolution, fps: 24, camera_fixed: fixed,
  }),
  'wan-video/wan-2.5-i2v-fast': ({ url, prompt, duration, resolution }) => ({
    image: url, prompt, duration, resolution,
    negative_prompt: 'text, lettering, writing, watermark, signature, photographic, glossy, 3d render, camera shake, jump cut, flicker, morphing, warping',
    enable_prompt_expansion: false,
  }),
};
const build = MODELS[model];
if (!build) throw new Error(`unknown --model '${model}' (known: ${Object.keys(MODELS).join(', ')})`);

// Wan/Seedance fetch `image` server-side and reject data: URIs with a bare
// "E002" that names nothing (i2v-replicate.mjs, verified) — upload first.
async function uploadImage(path, tok) {
  const body = new FormData();
  body.append('content', new Blob([readFileSync(path)], { type: 'image/png' }), basename(path));
  const r = await fetch('https://api.replicate.com/v1/files', {
    method: 'POST', headers: { Authorization: `Bearer ${tok}` }, body,
  });
  const j = await r.json();
  if (!r.ok) throw new Error(`upload ${r.status}: ${JSON.stringify(j).slice(0, 300)}`);
  const url = j?.urls?.get;
  if (!url) throw new Error('upload succeeded but returned no URL');
  return url;
}

if (explain) {
  console.log(JSON.stringify({ tool: 'image-to-video', provider: 'replicate', model, duration, resolution,
    camera_fixed: fixed, start: { file: image, sha256: sha(image) }, motionPrompt: prompt, out,
    warning: 'hosted i2v models produce slop — see CLAUDE.md', wouldRender: true, spent: 'nothing' }, null, 2));
  process.exit(0);
}
const tok = envKey('REPLICATE_API_TOKEN');
console.error(`image-to-video: SLOP PATH — ${model} · ${resolution} ${duration}s · camera_fixed=${fixed} → ${out}`);
console.error(`prompt: ${prompt}`);
const imageUrl = await uploadImage(image, tok);
const input = build({ url: imageUrl, prompt, duration, resolution, fixed });
const url = await predictModel(model, input, { token: tok, label: 'quick-i2v', interval: 4000, maxPolls: 300 });
const bytes = await fetchBytes(url);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);
writeFileSync(`${out}.json`, JSON.stringify({ tool: 'image-to-video', provider: 'replicate', model, duration,
  resolution, camera_fixed: fixed, start: { file: image, sha256: sha(image) }, motionPrompt: prompt, out,
  bytes: bytes.length }, null, 2));
console.log(JSON.stringify({ out, manifest: `${out}.json`, bytes: bytes.length, model, duration, resolution, camera_fixed: fixed }));
