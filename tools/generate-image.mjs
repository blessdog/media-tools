// media-tools — generate-image: prompt (+ style) → one image. One job.
//
// Salvaged from cutwork/tools/quick-still.mjs 2026-08-11. Two changes from the
// original: the style comes from styles/<key>/style.json instead of an imported
// constant (styles-by-reference, CLAUDE.md §5), and the result is JSON on
// stdout with progress on stderr (§4) so it composes in shell pipelines.
//
// Uses predict() — the VERSION-based endpoint. flux-2-dev 404s on the
// model-scoped one (proven in cutwork config.js:41); do not "simplify" this.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { envKey, repoRoot } from './_env.mjs';
import { predict, fetchBytes } from './_replicate.mjs';

const HELP = `generate-image — text prompt (+ optional style) to one image via Replicate

usage: node generate-image.mjs --prompt "..." --out path.png [flags]

flags:
  --prompt TEXT   (required) content description
  --out PATH      (required) output image path
  --style KEY     style from styles/KEY/style.json, prepended (default: inkwash)
  --object        use the style's objectPrompt variant (apparatus, not figures)
  --plate         use the style's platePrompt variant (photoreal identity plate)
  --raw           no style prefix; --prompt verbatim
  --aspect R      16:9 | 3:4 | 1:1  (default 16:9)
  --seed N        reproducible generation
  --model M       override model (default: the style's image.model)

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
const variant = args.includes('--object') ? 'objectPrompt'
  : args.includes('--plate') ? 'platePrompt'
  : 'prompt';
const stylePrefix = style ? style[variant] : '';
if (style && !stylePrefix) { console.error(`style '${styleKey}' has no ${variant}`); process.exit(2); }
const fullPrompt = raw ? prompt : `${stylePrefix} ${prompt}`;
const model = flag('--model', style?.image?.model || 'replicate/black-forest-labs/flux-2-dev');

const input = {
  prompt: fullPrompt,
  aspect_ratio: flag('--aspect', '16:9'),
  ...(style?.image?.params || { output_format: 'png' }),
};
const seed = flag('--seed');
if (seed) input.seed = parseInt(seed, 10);

console.error(`generate-image: ${model} → ${out}`);
console.error(`prompt: ${fullPrompt}`);
const url = await predict(model, input, { token: envKey('REPLICATE_API_TOKEN'), label: 'generate-image' });
const bytes = await fetchBytes(url);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, bytes);
console.log(JSON.stringify({ out, bytes: bytes.length, model, style: raw ? null : styleKey, variant: raw ? null : variant }));
