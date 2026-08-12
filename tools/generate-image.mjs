// media-tools — generate-image: prompt (+ style) → one image. One job.
//
// Salvaged from cutwork/tools/quick-still.mjs 2026-08-11. Two changes from the
// original: the style comes from styles/<key>/style.json instead of an imported
// constant (styles-by-reference, CLAUDE.md §5), and the result is JSON on
// stdout with progress on stderr (§4) so it composes in shell pipelines.
//
// Uses predict() — the VERSION-based endpoint. flux-2-dev 404s on the
// model-scoped one (proven in cutwork config.js:41); do not "simplify" this.

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';
import { envKey, repoRoot } from './_env.mjs';
import { predict, predictModel, fetchBytes } from './_replicate.mjs';
import { buildUsoGraph } from './_uso.mjs';
import { uploadInput, runWorkflow, fetchOutput } from './_comfy.mjs';

const HELP = `generate-image — a scene description (+ a style) to one image

Two routes, chosen by the style's renderer.provider:
  comfy      the real renderer — the USO graph on a Vast box (inkwash's winner).
             Needs a box + tunnel: gpu-box up --rent, then forward --port 8189.
  replicate  hosted fallback, used automatically when no box answers.

The style's REFERENCE IMAGE is the look; --prompt is the content.

usage: node generate-image.mjs --prompt "..." --out path.png [flags]

flags:
  --prompt TEXT    (required) what is in the scene — the content channel
  --out PATH       (required) output image path
  --style KEY      style from styles/KEY/style.json (default: inkwash)
  --provider P     comfy | replicate. Default: the style's renderer.provider,
                   falling back to replicate when the comfy host is unreachable.
                   Passing --provider comfy explicitly makes it an ERROR instead.
  --host URL       ComfyUI base url (default http://127.0.0.1:8189)
  --plate-image P  photoreal identity plate for the comfy IDENTITY channel
                   (omit for inserts/empty rooms — style + text only)
  --width N        comfy: frame width  (default: style renderer.dims)
  --height N       comfy: frame height (default: style renderer.dims)
  --lora F         comfy: USO style-lora strength (default: the style's, 1.0)
  --guidance F     comfy: flux guidance (default: the style's, 3.5) — lower is
                   looser and more painterly, higher is more literal
  --steps N        comfy: sampler steps (default: the style's, 20)
  --no-reference   text-only; skip the style's reference image
  --reference PATH override the style's reference image (= the style swatch)
  --identity       replicate only: ALSO copy the reference's face/identity
  --plate          use the style's platePrompt variant (photoreal identity plate)
  --raw            no style at all; --prompt verbatim
  --aspect R       replicate only: 16:9 | 3:4 | 1:1  (default 16:9)
  --seed N         reproducible generation (echoed in the JSON either way)
  --model M        replicate only: override model

example:
  node ~/projects/media-tools/tools/generate-image.mjs \\
    --style inkwash --prompt "a pet shop storefront at dusk" --out stills/01.png`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const prompt = flag('--prompt');
const out = flag('--out');
if (!prompt || !out) { console.error(HELP); process.exit(2); }

const raw = args.includes('--raw');
const styleKey = flag('--style', 'inkwash');

let style = null;
if (!raw) {
  const p = join(repoRoot(), 'styles', styleKey, 'style.json');
  try { style = JSON.parse(readFileSync(p, 'utf8')); }
  catch { console.error(`unknown --style '${styleKey}' (no ${p})`); process.exit(2); }
}
const usePlate = args.includes('--plate');
const variant = usePlate ? 'platePrompt' : 'prompt';

// Resolve the style's reference image (repo-relative) unless suppressed. A
// plate is by definition style-free, so it never rides with a reference.
let refPaths = [];
const refFlag = flag('--reference');
if (refFlag) refPaths = [refFlag];
else if (style && !usePlate && !args.includes('--no-reference')) {
  const list = style.references || (style.styleSwatch ? [style.styleSwatch] : (style.reference ? [style.reference] : []));
  refPaths = list.map((r) => join(repoRoot(), 'styles', styleKey, r));
}
const missing = refPaths.filter((r) => !existsSync(r));
if (missing.length) { console.error(`reference not found:\n  ${missing.join('\n  ')}`); process.exit(2); }
const useRef = refPaths.length > 0;

// ─── route: comfy (the real renderer) or replicate (hosted fallback) ────────
// The style names its own renderer; a box that isn't up must not be a hard stop
// mid-job, so an unreachable host silently degrades to the hosted path UNLESS
// --provider comfy was passed explicitly, in which case wanting it is the point.
const HOST = flag('--host', 'http://127.0.0.1:8189');
const askedProvider = flag('--provider');
const wantComfy = askedProvider ? askedProvider === 'comfy'
  : (!raw && style?.renderer?.provider === 'comfy');

async function comfyUp(url) {
  try {
    const r = await fetch(`${url.replace(/\/$/, '')}/system_stats`, { signal: AbortSignal.timeout(4000) });
    return r.ok;
  } catch { return false; }
}

const seedFlag = flag('--seed');
const seed = seedFlag ? parseInt(seedFlag, 10) : Math.floor(Math.random() * 1e6);

if (wantComfy) {
  const alive = await comfyUp(HOST);
  if (!alive && askedProvider === 'comfy') {
    console.error(`--provider comfy but no ComfyUI at ${HOST}\n  node ${join(repoRoot(), 'tools/gpu-box.mjs')} up --rent   (then: wait, forward --port 8189)`);
    process.exit(3);
  }
  if (alive) {
    if (!useRef) { console.error('comfy route needs the style swatch (the style channel) — do not pass --no-reference'); process.exit(2); }
    const r = style?.renderer || {};
    const width = parseInt(flag('--width', String(r.dims?.width || 1152)), 10);
    const height = parseInt(flag('--height', String(r.dims?.height || 640)), 10);
    const plate = flag('--plate-image');
    if (plate && !existsSync(plate)) { console.error(`--plate-image not found: ${plate}`); process.exit(2); }

    // The swatch carries the medium; the text channel stays a short content nudge
    // (style.json promptNote) — the opposite of the hosted path, where style text
    // is load-bearing.
    const scene = `${style?.prompt || ''} ${prompt}`.trim();
    console.error(`generate-image: comfy ${HOST} · USO ${width}x${height} seed ${seed}`
      + ` · style ${basename(refPaths[0])}${plate ? ` · identity ${basename(plate)}` : ' · NO identity channel'} → ${out}`);
    console.error(`prompt: ${scene}`);

    const swatchName = await uploadInput(HOST, readFileSync(refPaths[0]), basename(refPaths[0]));
    const plateName = plate ? await uploadInput(HOST, readFileSync(plate), basename(plate)) : null;
    const graph = buildUsoGraph({
      plateImage: plateName, swatchImage: swatchName, prompt: scene, seed,
      // renderer.lora reads "uso-flux1-dit-lora-v1.safetensors @ 1.0" — the file is
      // hardcoded in the graph, so only the strength after the @ is wanted here.
      lora: parseFloat(flag('--lora', String(r.lora || '').match(/@\s*([0-9.]+)/)?.[1] ?? '1.0')),
      guidance: parseFloat(flag('--guidance', String(r.guidance ?? 3.5))),
      width, height, steps: parseInt(flag('--steps', String(r.steps ?? 20)), 10),
      prefix: basename(out).replace(/\.[^.]+$/, ''),
      ckpt: r.checkpoint || 'flux1-dev-fp8.safetensors',
    });
    const { outputs, promptId } = await runWorkflow(HOST, graph, {
      clientId: 'media-tools', onStatus: (s) => s === 'running' && process.stderr.write('.'),
    });
    process.stderr.write('\n');
    const bytes = await fetchOutput(HOST, outputs[0]);
    mkdirSync(dirname(out), { recursive: true });
    writeFileSync(out, bytes);
    console.log(JSON.stringify({ out, bytes: bytes.length, provider: 'comfy', renderer: r.winner || null, style: styleKey, seed, width, height, identity: plateName, promptId }));
    process.exit(0);
  }
  console.error(`no ComfyUI at ${HOST} — falling back to the hosted renderer (expect a step down from ${style?.renderer?.winner || 'the real one'})`);
}

// With a reference, the referencePrompt template names it explicitly ("the same
// style as the reference") — that phrasing is what produced the approved plates.
// --identity locks the reference's FACE too (bongpot's one-character-many-shots
// case). Default borrows only the medium: without this, the reference plate's
// man gets painted into every scene (proven 2026-08-11).
const lockIdentity = args.includes('--identity');
const template = useRef
  ? (lockIdentity ? style?.referencePrompt : style?.styleOnlyPrompt)
  : null;
const stylePrefix = style ? style[variant] : '';
const fullPrompt = raw ? prompt
  : template ? template.replace('{SCENE}', prompt)
  : `${stylePrefix} ${prompt}`;
const model = flag('--model', style?.fallback?.model || style?.image?.model || 'replicate/black-forest-labs/flux-kontext-pro');

const input = {
  prompt: fullPrompt,
  aspect_ratio: flag('--aspect', '16:9'),
  ...(style?.fallback?.params || style?.image?.params || { output_format: 'png' }),
};
if (seedFlag) input.seed = seed;
if (useRef) {
  const uris = refPaths.map((r) => `data:image/png;base64,${readFileSync(r).toString('base64')}`);
  // Each family names its reference input differently (schemas verified 2026-08-11).
  if (model.includes('kontext')) input.input_image = uris[0];
  else if (model.includes('flux-2')) input.input_images = uris;
  else input.image_input = uris;
}

console.error(`generate-image: ${model}${useRef ? ` · ${refPaths.length} ref(s): ${refPaths.map((r) => basename(r)).join(', ')}` : ' · TEXT ONLY'} → ${out}`);
console.error(`prompt: ${fullPrompt}`);
const token = envKey('REPLICATE_API_TOKEN');
// nano-banana-pro is model-scoped; flux-2-dev 404s there and needs the version
// endpoint (cutwork config.js:41). Route on which model was actually chosen.
const url = model.includes('nano-banana')
  ? await predictModel(model.replace(/^replicate\//, ''), input, { token, label: 'generate-image' })
  : await predict(model, input, { token, label: 'generate-image' });
const bytes = await fetchBytes(url);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);
console.log(JSON.stringify({ out, bytes: bytes.length, model, style: raw ? null : styleKey, variant: raw ? null : variant }));
