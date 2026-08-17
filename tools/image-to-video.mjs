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
import { toUrl as falToUrl, balance as falBalance, submitAndWait as falSubmitAndWait,
  findVideoUrl as falFindVideo, fetchVideo as falFetch, estimateCost as falEstimate } from './_fal.mjs';

const HELP = `image-to-video — animate one still into one motion clip

usage: node image-to-video.mjs --image still.png --prompt "..." --out clip.mp4 [flags]

The prompt describes what MOVES, not what the frame is — the still already
carries the picture. "smoke rises and drifts left, he blinks" beats a re-run of
the shot description.

flags:
  --image PATH     (required) source still
  --prompt TEXT    (required) motion description ("mist drifts, water ripples")
  --out PATH       (required) output clip
  --provider P     comfy (default) | seedance | ltx | civitai | fal | replicate
                   seedance bytedance/seedance-2.0 on Replicate. The only route
                            carrying EVERY conditioning channel at once: first
                            frame, --last-frame, --style-ref (style guidance)
                            and --motion-video (motion transfer). Hand it real
                            choreography and it stops inventing smoke.
                   civitai  LTX 2.5 22b-dev on owned buzz. 35 buzz per 5s/720p.
                            Accepts ONLY firstLastFrameToVideo — keyframes are
                            its whole control surface, verified by probe.
                   fal      Wan 2.2 A14B. The only affordable door to control
                            conditioning (depth/pose/flow), which CivitAI does
                            not carry under any engine name. Costs dollars.
                   ltx      LTX 2.5 Pro on api.ltx.io. The full first-party
                            model, no box, ~$0.09/s at 720p. The ONLY route
                            that takes --last-frame.
                   replicate is SLOP — see the header. Ask for it explicitly.
  --last-frame P   ltx, seedance: an END frame. The model interpolates from
                   --image to this.
  --motion-video P seedance only: a video whose MOTION is copied. Its pixels
                   never appear — only its choreography. This is the cure for
                   invented nonsense; phone footage is fine.
  --style-ref P    seedance only: a reference image for style guidance. Put the
                   look here, never in --prompt.
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

// ─── fal (Wan 2.2 A14B) ─────────────────────────────────────────────────────
// The point of this route is NOT that it is another hosted I2V. It is the only
// affordable door to Wan's control conditioning, and rung 1 of that ladder is
// this: does Wan hold the ink look AT ALL, before a line of control tooling
// gets written. $0.20 answers it.
if (provider === 'fal') {
  const model = flag('--model', 'fal-ai/wan/v2.2-a14b/image-to-video');
  if (/turbo|fast|distill/i.test(model)) {
    console.error(`'${model}' is a distilled/turbo tier. Use the full A14B weights (CLAUDE.md).`);
    process.exit(2);
  }
  const resolution = flag('--resolution', '480p');
  if (!['480p', '580p', '720p'].includes(resolution)) {
    console.error(`--resolution must be 480p | 580p | 720p (got ${resolution})`);
    process.exit(2);
  }
  const fps = parseInt(flag('--fps', '16'), 10);
  const estimate = falEstimate(model, resolution, duration);

  const manifest = {
    tool: 'image-to-video', provider: 'fal', renderer: model,
    api: `https://queue.fal.run/${model}`,
    frame: { resolution, seconds: duration, fps },
    start: { file: image, sha256: sha(image) },
    motionPrompt: prompt, seed,
    costEstimateUsd: estimate, costIsEstimate: true,
    out,
  };
  if (explain) { console.log(JSON.stringify({ ...manifest, wouldRender: true, spent: 'nothing' }, null, 2)); process.exit(0); }

  const before = await falBalance().catch(() => null);
  if (before !== null && estimate !== null && before < estimate) {
    console.error(`fal balance $${before} is below the ~$${estimate} estimate for this render. Top up at fal.ai/dashboard/billing.`);
    process.exit(3);
  }
  console.error(`image-to-video: fal ${model} · ${resolution} · ${duration}s @ ${fps}`);
  console.error(`  ~$${estimate ?? '?'} (estimate)   balance $${before ?? '?'}`);
  console.error(`motion: ${prompt}`);

  const { id, result } = await falSubmitAndWait(model, {
    image_url: await falToUrl(image), prompt, resolution,
    num_frames: Math.round(duration * fps) + 1, frames_per_second: fps, seed,
  }, { onTick: (s, q) => process.stderr.write(`\r  ${s}${q != null ? ` q${q}` : ''}      `) });
  process.stderr.write('\n');

  const url = falFindVideo(result);
  if (!url) { console.error(`no video in result: ${JSON.stringify(result).slice(0, 400)}`); process.exit(1); }
  const bytes = await falFetch(url);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, bytes);
  const after = await falBalance().catch(() => null);
  writeFileSync(`${out}.json`, JSON.stringify({ ...manifest, requestId: id, videoUrl: url,
    bytes: bytes.length, balanceBefore: before, balanceAfter: after,
    actuallySpentUsd: before != null && after != null ? +(before - after).toFixed(4) : null }, null, 2));
  console.log(JSON.stringify({ out, manifest: `${out}.json`, bytes: bytes.length, provider: 'fal',
    renderer: model, requestId: id, balanceAfter: after }));
  process.exit(0);
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

// ─── seedance (bytedance/seedance-2.0) ──────────────────────────────────────
// The one model that carries every conditioning channel this project needs:
// first frame, last frame, up to 9 style/character reference images, up to 3
// reference VIDEOS for motion transfer, and reference audio. Schema verified
// live 2026-08-12.
//
// Why it is here and not in the slop block below: the failure Ryan named is a
// video model INVENTING — smoke clouds, nonsense transitions — because a still
// plus a duration is a vacuum and the model fills it. `reference_videos` is the
// cure. You hand it real choreography and it has nothing left to invent.
//
// And the prompt must NOT describe the medium. On a still model words like
// "blooms", "bleeds", "pools", "spreads" read as texture; on a VIDEO model they
// read as tense-carrying verbs and get animated — which is precisely how the
// ink ends up crawling. The look belongs in reference_images. The prompt gets
// subject motion only.
if (provider === 'seedance') {
  const motionVideo = flag('--motion-video');
  const styleRef = flag('--style-ref');
  const lastFrame = flag('--last-frame');
  const model = flag('--model', 'bytedance/seedance-2.0');
  const resolution = flag('--resolution', '1080p');
  const wantAudio = args.includes('--audio');

  for (const [lbl, p] of [['--motion-video', motionVideo], ['--style-ref', styleRef], ['--last-frame', lastFrame]]) {
    if (p && !existsSync(p)) { console.error(`${lbl} not found: ${p}`); process.exit(2); }
  }

  if (explain) {
    console.log(JSON.stringify({ tool: 'image-to-video', provider: 'seedance', model, resolution, duration,
      start: { file: image, sha256: sha(image) },
      motionVideo: motionVideo ? { file: motionVideo, sha256: sha(motionVideo) } : null,
      styleRef: styleRef ? { file: styleRef, sha256: sha(styleRef) } : null,
      lastFrame: lastFrame ? { file: lastFrame, sha256: sha(lastFrame) } : null,
      generate_audio: wantAudio, motionPrompt: prompt, out, spent: 'nothing' }, null, 2));
    process.exit(0);
  }

  const tok = envKey('REPLICATE_API_TOKEN');
  console.error(`image-to-video: seedance ${model} · ${resolution} · ${duration}s → ${out}`);
  console.error(`  first frame:   ${basename(image)}`);
  console.error(`  motion video:  ${motionVideo ? basename(motionVideo) : 'NONE — the model will invent the motion'}`);
  console.error(`  style ref:     ${styleRef ? basename(styleRef) : 'none'}`);
  console.error(`  last frame:    ${lastFrame ? basename(lastFrame) : 'none'}`);
  console.error(`  prompt:        ${prompt}`);

  // HARD CONSTRAINT, learned from a live E006 on 2026-08-12:
  //   "Reference images, videos, and audios cannot be used together with first
  //    or last frame images."
  // Seedance has TWO mutually exclusive modes, and the tool picks by intent:
  //   FRAME mode      --image (+ --last-frame)  → i2v / FLF2V
  //   REFERENCE mode  --motion-video / --style-ref → --image demotes to a
  //                   reference image, and there is no first frame at all.
  // Reference mode is the one that stops the model inventing, so any request
  // carrying choreography wins the tie.
  const referenceMode = Boolean(motionVideo || styleRef);
  if (referenceMode && lastFrame) {
    console.error(`seedance: --last-frame cannot be combined with --motion-video/--style-ref (model E006).`);
    console.error(`  Drop --last-frame for motion transfer, or drop the references for FLF2V.`);
    process.exit(2);
  }
  console.error(`  mode:          ${referenceMode ? 'REFERENCE (image demoted to a style/character reference)' : 'FRAME'}`);

  const input = {
    prompt,
    duration, resolution,
    aspect_ratio: 'adaptive',
    generate_audio: wantAudio,
    ...(seed ? { seed } : {}),
    ...(referenceMode
      ? {
          reference_images: [
            await uploadImage(image, tok),
            ...(styleRef ? [await uploadImage(styleRef, tok)] : []),
          ],
          ...(motionVideo ? { reference_videos: [await uploadImage(motionVideo, tok, 'video/mp4')] } : {}),
        }
      : {
          image: await uploadImage(image, tok),
          ...(lastFrame ? { last_frame_image: await uploadImage(lastFrame, tok) } : {}),
        }),
  };

  const url = await predictModel(model, input, { token: tok, label: 'seedance', interval: 5000, maxPolls: 400 });
  const bytes = await fetchBytes(url);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, bytes);
  writeFileSync(`${out}.json`, JSON.stringify({
    tool: 'image-to-video', provider: 'seedance', renderer: model,
    resolution, duration, generate_audio: wantAudio, seed: seed ?? null,
    start: { file: image, sha256: sha(image) },
    ...(motionVideo ? { motionVideo: { file: motionVideo, sha256: sha(motionVideo) } } : {}),
    ...(styleRef ? { styleRef: { file: styleRef, sha256: sha(styleRef) } } : {}),
    ...(lastFrame ? { end: { file: lastFrame, sha256: sha(lastFrame) } } : {}),
    motionPrompt: prompt, out, bytes: bytes.length,
  }, null, 2));
  console.log(JSON.stringify({ out, manifest: `${out}.json`, bytes: bytes.length, provider: 'seedance', renderer: model }));
  process.exit(0);
}

// ─── replicate (slop; opt-in only) ──────────────────────────────────────────
const resolution = flag('--resolution', '720p');
const model = flag('--model', 'bytedance/seedance-1-lite');
const fixed = !args.includes('--moving');
// Each provider block scopes its own --fps default; wan-2.2-a14b bills per
// second and takes num_frames, so it needs one here too. 16 is the model's own.
const fps = parseInt(flag('--fps', '16'), 10);

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
  // NOT slop: the full Wan 2.2 A14B weights, same tier the fal route reaches.
  // Schema read live off the Replicate API 2026-08-17 — this model takes
  // num_frames/frames_per_second, NOT `duration`, and has no negative_prompt.
  // go_fast=false and the full 40 sample_steps are the whole point of coming
  // here rather than to wan-2.2-i2v-fast, which is the PrunaAI distill.
  'wan-video/wan-2.2-i2v-a14b': ({ url, prompt, duration, resolution, fps, seed }) => ({
    image: url, prompt, resolution,
    num_frames: Math.round(duration * fps) + 1,
    frames_per_second: fps,
    go_fast: false, sample_steps: 40, sample_shift: 5,
    ...(seed ? { seed } : {}),
  }),
};
// Everything in this block is hosted, but not everything hosted is slop — the
// banner has to tell the truth about which one is being run, or it trains you
// to ignore it.
const SLOP = new Set(['bytedance/seedance-1-lite', 'bytedance/seedance-1-pro',
  'wan-video/wan-2.5-i2v-fast']);
const build = MODELS[model];
if (!build) throw new Error(`unknown --model '${model}' (known: ${Object.keys(MODELS).join(', ')})`);

// Wan/Seedance fetch `image` server-side and reject data: URIs with a bare
// "E002" that names nothing (i2v-replicate.mjs, verified) — upload first.
async function uploadImage(path, tok, mime = 'image/png') {
  const body = new FormData();
  body.append('content', new Blob([readFileSync(path)], { type: mime }), basename(path));
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
    warning: SLOP.has(model) ? 'hosted i2v models produce slop — see CLAUDE.md'
      : 'full weights, not a distilled tier — judge the output, not the host',
    wouldRender: true, spent: 'nothing' }, null, 2));
  process.exit(0);
}
const tok = envKey('REPLICATE_API_TOKEN');
console.error(SLOP.has(model)
  ? `image-to-video: SLOP PATH — ${model} · ${resolution} ${duration}s · camera_fixed=${fixed} → ${out}`
  : `image-to-video: replicate ${model} · ${resolution} · ${duration}s · full weights → ${out}`);
console.error(`prompt: ${prompt}`);
const imageUrl = await uploadImage(image, tok);
const input = build({ url: imageUrl, prompt, duration, resolution, fixed, fps, seed });
const url = await predictModel(model, input, { token: tok, label: 'quick-i2v', interval: 4000, maxPolls: 300 });
const bytes = await fetchBytes(url);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);
writeFileSync(`${out}.json`, JSON.stringify({ tool: 'image-to-video', provider: 'replicate', model, duration,
  resolution, camera_fixed: fixed, start: { file: image, sha256: sha(image) }, motionPrompt: prompt, out,
  bytes: bytes.length }, null, 2));
console.log(JSON.stringify({ out, manifest: `${out}.json`, bytes: bytes.length, model, duration, resolution, camera_fixed: fixed }));
