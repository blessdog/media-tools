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

const HELP = `generate-image — a scene description (+ a style) to one image via Replicate

The style's REFERENCE IMAGE is the look; --prompt is the content. Both are sent
unless you pass --no-reference. Text alone has never reproduced the inkwash look.

usage: node generate-image.mjs --prompt "..." --out path.png [flags]

flags:
  --prompt TEXT    (required) what is in the scene — the content channel
  --out PATH       (required) output image path
  --style KEY      style from styles/KEY/style.json (default: inkwash)
  --no-reference   text-only; skip the style's reference image
  --reference PATH override the style's reference image
  --identity       ALSO copy the reference's face/identity, not just its medium
                   (for carrying one character across shots; off by default)
  --plate          use the style's platePrompt variant (photoreal identity plate)
  --raw            no style at all; --prompt verbatim
  --aspect R       16:9 | 3:4 | 1:1  (default 16:9)
  --seed N         reproducible generation
  --model M        override model (default: the style's image.model)

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
let refPath = flag('--reference');
if (!refPath && style && !usePlate && !args.includes('--no-reference') && style.reference) {
  refPath = join(repoRoot(), 'styles', styleKey, style.reference);
}
const useRef = !!refPath && existsSync(refPath);
if (refPath && !useRef) { console.error(`reference not found: ${refPath}`); process.exit(2); }

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
const model = flag('--model', style?.image?.model || 'replicate/black-forest-labs/flux-2-dev');

const input = {
  prompt: fullPrompt,
  aspect_ratio: flag('--aspect', '16:9'),
  ...(style?.image?.params || { output_format: 'png' }),
};
const seed = flag('--seed');
if (seed) input.seed = parseInt(seed, 10);
if (useRef) input.image_input = [`data:image/png;base64,${readFileSync(refPath).toString('base64')}`];

console.error(`generate-image: ${model}${useRef ? ` · ref ${basename(refPath)}` : ' · TEXT ONLY'} → ${out}`);
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
