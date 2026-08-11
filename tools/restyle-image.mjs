// media-tools — restyle-image: existing image + style → restyled image. One job.
//
// The still-photo sibling of restyle-video. generate-image makes pictures from
// nothing; this one transforms a picture that already exists, preserving its
// composition. Gap found 2026-08-11 by running a real photo through the toolbox.
//
// Model schemas verified live against the Replicate API 2026-08-11:
//   google/nano-banana-pro    image_input: array (up to 14 refs)   ← default
//   black-forest-labs/flux-kontext-pro  input_image: string
//   black-forest-labs/flux-2-dev        input_images: array (max 4)
//   qwen/qwen-image-edit                image: string
// nano-banana-pro is the default because cutwork already proved it strongest
// at identity coherence across reference angles (creative.js 'nano-ref'), and
// its array input is what lets styles/<key>/reference/ plates ride along later.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
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
  --model M        google/nano-banana-pro (default)
                   | black-forest-labs/flux-kontext-pro
                   | black-forest-labs/flux-2-dev
                   | qwen/qwen-image-edit
  --aspect R       output aspect (default: match source, model permitting)

example:
  node ~/projects/media-tools/tools/restyle-image.mjs \\
    --image photo.jpg --style inkwash --out photo-inkwash.png`;

const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) { console.log(HELP); process.exit(0); }
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const image = flag('--image');
const out = flag('--out');
if (!image || !out) { console.error(HELP); process.exit(2); }

const raw = args.includes('--raw');
const styleKey = flag('--style', 'inkwash');
const extra = flag('--prompt', '');
let stylePrompt = '';
if (!raw) {
  const p = join(repoRoot(), 'styles', styleKey, 'style.json');
  let style;
  try { style = JSON.parse(readFileSync(p, 'utf8')); }
  catch { console.error(`unknown --style '${styleKey}' (no ${p})`); process.exit(2); }
  stylePrompt = args.includes('--object') ? style.objectPrompt : style.prompt;
}
// An edit model needs an INSTRUCTION, not just a style noun-phrase: without a
// verb it tends to return the source untouched.
const prompt = raw
  ? extra
  : `Repaint this photograph in the following style, keeping the exact same composition, subjects, poses and framing. ${stylePrompt}${extra ? ' ' + extra : ''}`;
if (!prompt.trim()) { console.error('need --style or --prompt'); process.exit(2); }

const model = flag('--model', 'google/nano-banana-pro');
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

const aspect = flag('--aspect');
const MODELS = {
  'google/nano-banana-pro': (url) => ({
    prompt, image_input: [url], output_format: 'png',
    ...(aspect ? { aspect_ratio: aspect } : {}),
  }),
  'black-forest-labs/flux-kontext-pro': (url) => ({
    prompt, input_image: url, output_format: 'png',
    ...(aspect ? { aspect_ratio: aspect } : {}),
  }),
  'black-forest-labs/flux-2-dev': (url) => ({
    prompt, input_images: [url], output_format: 'png',
    ...(aspect ? { aspect_ratio: aspect } : {}),
  }),
  'qwen/qwen-image-edit': (url) => ({ prompt, image: url, output_format: 'png' }),
};
if (!MODELS[model]) { console.error(`unknown --model '${model}' (known: ${Object.keys(MODELS).join(', ')})`); process.exit(2); }

console.error(`restyle-image: ${model} → ${out}`);
const url = await uploadFile(image);
const result = await predictModel(model, MODELS[model](url), { token: tok, label: 'restyle-image', interval: 3000, maxPolls: 200 });
const bytes = await fetchBytes(result);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);
console.log(JSON.stringify({ out, bytes: bytes.length, model, style: raw ? null : styleKey, source: image }));
