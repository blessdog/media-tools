// media-tools — restyle-image: existing image + style → restyled image. One job.
//
// The still-photo sibling of restyle-video. generate-image makes pictures from
// nothing; this one transforms a picture that already exists, preserving its
// composition. Gap found 2026-08-11 by running a real photo through the toolbox.
//
// THE STYLE IS AN IMAGE, NOT A STRING (Ryan, 2026-08-12).
// Until today this tool could only send WORDS. It restyled a photo by pasting
// style.json.prompt into an edit instruction — and the result was a step down
// from the same style rendered through USO, where the medium arrives as the
// LOCKED swatch through CLIPVision. Adjectives cannot carry a medium.
// So: --style-ref sends the swatch as a second reference IMAGE, which is the
// same mechanism USO uses, on models that take multiple references. When a
// style ref is in play the text stops describing the look and becomes a
// content-only instruction — the third channel, exactly as in the USO graph.
//
// Model schemas verified live against the Replicate API (2026-08-11, extended
// 2026-08-12). Ref-capable models are marked ✱ — those are the ones that can
// receive the swatch:
//   google/nano-banana-pro              image_input: array (14)   ✱
//   google/nano-banana-2                image_input: array (14)   ✱
//   black-forest-labs/flux-kontext-pro  input_image: string
//   black-forest-labs/flux-2-dev        input_images: array (4)   ✱
//   black-forest-labs/flux-2-pro        input_images: array (8)   ✱
//   qwen/qwen-image-edit                image: string
//   qwen/qwen-image-edit-plus           image: array             ✱
//   flux-kontext-apps/multi-image-kontext-max  input_image_1 + _2 ✱
//   bytedance/seedream-4.5              image_input: array (14)   ✱
// Order is SOURCE FIRST, style ref second, so aspect_ratio=match_input_image
// locks to the photograph's framing — flux-2-dev squared a 720x1280 portrait
// when left to default, which is how framing got lost on the first attempt.

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, basename, extname } from 'node:path';
import { envKey, repoRoot } from './_env.mjs';
import { predictModel, fetchBytes } from './_replicate.mjs';

const HELP = `restyle-image — restyle an existing image, preserving its composition

usage: node restyle-image.mjs --image in.jpg --out out.png [flags]

flags:
  --image PATH     (required) source image (jpeg/png/gif/webp)
  --out PATH       (required) output image path
  --style KEY      style from styles/KEY/style.json (default: inkwash)
  --object         use the style's objectPrompt variant (apparatus, not figures)
  --prompt TEXT    extra direction appended after the style
  --raw            no style; --prompt verbatim (requires --prompt)
  --style-ref P    style reference IMAGE — the medium arrives as a picture, not
                   as adjectives. Defaults to the style's styleSwatch when the
                   model accepts multiple references. This is the USO mechanism.
  --no-style-ref   text-only, even when the style has a swatch (the old behaviour)
  --model M        google/nano-banana-pro (default)
                   | google/nano-banana-2
                   | black-forest-labs/flux-kontext-pro
                   | black-forest-labs/flux-2-dev
                   | black-forest-labs/flux-2-pro
                   | qwen/qwen-image-edit
                   | qwen/qwen-image-edit-plus
                   | flux-kontext-apps/multi-image-kontext-max
                   | bytedance/seedream-4.5
  --aspect R       output aspect (default: match_input_image where supported)
  --seed N         reproducible generation, where the model takes one

Writes <out>.json beside the image: model, prompt, seed, style, and the
sha256 of every input — so a picture you like can be reproduced, and two
pictures can be diffed to find what made one better.

example:
  node ~/projects/media-tools/tools/restyle-image.mjs \\
    --image photo.jpg --style inkwash --model black-forest-labs/flux-2-pro \\
    --out photo-inkwash.png`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const image = flag('--image');
const out = flag('--out');
if (!image || !out) { console.error(HELP); process.exit(2); }

const raw = args.includes('--raw');
const styleKey = flag('--style', 'inkwash');
const extra = flag('--prompt', '');
const model = flag('--model', 'google/nano-banana-pro');
const seed = flag('--seed');

// Models that can receive a second reference image. Anything else gets words.
const REF_CAPABLE = new Set([
  'google/nano-banana-pro', 'google/nano-banana-2',
  'black-forest-labs/flux-2-dev', 'black-forest-labs/flux-2-pro',
  'black-forest-labs/flux-2-max',
  'qwen/qwen-image-edit-plus', 'flux-kontext-apps/multi-image-kontext-max',
  'bytedance/seedream-4.5', 'bytedance/seedream-5-pro',
  'wan-video/wan-2.7-image-pro', 'openai/gpt-image-2',
]);

let stylePrompt = '';
let styleRef = flag('--style-ref');
if (!raw) {
  const p = join(repoRoot(), 'styles', styleKey, 'style.json');
  let style;
  try { style = JSON.parse(readFileSync(p, 'utf8')); }
  catch { console.error(`unknown --style '${styleKey}' (no ${p})`); process.exit(2); }
  stylePrompt = args.includes('--object') ? style.objectPrompt : style.prompt;
  if (!styleRef && !args.includes('--no-style-ref') && style.styleSwatch && REF_CAPABLE.has(model)) {
    const swatch = join(repoRoot(), 'styles', styleKey, style.styleSwatch);
    if (existsSync(swatch)) styleRef = swatch;
  }
}
if (styleRef && !existsSync(styleRef)) { console.error(`--style-ref not found: ${styleRef}`); process.exit(2); }
if (styleRef && !REF_CAPABLE.has(model)) {
  console.error(`--model '${model}' takes no second reference image; drop --style-ref or pick a ref-capable model.`);
  process.exit(2);
}

// Two prompt registers, and which one you get depends on where the style is.
//
// WITH a style ref, the medium arrives as a picture, so the text must NOT also
// describe it — that is the USO three-channel split (style=image, identity=
// image, text=content only). It must also forbid copying the swatch's SUBJECT,
// because the swatch is a painting and the model will happily paint its
// contents instead of its technique.
//
// WITHOUT one, the text is load-bearing and carries the whole look.
const prompt = raw
  ? extra
  : styleRef
    ? `The FIRST image is a photograph. The SECOND image is a painting supplied only as a technique reference. `
      + `Repaint the photograph using the exact medium, brushwork, ink density, colour-wash behaviour, edge quality and paper of the second image. `
      + `Keep the photograph's composition, subject, pose, expression and framing unchanged. `
      + `Take only the painting technique from the second image — never its subject, figures, scenery or composition.${extra ? ' ' + extra : ''}`
    : `Repaint this photograph in the following style, keeping the exact same composition, subjects, poses and framing. ${stylePrompt}${extra ? ' ' + extra : ''}`;
if (!prompt.trim()) { console.error('need --style or --prompt'); process.exit(2); }

const tok = envKey('REPLICATE_API_TOKEN');

const MIME = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif' };

// Replicate fetches these server-side and rejects data: URIs with a bare E002
// that names nothing (proven in cutwork's i2v path) — upload the file first.
async function uploadFile(path) {
  const mime = MIME[extname(path).toLowerCase()] || 'image/jpeg';
  const body = new FormData();
  body.append('content', new Blob([readFileSync(path)], { type: mime }), basename(path));
  const r = await fetch('https://api.replicate.com/v1/files', {
    method: 'POST', headers: { Authorization: `Bearer ${tok}` }, body,
  });
  const j = await r.json();
  if (!r.ok || !j?.urls?.get) throw new Error(`upload ${r.status}: ${JSON.stringify(j).slice(0, 300)}`);
  return j.urls.get;
}

// 'match_input_image' keeps the source's framing. Leaving it to the model's
// own default is what squared a 720x1280 portrait on 2026-08-12.
const aspect = flag('--aspect', 'match_input_image');
const withSeed = seed ? { seed: Number(seed) } : {};

// src = the photograph, ref = the style swatch (may be undefined).
const MODELS = {
  'google/nano-banana-pro': (src, ref) => ({
    prompt, image_input: [src, ...(ref ? [ref] : [])], output_format: 'png', aspect_ratio: aspect,
  }),
  'google/nano-banana-2': (src, ref) => ({
    prompt, image_input: [src, ...(ref ? [ref] : [])], output_format: 'png', aspect_ratio: aspect, resolution: '2K',
  }),
  'black-forest-labs/flux-kontext-pro': (src) => ({
    prompt, input_image: src, output_format: 'png', aspect_ratio: aspect,
  }),
  'black-forest-labs/flux-2-dev': (src, ref) => ({
    prompt, input_images: [src, ...(ref ? [ref] : [])], output_format: 'png', aspect_ratio: aspect, ...withSeed,
  }),
  'black-forest-labs/flux-2-pro': (src, ref) => ({
    prompt, input_images: [src, ...(ref ? [ref] : [])], output_format: 'png',
    aspect_ratio: aspect, resolution: '2 MP', output_quality: 100, ...withSeed,
  }),
  'qwen/qwen-image-edit': (src) => ({ prompt, image: src, output_format: 'png' }),
  'qwen/qwen-image-edit-plus': (src, ref) => ({
    prompt, image: [src, ...(ref ? [ref] : [])], output_format: 'png',
    aspect_ratio: aspect, output_quality: 100, go_fast: false, ...withSeed,
  }),
  // Two slots, no array — the only model here where the ref is mandatory.
  'flux-kontext-apps/multi-image-kontext-max': (src, ref) => ({
    prompt, input_image_1: src, input_image_2: ref, output_format: 'png', aspect_ratio: aspect, ...withSeed,
  }),
  'bytedance/seedream-4.5': (src, ref) => ({
    prompt, image_input: [src, ...(ref ? [ref] : [])], size: '2K', aspect_ratio: aspect,
  }),
  'bytedance/seedream-5-pro': (src, ref) => ({
    prompt, image_input: [src, ...(ref ? [ref] : [])], size: '2K', aspect_ratio: aspect, output_format: 'png',
  }),
  'black-forest-labs/flux-2-max': (src, ref) => ({
    prompt, input_images: [src, ...(ref ? [ref] : [])], output_format: 'png',
    aspect_ratio: aspect, resolution: '2 MP', output_quality: 100, ...withSeed,
  }),
  // No aspect_ratio field at all — `size` auto-sizes from the input.
  'wan-video/wan-2.7-image-pro': (src, ref) => ({
    prompt, images: [src, ...(ref ? [ref] : [])], size: '2K', thinking_mode: true, ...withSeed,
  }),
  // aspect_ratio here is an OpenAI size enum with no match_input_image member;
  // 'auto' is its equivalent and sending ours 422s.
  'openai/gpt-image-2': (src, ref) => ({
    prompt, input_images: [src, ...(ref ? [ref] : [])], output_format: 'png',
    aspect_ratio: 'auto', quality: 'high',
  }),
  // Single image only — no channel for the swatch, so the style rides the text.
  'xai/grok-imagine-image': (src) => ({ prompt, image: src }),
};
if (!MODELS[model]) { console.error(`unknown --model '${model}' (known: ${Object.keys(MODELS).join(', ')})`); process.exit(2); }
if (model === 'flux-kontext-apps/multi-image-kontext-max' && !styleRef) {
  console.error(`${model} requires two images — pass --style-ref or use a style with a styleSwatch.`); process.exit(2);
}

const sha = (p) => createHash('sha256').update(readFileSync(p)).digest('hex').slice(0, 16);

console.error(`restyle-image: ${model} → ${out}`);
console.error(`  source:    ${image}`);
console.error(`  style ref: ${styleRef ? basename(styleRef) : 'NONE — style is text only'}`);

const srcUrl = await uploadFile(image);
const refUrl = styleRef ? await uploadFile(styleRef) : undefined;
const input = MODELS[model](srcUrl, refUrl);
const result = await predictModel(model, input, { token: tok, label: 'restyle-image', interval: 3000, maxPolls: 200 });
const bytes = await fetchBytes(result);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);

// The verdict problem: without this, a picture Ryan likes and one he hates are
// indistinguishable data, and the next session averages them into canon.
writeFileSync(`${out}.json`, JSON.stringify({
  tool: 'restyle-image', provider: 'replicate', model,
  style: raw ? null : styleKey,
  styleChannel: styleRef ? 'image' : 'text',
  prompt,
  seed: seed ? Number(seed) : null,
  aspect,
  inputs: {
    source: { file: image, sha256: sha(image) },
    ...(styleRef ? { styleRef: { file: styleRef, sha256: sha(styleRef) } } : {}),
  },
  out, bytes: bytes.length,
}, null, 2));

console.log(JSON.stringify({ out, manifest: `${out}.json`, bytes: bytes.length, model, styleChannel: styleRef ? 'image' : 'text', style: raw ? null : styleKey, source: image }));
